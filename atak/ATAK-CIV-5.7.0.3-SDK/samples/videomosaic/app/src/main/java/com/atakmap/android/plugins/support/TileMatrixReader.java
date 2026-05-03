package com.atakmap.android.plugins.support;

import android.graphics.Bitmap;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.control.Controls;
import com.atakmap.map.layer.raster.controls.TileCacheControl;
import com.atakmap.map.layer.raster.controls.TileClientControl;
import com.atakmap.map.layer.raster.tilematrix.TileClient;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.map.layer.raster.tilepyramid.AbstractTilePyramidTileReader;

// XXX - this implementation assumes a quadtree tile matrix
public final class TileMatrixReader extends AbstractTilePyramidTileReader {
    private static final Class<?>[] transferControls = new Class[]{};

    final TileMatrix _impl;
    final int _maxZoom;
    long _version;
    boolean _owns;

    public TileMatrixReader(TileMatrix impl, String uri, AsynchronousIO asyncIO, boolean owns) {
        super(
                uri,
                null,
                asyncIO,
                impl.getZoomLevel()[impl.getZoomLevel().length-1].level+1,
                (long)impl.getZoomLevel()[impl.getZoomLevel().length-1].tileWidth<<(long)impl.getZoomLevel()[impl.getZoomLevel().length-1].level,
                (long)impl.getZoomLevel()[impl.getZoomLevel().length-1].tileHeight<<(long)impl.getZoomLevel()[impl.getZoomLevel().length-1].level,
                impl.getZoomLevel()[impl.getZoomLevel().length-1].tileWidth,
                impl.getZoomLevel()[impl.getZoomLevel().length-1].tileHeight);

        _impl = impl;
        _maxZoom = impl.getZoomLevel()[impl.getZoomLevel().length-1].level;
        _version = 0L;
        _owns = owns;

        // always install a `TileClientControl` to enable the application to request refreshes/set
        // an automatic refresh interval
        TileClientControl clientControl = getControl(_impl, TileClientControl.class);
        this.registerControl(new ClientControlImpl(clientControl));

        // expose a `TileCacheControl` if available from the `TileMatrix`. The exposed control will
        // wrap the matrix's control and perform the zoom level inversion
        TileCacheControl cacheControl = getControl(_impl, TileCacheControl.class);
        if (cacheControl != null) {
            this.registerControl(new CacheControlImpl(cacheControl));
        }

        for(Class ctrlType : transferControls) {
            Object o = getControl(_impl, ctrlType);
            if (o != null)
                this.registerControl(o);
        }
    }

    @Override
    protected void disposeImpl() {
        super.disposeImpl();
        if(_owns)
            _impl.dispose();
    }

    long lastBump = -1L;

    @Override
    public void start() {
        final TileClientControl ctrl = getControl(TileClientControl.class);
        final long tick = System.currentTimeMillis();
        final long refreshInterval = (ctrl != null) ? ctrl.getCacheAutoRefreshInterval() : 0L;
        if(refreshInterval > 0 && (tick-lastBump) > refreshInterval) {
            // refresh interval is elapsed, bump the version
            _version++;
            lastBump = tick;
        }
        super.start();
    }

    @Override
    public long getTileVersion(int level, long tileColumn, long tileRow) {
        return _version;
    }

    @Override
    protected Bitmap getTileImpl(int level, long tileColumn, long tileRow, ReadResult[] code) {
        final Bitmap tile = _impl.getTile(_maxZoom-level, (int)tileColumn, (int)tileRow, null);
        if(code != null)
            code[0] = (tile != null) ? ReadResult.SUCCESS : ReadResult.ERROR;
        return tile;
    }

    static <T> T getControl(TileMatrix tiles, Class<T> ctrlType) {
        if(tiles instanceof TileClient)
            return ((TileClient) tiles).getControl(ctrlType);
        else if(tiles instanceof TileContainer2)
            return ((TileContainer2) tiles).getControl(ctrlType);
        else if(tiles instanceof Controls)
            return ((Controls) tiles).getControl(ctrlType);
        else
            return null;
    }
    private class CacheControlImpl implements TileCacheControl, TileCacheControl.OnTileUpdateListener {
        final TileCacheControl impl;
        OnTileUpdateListener listener;

        CacheControlImpl(TileCacheControl cache) {
            this.impl = cache;
            this.impl.setOnTileUpdateListener(this);
        }

        public void onTileUpdated(int level, int x, int y) {
            OnTileUpdateListener l = this.listener;
            if (l != null) {
                l.onTileUpdated(_maxZoom - level, x, y);
            }
        }

        public void prioritize(GeoPoint p) {
            this.impl.prioritize(p);
        }

        public void abort(int level, int x, int y) {
            this.impl.abort(_maxZoom - level, x, y);
        }

        public boolean isQueued(int level, int x, int y) {
            return this.impl.isQueued(_maxZoom - level, x, y);
        }

        public void setOnTileUpdateListener(OnTileUpdateListener l) {
            this.listener = l;
        }

        public void expireTiles(long expiry) {
            this.impl.expireTiles(expiry);
        }
    }

    private class ClientControlImpl implements TileClientControl {
        final TileClientControl impl;
        long refreshInterval;

        ClientControlImpl(TileClientControl client) {
            this.impl = client;
        }

        @Override
        public void setOfflineOnlyMode(boolean offlineOnly) {
            if(this.impl != null)
                this.impl.setOfflineOnlyMode(offlineOnly);
        }

        @Override
        public boolean isOfflineOnlyMode() {
            return (this.impl != null) ? this.impl.isOfflineOnlyMode() : false;
        }

        @Override
        public void refreshCache() {
            // application requested a refresh, bump the version
            if(this.impl != null)
                this.impl.refreshCache();
            _version++;
        }

        @Override
        public void setCacheAutoRefreshInterval(long milliseconds) {
            if(this.impl != null)
                this.impl.setCacheAutoRefreshInterval(milliseconds);
            this.refreshInterval = milliseconds;
        }

        @Override
        public long getCacheAutoRefreshInterval() {
            return this.refreshInterval;
        }
    }
}
