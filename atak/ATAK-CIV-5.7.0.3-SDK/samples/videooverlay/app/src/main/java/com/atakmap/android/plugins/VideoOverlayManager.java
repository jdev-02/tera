
package com.atakmap.android.plugins;

import java.io.File;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.Set;

import com.atakmap.coremap.log.Log;

public final class VideoOverlayManager {

    private Map<File, VideoOverlayLayer> overlays;
    private Set<OnVideoOverlayListener> listeners;

    public VideoOverlayManager() {
        this.overlays = new HashMap<File, VideoOverlayLayer>();
        this.listeners = Collections
                .newSetFromMap(
                        new IdentityHashMap<OnVideoOverlayListener, Boolean>());
    }

    public synchronized boolean add(File file) {
        if (this.overlays.containsKey(file))
            return true;

        VideoOverlayLayer overlay;
        try {
            overlay = new VideoOverlayLayer(file.getName(),
                    file.getAbsolutePath());
            this.overlays.put(file, overlay);
            overlay.start();
        } catch (Exception e) {
            Log.e("VideoOverlayManager",
                    "Failed to load " + file.getAbsolutePath(), e);
            return false;
        }

        this.dispatchOnVideoOverlayAddedNoSync(overlay);
        return true;
    }

    public synchronized void remove(File file) {
        final VideoOverlayLayer layer = this.overlays.remove(file);
        if (layer != null)
            this.dispatchOnVideoOverlayRemovedNoSync(layer);
    }

    public synchronized void remove(VideoOverlayLayer layer) {
        if (this.overlays.values().remove(layer))
            this.dispatchOnVideoOverlayRemovedNoSync(layer);
    }

    public synchronized VideoOverlayLayer[] getOverlays() {
        VideoOverlayLayer[] retval = new VideoOverlayLayer[this.overlays
                .size()];
        this.overlays.values().toArray(retval);
        return retval;
    }

    private void dispatchOnVideoOverlayAddedNoSync(VideoOverlayLayer layer) {
        for (OnVideoOverlayListener l : this.listeners)
            l.onVideoOverlayAdded(layer);
    }

    private void dispatchOnVideoOverlayRemovedNoSync(VideoOverlayLayer layer) {
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
        public void onVideoOverlayAdded(VideoOverlayLayer overlay);

        public void onVideoOverlayRemoved(VideoOverlayLayer overlay);
    }

}
