package com.atakmap.android.plugins.videomosaic.tiles;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;

import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.util.ConfigOptions;

import java.io.ByteArrayOutputStream;

public class ForegroundBackgroundTileMatrix implements TileMatrix {
    TileMatrix _background;
    TileMatrix _foreground;
    boolean _debugDraw;
    int version = 0;


    ForegroundBackgroundTileMatrix(TileMatrix foreground, TileMatrix background) {
        _foreground = foreground;
        _background = background;
        _debugDraw = (ConfigOptions.getOption("imagery.debug-draw-enabled", 0) != 0);
    }

    @Override
    public String getName() {
        return _foreground.getName();
    }

    @Override
    public int getSRID() {
        return _foreground.getSRID();
    }

    @Override
    public ZoomLevel[] getZoomLevel() {
        return _foreground.getZoomLevel();
    }

    @Override
    public double getOriginX() {
        return _foreground.getOriginX();
    }

    @Override
    public double getOriginY() {
        return _foreground.getOriginY();
    }

    @Override
    public Bitmap getTile(int zoom, int tx, int ty, Throwable[] error) {
        final Bitmap fg = _foreground.getTile(zoom, tx, ty, error);
        if(fg == null)
            return null;
        final Bitmap bg = _background.getTile(zoom, tx, ty, null);
        if(bg == null && !_debugDraw)
            return fg;
        final Bitmap tile = Bitmap.createBitmap(fg.getWidth(), fg.getHeight(), Bitmap.Config.ARGB_8888);
        Canvas c = new Canvas(tile);
        if(bg != null) {
            c.drawBitmap(bg, 0, 0, null);
            bg.recycle();
        }
        c.drawBitmap(fg, 0, 0, null);
        fg.recycle();
        if(_debugDraw) {
            Paint tp = new Paint();
            tp.setColor(Color.MAGENTA);
            tp.setStyle(Paint.Style.FILL);
            tp.setTypeface(Typeface.defaultFromStyle(Typeface.BOLD));
            tp.setTextSize(32);
            c.drawText("VERSION " + version, 32, tile.getHeight() - 32, tp);
        }
        return tile;
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
        return _foreground.getBounds();
    }

    @Override
    public void dispose() {
        _foreground.dispose();
        _background.dispose();
    }
}
