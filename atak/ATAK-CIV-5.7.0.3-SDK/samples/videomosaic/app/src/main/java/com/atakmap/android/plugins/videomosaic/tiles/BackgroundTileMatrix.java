package com.atakmap.android.plugins.videomosaic.tiles;

import android.graphics.Bitmap;

import com.atakmap.android.plugins.support.TileCompositor;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;

import java.io.ByteArrayOutputStream;

final class BackgroundTileMatrix implements TileMatrix {
    TileMatrix _source;
    
    BackgroundTileMatrix(TileMatrix source) {
        _source = source;
    }

    @Override
    public String getName() {
        return _source.getName();
    }

    @Override
    public int getSRID() {
        return _source.getSRID();
    }

    @Override
    public ZoomLevel[] getZoomLevel() {
        return _source.getZoomLevel();
    }

    @Override
    public double getOriginX() {
        return _source.getOriginX();
    }

    @Override
    public double getOriginY() {
        return _source.getOriginY();
    }

    @Override
    public Bitmap getTile(int zoom, int tx, int ty, Throwable[] error) {
        final TileMatrix.ZoomLevel level = TileMatrix.Util.findZoomLevel(_source, zoom);
        if(level == null)
            return null;
        final Envelope backgroundBounds = TileMatrix.Util.getTileBounds(level, _source.getOriginX(), _source.getOriginY(), tx, ty);
        Bitmap background = null;
        for(int i = 0; i < zoom; i++) {
            final int shift = zoom-i;
            final int atx = tx>>shift;
            final int aty = ty>>shift;
            final Bitmap ancestor = _source.getTile(i, atx, aty, null);
            if(ancestor == null)
                continue;
            if(background == null)
                background = Bitmap.createBitmap(level.tileWidth, level.tileHeight, Bitmap.Config.ARGB_8888);
            // copy ancestor to background
            TileCompositor.copyIntersectingRegion(ancestor, TileMatrix.Util.getTileBounds(_source, i, atx, aty), background, backgroundBounds);
            ancestor.recycle();
        }

        return background;
    }

    @Override
    public byte[] getTileData(int zoom, int x, int y, Throwable[] error) {
        final Bitmap tile = getTile(zoom, x, y, error);
        if(tile == null)
            return null;
        try {
            final ByteArrayOutputStream bos = new ByteArrayOutputStream(tile.getWidth()*tile.getHeight()*4);
            tile.compress(Bitmap.CompressFormat.PNG, 100, bos);
            tile.recycle();
            return bos.toByteArray();
        } catch(Throwable t) {
            if(error != null)
                error[0] = t;
            return null;
        }
    }

    @Override
    public Envelope getBounds() {
        return _source.getBounds();
    }

    @Override
    public void dispose() {
        _source.dispose();
    }
}
