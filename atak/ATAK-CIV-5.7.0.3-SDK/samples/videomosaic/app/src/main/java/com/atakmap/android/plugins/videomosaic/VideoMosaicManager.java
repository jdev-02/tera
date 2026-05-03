
package com.atakmap.android.plugins.videomosaic;

import java.io.File;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.plugins.videomosaic.tiles.MosaickingTileLayer;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.io.IOProviderFactory;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.MapRenderer3;
import com.atakmap.map.layer.control.SurfaceRendererControl;
import com.atakmap.map.layer.raster.controls.TileClientControl;
import com.atakmap.util.Collections2;
import com.atakmap.util.Visitor;

public final class VideoMosaicManager {

    /**
     * Callback invoked when a frame is mosaicked. The callback will request that the corresponding
     * globe surface region is refreshed and signal to the tile renderer that a refresh is required.
     */
    final MosaicDataPipe.FrameMosaickedListener _mosaicListener = new MosaicDataPipe.FrameMosaickedListener() {
        @Override
        public void onFrameMosaicked(MosaickingTileLayer sink, GeoPoint ul, GeoPoint ur, GeoPoint lr, GeoPoint ll) {
            final MapRenderer3 renderer = MapView.getMapView().getRenderer3();

            // signal that the tiles should be refreshed
            renderer.visitControl(sink, new Visitor<TileClientControl>() {
                @Override
                public void visit(TileClientControl object) {
                    object.refreshCache();
                }
            }, TileClientControl.class);

            // mark the surface as dirty
            SurfaceRendererControl surfaceCtrl = renderer.getControl(SurfaceRendererControl.class);
            if(surfaceCtrl != null) {
                surfaceCtrl.markDirty();
            }
        }
    };

    private Map<File, MosaicDataPipe> overlays;
    private Set<OnVideoOverlayListener> listeners;

    public VideoMosaicManager() {
        this.overlays = new HashMap<>();
        this.listeners = Collections2.newIdentityHashSet();
    }

    public synchronized boolean add(File file) {
        if (this.overlays.containsKey(file))
            return true;

        MosaicDataPipe overlay;
        try {
            MosaicDataProvider provider = new MosaicDataProvider(file.getAbsolutePath());
            File f = FileSystemUtils.getItem("tools/realtimemosaic/" + file.getName() + ".sqlite");
            if(IOProviderFactory.exists(f))
                IOProviderFactory.delete(f);
            if(!IOProviderFactory.exists(f.getParentFile()))
                IOProviderFactory.mkdirs(f.getParentFile());
            MosaickingTileLayer mosaic = new MosaickingTileLayer(file.getName(), f);
            overlay = new MosaicDataPipe(provider, mosaic);
            overlay.setListener(_mosaicListener);
            this.overlays.put(file, overlay);
            overlay.start(true);
        } catch (Exception e) {
            Log.e("VideoOverlayManager",
                    "Failed to load " + file.getAbsolutePath(), e);
            return false;
        }

        if(overlay.sink() != null)
            this.dispatchOnVideoOverlayAddedNoSync(overlay.sink());
        return true;
    }

    public synchronized void remove(File file) {
        final MosaicDataPipe layer = this.overlays.remove(file);
        if (layer != null)
            this.dispatchOnVideoOverlayRemovedNoSync(layer.sink());
    }

    public synchronized void remove(MosaickingTileLayer layer) {
        for(Map.Entry<File, MosaicDataPipe> entry : overlays.entrySet()) {
            if(entry.getValue().sink() == layer) {
                entry.getValue().stop();
                entry.getValue().setListener(null);
                overlays.remove(entry.getKey());
                this.dispatchOnVideoOverlayRemovedNoSync(entry.getValue().sink());
            }
        }
    }

    public synchronized MosaickingTileLayer[] getOverlays() {
        MosaickingTileLayer[] retval = new MosaickingTileLayer[this.overlays
                .size()];
        int idx = 0;
        for(MosaicDataPipe entry : overlays.values())
            retval[idx++] = entry.sink();
        return retval;
    }

    private void dispatchOnVideoOverlayAddedNoSync(MosaickingTileLayer layer) {
        for (OnVideoOverlayListener l : this.listeners)
            l.onVideoOverlayAdded(layer);
    }

    private void dispatchOnVideoOverlayRemovedNoSync(MosaickingTileLayer layer) {
        for (OnVideoOverlayListener l : this.listeners)
            l.onVideoOverlayRemoved(layer);
    }

    public synchronized void addOnVideoOverlayListener(
            OnVideoOverlayListener l) {
        this.listeners.add(l);
    }

    public synchronized void removeOnVideoOverlayListener(
            OnVideoOverlayListener l) {
        this.listeners.remove(l);
    }

    /**************************************************************************/

    public static interface OnVideoOverlayListener {
        public void onVideoOverlayAdded(MosaickingTileLayer overlay);

        public void onVideoOverlayRemoved(MosaickingTileLayer overlay);
    }

}
