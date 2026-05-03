package com.atakmap.android.customtiles;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Rect;

import com.atakmap.map.layer.raster.gdal.GdalGraphicUtils;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.map.layer.raster.tilereader.TileReader;
import com.atakmap.map.layer.raster.tilereader.TileReaderFactory;
import com.atakmap.map.layer.raster.tilereader.TileReaderSpi;

/**
 * Created by Developer on 7/31/2018.
 */

class TileContainerTileReader extends TileReader {
    final static TileReaderSpi SPI = new TileReaderSpi() {
        @Override
        public String getName() {
            return "tilecontainer-adapter";
        }

        @Override
        public TileReader create(String uri, TileReaderFactory.Options options) {
            try {
                AsynchronousIO asyncIO = TileReader.getMasterIOThread();
                if (options != null && options.asyncIO != null)
                    asyncIO = options.asyncIO;
                if (!uri.startsWith("tiles://") || uri.length() < 9)
                    return null;
                uri = uri.substring(8);
                String[] splits = uri.split("\\/");
                if (splits.length != 4)
                    return null;
                final String id = splits[0];
                final int zoom;
                final int row;
                final int col;
                try {
                    zoom = Integer.parseInt(splits[1]);
                    row = Integer.parseInt(splits[2]);
                    col = Integer.parseInt(splits[3]);
                } catch (NumberFormatException e) {
                    return null;
                }

                return new TileContainerTileReader(uri, id, zoom, col, row, asyncIO);
            } catch(Throwable t) {
                return null;
            }
        }

        @Override
        public boolean isSupported(String s) {
            return s.startsWith("tiles://");
        }
    };

    private final String id;
    private final int zoom;
    private final int col;
    private final int row;
    private final int width;
    private final int height;

    TileContainerTileReader(String uri, String id, int zoom, int col, int row, AsynchronousIO asyncIO) {
        super(uri, null, Integer.MAX_VALUE, asyncIO);

        this.id = id;
        this.zoom = zoom;
        this.col = col;
        this.row = row;

        TileContainer tiles = TileContainerMosaicDatabase.find(this.id);
        if(tiles != null) {
            TileMatrix.ZoomLevel zoomLevel = TileMatrix.Util.findZoomLevel(tiles, zoom);
            this.width = zoomLevel.tileWidth;
            this.height = zoomLevel.tileHeight;
        } else {
            this.width = 1;
            this.height = 1;
        }
    }

    @Override
    public long getWidth() {
        return this.getTileWidth();
    }

    @Override
    public long getHeight() {
        return this.getTileHeight();
    }

    @Override
    public int getTileWidth() {
        return this.width;
    }

    @Override
    public int getTileHeight() {
        return this.height;
    }

    @Override
    public ReadResult read(long srcX, long srcY, long srcW, long srcH, int dstW, int dstH, byte[] data) {
        TileContainer tiles = TileContainerMosaicDatabase.find(this.id);
        if(tiles == null)
            return ReadResult.ERROR;
        Bitmap tile = null;
        try {
            // obtain the tile from the container
            tile = tiles.getTile(this.zoom, this.col, this.row, null);
            if (tile == null)
                return ReadResult.ERROR;

            // if the caller has requested any clipping or subsampling, create a new bitmap and
            // perform
            if (srcX != 0 || srcY != 0 || srcW != this.width || srcH != this.height || srcW != dstW || srcH != dstH) {
                Bitmap scratch = Bitmap.createBitmap(dstW, dstH, Bitmap.Config.ARGB_8888);
                Canvas graphics = new Canvas(scratch);
                graphics.drawBitmap(tile,
                        new Rect((int) srcX, (int) srcY, (int) (srcX + srcW), (int) (srcY + srcH)),
                        new Rect(0, 0, dstW, dstH),
                        null);
                // swap the bitmaps
                tile.recycle();
                tile = scratch;
            }

            // get the bitmap data in the specified interleave and format
            GdalGraphicUtils.getBitmapData(tile,
                                           data,
                                           tile.getWidth(),
                                           tile.getHeight(),
                                           this.getInterleave(),
                                           this.getFormat());
            return ReadResult.SUCCESS;
        } finally {
            if(tile != null)
                tile.recycle();
        }
    }

    @Override
    public Format getFormat() {
        return Format.ARGB;
    }

    @Override
    public Interleave getInterleave() {
        return Interleave.BIP;
    }
}
