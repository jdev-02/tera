package com.atakmap.android.customtiles;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;

import com.atakmap.database.CursorIface;
import com.atakmap.database.DatabaseIface;
import com.atakmap.database.QueryIface;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;
import com.atakmap.map.layer.raster.tilematrix.TileEncodeException;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;

import java.io.File;

/**
 * Created by Developer on 7/23/2018.
 */

public class CustomTilesTileContainer implements TileContainer {

    private final DatabaseIface db;
    private final String name;
    private final int srid;
    private final double originX;
    private final double originY;
    private final Envelope bounds;
    private final ZoomLevel[] zoomLevels;

    CustomTilesTileContainer(File file, DatabaseIface db) {
        this.name = file.getName();
        this.db = db;

        CursorIface result;

        // obtain the general metadata about the tile matrix
        result = null;
        ZoomLevel minLevel = new ZoomLevel();
        try {
            result = db.query("SELECT srid, origin_x, origin_y, min_x, min_y, max_x, max_y, tile_width, tile_height, pixel_size_x_z0, pixel_size_y_z0 FROM info LIMIT 1", null);
            if(!result.moveToNext())
                throw new IllegalArgumentException();

            // obtain the SRID (EPSG projection code)
            srid = result.getInt(0);

            // obtain the origin of the tile grid. The origin is the upper-left most coordinate of
            // tile 0,0 at zoom level 0, in the native spatial reference
            originX = result.getDouble(1);
            originY = result.getDouble(2);

            // obtain the bounds of the data containing region. The bounds may not enclose the
            // entire grid, nor is it required to "snap" to the tile grid. ATAK will only request
            // those subset of tiles that intersect these bounds. The bounds should be defined in
            // the native spatial reference
            bounds = new Envelope(result.getDouble(3),
                                  result.getDouble(4),
                             0d,
                                   result.getDouble(5),
                                   result.getDouble(6),
                             0d);

            // tile dimensions
            minLevel.tileWidth = result.getInt(7);
            minLevel.tileHeight = result.getInt(8);

            // for our custom tiles format, these define the pixel size for zoom level zero. Pixel
            // sizes are expressed in native spatial reference units. For example, Web Mercator
            // imagery will specify these in meters (the number of meters per pixel) while WGS84
            // imagery will express these in degrees. These values should be exact as they are used
            // to translate native spatial reference coordinates into tile indices.
            minLevel.pixelSizeX = result.getDouble(9);
            minLevel.pixelSizeY = result.getDouble(10);
        } finally {
            if(result != null)
                result.close();
        }

        // compute the zoom levels

        result = null;
        final int maxZoom;
        try {
            result = db.query("SELECT max(z) FROM customtiles", null);
            if(!result.moveToNext())
                throw new IllegalArgumentException();
            maxZoom = result.getInt(0);
        } finally {
            if(result != null)
                result.close();
        }

        result = null;
        final int minZoom;
        try {
            result = db.query("SELECT min(z) FROM customtiles", null);
            if(!result.moveToNext())
                throw new IllegalArgumentException();
            minZoom = result.getInt(0);
        } finally {
            if(result != null)
                result.close();
        }

        // configure the minimum zoom level
        minLevel.level = minZoom;
        // adjust the pixel size for zoom level 0 by the minimum level -- since the progressive
        // levels are powers-of-two, we can compute this simply by dividing by the appropriate power
        // of two
        minLevel.pixelSizeX /= (1<<minZoom);
        minLevel.pixelSizeY /= (1<<minZoom);

        // the 'resolution' field is information and represents the nominal resolution, in meters
        // per pixel, for a tile at the given zoom level. for meters based coordinate systems, this
        // should be equal to pixel_size_[xy]
        if(srid == 4326) {
            // XXX - crude approximation of resolution for degrees based spatial reference;
            //       implementations should try to estimate as accurately as possible for the best
            //       results
            minLevel.resolution = minLevel.pixelSizeY * 111111d;
        } else {
            // XXX - we're assuming a meters based coordinate system, so the resolution is simply
            //       equal to the pixel size
            minLevel.resolution = minLevel.pixelSizeX;
        }

        // since we know the layout for the tile matrix of the custom tiles format is a quadtree, we
        // can use a utility function to construct all of the zoom levels from the minimum zoom
        // level
        final int numZoomLevels = (maxZoom-minZoom) + 1;
        zoomLevels = TileMatrix.Util.createQuadtree(minLevel, numZoomLevels);
    }

    @Override
    public boolean isReadOnly() {
        return true;
    }

    @Override
    public void setTile(int zoom, int tileColumn, int tileRow, byte[] tileData, long expiration) {
        throw new UnsupportedOperationException("Format is read-only");
    }

    @Override
    public void setTile(int zoom, int tileColumn, int tileRow, Bitmap bitmap, long expiration) throws TileEncodeException {
        throw new UnsupportedOperationException("Format is read-only");
    }

    @Override
    public boolean hasTileExpirationMetadata() {
        return false;
    }

    @Override
    public long getTileExpiration(int i, int i1, int i2) {
        return -1L;
    }

    @Override
    public String getName() {
        return name;
    }

    @Override
    public int getSRID() {
        return srid;
    }

    @Override
    public ZoomLevel[] getZoomLevel() {
        return zoomLevels;
    }

    @Override
    public double getOriginX() {
        return originX;
    }

    @Override
    public double getOriginY() {
        return originY;
    }

    @Override
    public Bitmap getTile(int zoom, int col, int row, Throwable[] error) {
        // obtains the specified tile as an Android Bitmap. This bitmap will be uploaded to a
        // texture for render on the map
        byte[] data = getTileData(zoom, col, row, error);
        if(data == null)
            return null;
        try {
            return BitmapFactory.decodeByteArray(data, 0, data.length);
        } catch(Throwable t) {
            if(error != null)
                error[0] = t;
            return null;
        }
    }

    @Override
    public byte[] getTileData(int zoom, int col, int row, Throwable[] error) {
        // obtains the tile data as a raw byte array. The serialized representation of the data is
        // implementation specific -- in our case we know it will be an encoded image, such as PNG
        // or JPEG
        QueryIface result = null;
        try {
            result = this.db.compileQuery("SELECT tile FROM customtiles WHERE z = ? AND x = ? AND y = ? LIMIT 1");
            result.bind(1, zoom);
            result.bind(2, col);
            result.bind(3, row);

            if(!result.moveToNext())
                return null;

            return result.getBlob(0);
        } catch(Throwable t) {
            if(error != null)
                error[0] = t;
            return null;
        } finally {
            if (result != null)
                result.close();
        }
    }

    @Override
    public Envelope getBounds() {
        return bounds;
    }

    @Override
    public void dispose() {
        this.db.close();
    }
}
