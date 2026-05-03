package com.atakmap.android.plugins.videomosaic.tiles;

import android.graphics.Bitmap;
import android.graphics.Canvas;

import com.atakmap.android.plugins.support.OSMDroidTileContainer2;
import com.atakmap.android.plugins.support.TileCompositor;
import com.atakmap.android.plugins.support.TileContainer2;
import com.atakmap.coremap.io.IOProviderFactory;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.AbstractLayer;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.ImageInfo;
import com.atakmap.map.layer.raster.tilematrix.TileEncodeException;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.math.MathUtils;

import java.io.File;

public final class MosaickingTileLayer extends AbstractLayer {
    /** dynamically composited foreground+background */
    ForegroundBackgroundTileMatrix displayData;
    /** holds the source tiles */
    TileContainer2 sourceData;
    /** holds the tiles merged into foreground */
    TileContainer2 foreground;
    /** dynamically generated background */
    TileMatrix background;
    /** minimum bounding box containing data received */
    Envelope mbb;

    public MosaickingTileLayer(String name, File mosaicFile) {
        super(name);

        if(!IOProviderFactory.isDirectory(mosaicFile)) {
            IOProviderFactory.delete(mosaicFile);
            IOProviderFactory.mkdirs(mosaicFile);
        }


        sourceData = OSMDroidTileContainer2.openOrCreate(new File(mosaicFile, "source").getAbsolutePath(), "mosaic", 3857);
        foreground = OSMDroidTileContainer2.openOrCreate(new File(mosaicFile, "foreground").getAbsolutePath(), "mosaic", 3857);
        background = new BackgroundTileMatrix(sourceData);
        displayData = new ForegroundBackgroundTileMatrix(foreground, background);
    }

    /**
     * Updates the mosaic with the specified data. The data is assumed to be in an equirectangular
     * map projection.
     * @param ul    The upper-left corner of the data
     * @param ur    The upper-right corner of the data
     * @param lr    The lower-right corner of the data
     * @param ll    The lower-left corner of the data
     * @param data  The image data
     */
    public void updateMosaic(GeoPoint ul, GeoPoint ur, GeoPoint lr, GeoPoint ll, Bitmap data) {
        updateMosaic(new ImageInfo(
                        null,
                        null,
                        false,
                        ul, ur, lr, ll,
                        DatasetDescriptor.computeGSD(data.getWidth(), data.getHeight(), ul, ur, lr, ll),
                        data.getWidth(), data.getHeight(),
                        4326),
                data);
    }

    /**
     * Updates the mosaic with the specified data.
     * @param info  Describes the data; a reasonable value for <code>maxGsd</code> MUST be specified
     * @param data  The image data
     */
    void updateMosaic(ImageInfo info, Bitmap data) {
        final int compositeZoomLevel =  TileCompositor.selectCompositeZoomLevel(sourceData, info.maxGsd);

        // composite the tile into the sources container
        {
            long s = System.currentTimeMillis();
            TileCompositor.mergeTile(sourceData, compositeZoomLevel, info, data);
            long e = System.currentTimeMillis();
            Log.i("RealtimeMosaicLayer", "composited source in " + (e - s) + "ms");
        }
        // regenerate the foreground tiles
        {
            long s = System.currentTimeMillis();
            final Envelope dataRegion = TileCompositor.getMinimumBoundingBox(info, sourceData.getSRID());
            final TileMatrix.ZoomLevel[] levels = sourceData.getZoomLevel();
            final int compositeLevelIdx = TileCompositor.findZoomLevelIndex(sourceData, compositeZoomLevel);
            final TileMatrix.ZoomLevel compositeLevel = levels[compositeLevelIdx];
            // regenerate foreground at composite level
            TileCompositor.forEachTile(sourceData, compositeLevel.level, dataRegion, new TileCompositor.OnTileCallback() {
                @Override
                public boolean fn(int zoomLevel, int tx, int ty) {
                    final Bitmap foregroundTile = generateForeground(zoomLevel, tx, ty);
                    if(foregroundTile != null) {
                        // set tile
                        try {
                            foreground.setTile(zoomLevel, tx, ty, foregroundTile, -1L);
                        } catch(TileEncodeException ignored) {}
                        foregroundTile.recycle();
                    }
                    return true;
                }
            });

            // propopagate new foreground
            for(int i = compositeLevelIdx-1; i >= 0; i--) {
                // subsample down to single pixel contribution
                if((levels[i].tileWidth>>(compositeLevelIdx-i)) == 0 || (levels[i].tileHeight>>(compositeLevelIdx-i)) == 0)
                    break;

                final int tileWidth = levels[i].tileWidth;
                final int tileHeight = levels[i].tileHeight;
                // regenerate foreground for current zoom level
                TileCompositor.forEachTile(sourceData, levels[i].level, dataRegion, new TileCompositor.OnTileCallback() {
                    @Override
                    public boolean fn(int zoomLevel, int tx, int ty) {
                        Bitmap ancestor = Bitmap.createBitmap(tileWidth, tileHeight, Bitmap.Config.ARGB_8888);
                        Canvas ac = new Canvas(ancestor);
                        // old foreground is background of new foreground
                        final Bitmap fg = foreground.getTile(zoomLevel, tx, ty, null);
                        if(fg != null) {
                            ac.drawBitmap(fg, 0, 0, null);
                            fg.recycle();
                        }
                        // composite foreground on top of tile
                        TileCompositor.compositeChildren(foreground, zoomLevel, tx, ty, ac);

                        // set updated tile
                        try {
                            foreground.setTile(zoomLevel, tx, ty, ancestor, -1L);
                        } catch(TileEncodeException ignored) {}
                        ancestor.recycle();

                        return true;
                    }
                });
            }

            long e = System.currentTimeMillis();
            Log.i("RealtimeMosaicLayer", "generated foreground in " + (e - s) + "ms");
        }

        // update data containing bounds
        final double ullat = info.upperLeft.getLatitude();
        final double ullng = info.upperLeft.getLongitude();
        final double urlat = info.upperRight.getLatitude();
        final double urlng = info.upperRight.getLongitude();
        final double lrlat = info.lowerRight.getLatitude();
        final double lrlng = info.lowerRight.getLongitude();
        final double lllat = info.lowerLeft.getLatitude();
        final double lllng = info.lowerLeft.getLongitude();
        final Envelope frameBounds = new Envelope(
                MathUtils.min(ullng, urlng, lrlng, lllng),
                MathUtils.min(ullat, urlat, lrlat, lllat),
                0d,
                MathUtils.max(ullng, urlng, lrlng, lllng),
                MathUtils.max(ullat, urlat, lrlat, lllat),
                0d
        );
        if(mbb == null) {
            mbb = frameBounds;
        } else {
            mbb.minX = Math.min(frameBounds.minX, mbb.minX);
            mbb.minY = Math.min(frameBounds.minY, mbb.minY);
            mbb.maxX = Math.max(frameBounds.maxX, mbb.maxX);
            mbb.maxY = Math.max(frameBounds.maxY, mbb.maxY);
        }

        displayData.version++;
    }

    /**
     * Generates the foreground for the specified file from source data. Data for the zoom level is
     * included.
     * @param zoomLevel
     * @param tx
     * @param ty
     * @return
     */
    Bitmap generateForeground(int zoomLevel, int tx, int ty) {
        // obtain source data
        final Bitmap sourceTile = sourceData.getTile(zoomLevel, tx, ty, null);
        if(sourceTile == null)
            return null;
        Bitmap foregroundTile = Bitmap.createBitmap(sourceTile.getWidth(), sourceTile.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(foregroundTile);
        // source tile is "background" of foreground
        c.drawBitmap(sourceTile, 0, 0, null);
        sourceTile.recycle();

        // composite foreground on top of source tile
        TileCompositor.compositeChildren(foreground, zoomLevel, tx, ty, c);
        return foregroundTile;
    }

    TileMatrix getTiles() {
        return displayData;
    }

    public Envelope getBounds() {
        return mbb;
    }
}
