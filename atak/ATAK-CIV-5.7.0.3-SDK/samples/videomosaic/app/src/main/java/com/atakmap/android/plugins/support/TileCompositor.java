package com.atakmap.android.plugins.support;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Point;
import android.graphics.Rect;

import com.atakmap.android.plugins.support.TileContainer2;
import com.atakmap.coremap.log.Log;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.raster.DatasetProjection2;
import com.atakmap.map.layer.raster.DefaultDatasetProjection2;
import com.atakmap.map.layer.raster.ImageInfo;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;
import com.atakmap.map.layer.raster.tilematrix.TileEncodeException;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.map.projection.Projection;
import com.atakmap.map.projection.ProjectionFactory;
import com.atakmap.math.MathUtils;
import com.atakmap.math.PointD;
import com.atakmap.spatial.GeometryTransformer;

public final class TileCompositor {
    /**
     * Selects the zoom level to composite
     * @param container
     * @param gsd
     * @return
     */
    public static int selectCompositeZoomLevel(TileContainer2 container, double gsd) {
        final TileMatrix.ZoomLevel[] levels = container.getZoomLevel();
        // find closest level (ceil)
        int zoomLevelIdx = levels.length-1;
        for(int i = levels.length-1; i >= 0; i--) {
            // we are going to bias towards lower resolution to maximize throughput; assignment
            // could occur after the comparison to bias towards the higher resolution level
            zoomLevelIdx = i;

            // next zoom level is lower res than data, done
            if(gsd <= levels[i].resolution)
                break;
            // zoom level is higher res than data, continue
        }

        return levels[zoomLevelIdx].level;
    }

    public static interface OnTileCallback {
        boolean fn(int zoomLevel, int tx, int ty);
    }

    /**
     * Iterates all tile indices in the given container at the specified zoom level over the
     * specified region.
     * @param container The tile container
     * @param zoomLevel The zoom level
     * @param region    The region to iterate, specified in the container's spatial reference
     * @param action    The callback to execute for each tile. If the callback returns
     *                  <code>false</code>, iteration terminates and <code>false</code> is returned.
     * @return  <code>true</code> if iteration completed, <code>false</code> if it terminated early.
     */
    public static boolean forEachTile(TileMatrix container, int zoomLevel, Envelope region, OnTileCallback action) {
        final TileMatrix.ZoomLevel zoom = TileMatrix.Util.findZoomLevel(container, zoomLevel);
        if(zoom == null)
            return false; // nothing to evict

        final Point st = TileMatrix.Util.getTileIndex(container.getOriginX(), container.getOriginY(), zoom, region.minX, region.maxY);
        final Point ft = TileMatrix.Util.getTileIndex(container.getOriginX(), container.getOriginY(), zoom, region.maxX, region.minY);
        for(int ty = st.y; ty <= ft.y; ty++) {
            for(int tx = st.x; tx <= ft.x; tx++) {
                if(!action.fn(zoomLevel, tx, ty))
                    return false;
            }
        }
        return true;
    }

    /**
     * Merges the specified chip into the tile container at the specified zoom level.
     * @param container The tile container
     * @param zoomLevel The zoom level
     * @param info      Basic metadata about the chip. Requires that the corners are defined; if the
     *                  SRID is undefined, same SRID as the container is assumed
     * @param data      The data to be merged
     * @return  <code>true</code> if the data was successfully merged, <code>false</code> otherwise.
     */
    public static boolean mergeTile(TileContainer container, int zoomLevel, ImageInfo info, Bitmap data) {
        final int zoomLevelIdx = findZoomLevelIndex(container, zoomLevel);
        if(zoomLevelIdx < 0)
            return false;
        final TileMatrix.ZoomLevel[] zoomLevels = container.getZoomLevel();
        final TileMatrix.ZoomLevel zoom = zoomLevels[zoomLevelIdx];

        // construct I2G/G2I for data
        final DatasetProjection2 i2g = new DefaultDatasetProjection2(info);
        // convert MBB to container's native projection
        final Envelope mbb = getMinimumBoundingBox(info, container.getSRID());
        // determine intersecting tiles
        final Point st = TileMatrix.Util.getTileIndex(container.getOriginX(), container.getOriginY(), zoom, mbb.minX, mbb.maxY);
        final Point ft = TileMatrix.Util.getTileIndex(container.getOriginX(), container.getOriginY(), zoom, mbb.maxX, mbb.minY);

        Log.i("TileCompositor", "mosaic ntx=" + (ft.x-st.x+1) + " nty=" + (ft.y-st.y+1));
        final Projection proj = ProjectionFactory.getProjection(container.getSRID());

        final PointD dataULproj = new PointD(0d, 0d, 0d);
        proj.forward(info.upperLeft, dataULproj);
        final PointD dataURproj = new PointD(0d, 0d, 0d);
        proj.forward(info.upperRight, dataURproj);
        final PointD dataLRproj = new PointD(0d, 0d, 0d);
        proj.forward(info.lowerRight, dataLRproj);
        final PointD dataLLproj = new PointD(0d, 0d, 0d);
        proj.forward(info.lowerLeft, dataLLproj);

        for(int ty = st.y; ty <= ft.y; ty++) {
            for(int tx = st.x; tx <= ft.x; tx++) {
                final Envelope tileBounds = TileMatrix.Util.getTileBounds(zoom, container.getOriginX(), container.getOriginY(), tx, ty);

                Bitmap tile = container.getTile(zoomLevel, tx, ty, null);
                if(tile == null) {
                    // no data is available, create a transparent tile
                    tile = Bitmap.createBitmap(zoom.tileWidth, zoom.tileHeight, Bitmap.Config.ARGB_8888);
                } else if(!tile.isMutable()) {
                    // the tile is present, but it is not writable. Create a writable bitmap and
                    // copy the original tile content
                    final Bitmap mutable = Bitmap.createBitmap(tile.getWidth(), tile.getHeight(), Bitmap.Config.ARGB_8888);
                    Canvas c = new Canvas(mutable);
                    c.drawBitmap(tile, 0, 0, null);
                    final Bitmap toRecycle = tile;
                    tile = mutable;
                    toRecycle.recycle();
                }

                // composite the data onto the tile

                // NOTE: experimental profiling indicates that restricting the composition operation
                // to the interesecting regions of the source and destination bitmaps does not have
                // a significant impact on performance
                final PointD meshULxy = TileMatrix.Util.getTilePixel(container, zoomLevel, tx, ty, dataULproj.x, dataULproj.y);
                final PointD meshURxy = TileMatrix.Util.getTilePixel(container, zoomLevel, tx, ty, dataURproj.x, dataURproj.y);
                final PointD meshLRxy = TileMatrix.Util.getTilePixel(container, zoomLevel, tx, ty, dataLRproj.x, dataLRproj.y);
                final PointD meshLLxy = TileMatrix.Util.getTilePixel(container, zoomLevel, tx, ty, dataLLproj.x, dataLLproj.y);

                if(MathUtils.min(meshULxy.x, meshURxy.x, meshLRxy.x, meshLLxy.x) == MathUtils.max(meshULxy.x, meshURxy.x, meshLRxy.x, meshLLxy.x) ||
                   MathUtils.min(meshULxy.y, meshURxy.y, meshLRxy.y, meshLLxy.y) == MathUtils.max(meshULxy.y, meshURxy.y, meshLRxy.y, meshLLxy.y)) {

                    Log.i("TileCompositor", "skipping empty mosaic tile");
                    continue;
                }

                Canvas c = new Canvas(tile);
                c.drawBitmapMesh(
                        data, 1, 1,
                        new float[]{
                                (float) meshULxy.x, (float) meshULxy.y,
                                (float) meshURxy.x, (float) meshURxy.y,
                                (float) meshLLxy.x, (float) meshLLxy.y,
                                (float) meshLRxy.x, (float) meshLRxy.y,},
                        0,
                        new int[]{-1, -1, -1, -1}, 0,
                        null);

                // set the tile
                try {
                    container.setTile(zoomLevel, tx, ty, tile, -1L);
                } catch(TileEncodeException e) {
                    return false;
                }

                tile.recycle();
            }
        }

        return true;
    }


    /**
     * Evict all tiles at a given zoom level that intersect the specified region.
     * @param container The tile container
     * @param region    The region to evict, specified in the spatial reference of the container
     * @param zoomLevel The zoom level
     * @return
     */
    public static void evictTiles(final TileContainer2 container, Envelope region, int zoomLevel) {
        final TileMatrix.ZoomLevel zoom = TileMatrix.Util.findZoomLevel(container, zoomLevel);

        // determine intersecting tiles
        final Point st = TileMatrix.Util.getTileIndex(container.getOriginX(), container.getOriginY(), zoom, region.minX, region.maxY);
        final Point ft = TileMatrix.Util.getTileIndex(container.getOriginX(), container.getOriginY(), zoom, region.maxX, region.minY);

        container.deleteTiles(zoomLevel, st.x, st.y, ft.x, ft.y);
    }

    /**
     * Obtains the minimum bounding box of the image described by the specified metadata, in the
     * specified spatial reference.
     * @param info      The image metadata
     * @param dstSrid   The output spatial reference
     * @return  The minimum bounding box of the described image, in the specified spatial reference.
     */
    public static Envelope getMinimumBoundingBox(ImageInfo info, int dstSrid) {
        final double ullat = info.upperLeft.getLatitude();
        final double ullng = info.upperLeft.getLongitude();
        final double urlat = info.upperRight.getLatitude();
        final double urlng = info.upperRight.getLongitude();
        final double lrlat = info.lowerRight.getLatitude();
        final double lrlng = info.lowerRight.getLongitude();
        final double lllat = info.lowerLeft.getLatitude();
        final double lllng = info.lowerLeft.getLongitude();
        final Envelope mbb = new Envelope(
            MathUtils.min(ullng, urlng, lrlng, lllng),
            MathUtils.min(ullat, urlat, lrlat, lllat),
            0d,
            MathUtils.max(ullng, urlng, lrlng, lllng),
            MathUtils.max(ullat, urlat, lrlat, lllat),
            0d
        );

        return GeometryTransformer.transform(mbb, 4326, dstSrid);
    }

    /**
     * Finds the array index for <code>matrix.getZoomLevel()</code> that corresponds to the
     * specified zoom level.
     * @param matrix    A tile matrix
     * @param zoomLevel The zoom level
     * @return  The array index corresponding to the zoom level or <code>-1</code> if the zoom level
     *          does not exist for the matrix.
     */
    public static int findZoomLevelIndex(TileMatrix matrix, int zoomLevel) {
        // XXX - could implement as binary search for efficiency
        final TileMatrix.ZoomLevel[] levels = matrix.getZoomLevel();
        for(int i = 0; i < levels.length; i++) {
            if(levels[i].level == zoomLevel)
                return i;
        }
        return -1;
    }

    public static Rect computeRegion(Envelope window, Envelope fullExtent, int extentWidth, int extentHeight) {
        // NOTE: maxy corresponds to image top, miny corresponds to image bottom
        final double l = (window.minX-fullExtent.minX)/(fullExtent.maxX-fullExtent.minX);
        final double t = ((fullExtent.maxY-window.maxY)/(fullExtent.maxY-fullExtent.minY));
        final double r = ((window.maxX-fullExtent.minX)/(fullExtent.maxX-fullExtent.minX));
        final double b = ((fullExtent.maxY-window.minY)/(fullExtent.maxY-fullExtent.minY));
        return new Rect(
                (int)MathUtils.clamp(l*extentWidth, 0, extentWidth-1),
                (int)MathUtils.clamp(t*extentHeight, 0, extentHeight-1),
                (int)MathUtils.clamp(r*extentWidth, 0, extentWidth),
                (int)MathUtils.clamp(b*extentHeight, 0, extentHeight)
        );
    }

    /**
     * Copies the intersecting region of the source onto the corresponding region in the
     * destination. The bounds do not need to be in pixel space -- they will be linearly mapped to
     * the pixel extents of the respective bitmaps.
     * @param srcData   The source bitmap to be copied onto the destination bitmap
     * @param srcBounds The bounds of the source
     * @param dstData   The destination bitmap
     * @param dstBounds The bounds of the destination
     */
    public static void copyIntersectingRegion(Bitmap srcData, Envelope srcBounds, Bitmap dstData, Envelope dstBounds) {
        copyIntersectingRegion(srcData, srcBounds, new Canvas(dstData), dstData.getWidth(), dstData.getHeight(), dstBounds);
    }
    public static void copyIntersectingRegion(Bitmap srcData, Envelope srcBounds, Canvas dst, int dstWidth, int dstHeight, Envelope dstBounds) {
        Envelope boundsIsect = new Envelope(dstBounds);
        boundsIsect.minX = Math.max(srcBounds.minX, dstBounds.minX);
        boundsIsect.minY = Math.max(srcBounds.minY, dstBounds.minY);
        boundsIsect.maxX = Math.min(srcBounds.maxX, dstBounds.maxX);
        boundsIsect.maxY = Math.min(srcBounds.maxY, dstBounds.maxY);
        if(boundsIsect.minX == boundsIsect.maxX || boundsIsect.minY == boundsIsect.maxY)
            return;

        dst.drawBitmap(
                srcData,
                // source region
                computeRegion(boundsIsect, srcBounds, srcData.getWidth(), srcData.getHeight()),
                // destination region
                computeRegion(boundsIsect, dstBounds, dstWidth, dstHeight),
                null);
    }

    /**
     * Composites the child tiles for the given tile index into the provide {@link Canvas}
     * @param tiles     The tile matrix
     * @param zoomLevel The zoom level of the parent
     * @param tx        The tile column of the parent
     * @param ty        The tile row of the parent
     * @param c         The target {@link Canvas}
     * @return  <code>true</code> if one or more child tiles were composited, <code>false</code>
     *          if no child tiles were composited.
     */
    public static boolean compositeChildren(TileMatrix tiles, int zoomLevel, int tx, int ty, final Canvas c) {
        final TileMatrix.ZoomLevel zoom = TileMatrix.Util.findZoomLevel(tiles, zoomLevel);
        if(zoom == null)
            return false;

        final Envelope parentBounds = TileMatrix.Util.getTileBounds(tiles, zoomLevel, tx, ty);
        // shrink bounds by single pixel to avoid picking up intersections on edges
        parentBounds.minX += zoom.pixelSizeX;
        parentBounds.minY += zoom.pixelSizeY;
        parentBounds.maxX -= zoom.pixelSizeX;
        parentBounds.maxY -= zoom.pixelSizeY;

        final int[] childCount = new int[] {0};
        forEachTile(tiles, zoomLevel+1, parentBounds, new OnTileCallback() {
            @Override
            public boolean fn(int czl, int ctx, int cty) {
                final Bitmap child = tiles.getTile(czl, ctx, cty, null);
                if(child != null) {
                    copyIntersectingRegion(child, TileMatrix.Util.getTileBounds(tiles, czl, ctx, cty), c, zoom.tileWidth, zoom.tileHeight, parentBounds);
                    childCount[0]++;
                    child.recycle();
                }
                return true;
            }
        });

        return childCount[0]>0;
    }
}
