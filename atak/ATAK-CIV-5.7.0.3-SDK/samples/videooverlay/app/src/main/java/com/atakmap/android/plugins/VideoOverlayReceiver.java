
package com.atakmap.android.plugins;

import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.view.LayoutInflater;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.plugins.VideoOverlay.R;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.map.AtakMapView;

class VideoOverlayReceiver extends DropDownReceiver implements
        VideoOverlayManager.OnVideoOverlayListener {

    private final MapView _mapView;
    private final Context pluginContext;
    private final VideoOverlayManager mgr;

    public VideoOverlayReceiver(Context pluginContext, MapView mapView,
            VideoOverlayManager mgr) {
        super(mapView);

        this.pluginContext = pluginContext;
        _mapView = mapView;
        this.mgr = mgr;

        this.mgr.addOnVideoOverlayListener(this);
    }

    @Override
    public void disposeImpl() {
        this.mgr.removeOnVideoOverlayListener(this);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent.getAction().equals(
                VideoOverlayComponent.SHOW_VIDEO_OVERLAY_TOOL)) {
            showManagerView(context);
        }
    }

    private void showManagerView(Context context) {
        LayoutInflater inflater = (LayoutInflater) this.pluginContext
                .getSystemService(Service.LAYOUT_INFLATER_SERVICE);
        VideoOverlayView settingsView = (VideoOverlayView) inflater.inflate(
                R.layout.video_overlay_manager, null);

        settingsView.initView(_mapView, this.mgr);

        showDropDown(settingsView, THREE_EIGHTHS_WIDTH, FULL_HEIGHT,
                FULL_WIDTH, THREE_EIGHTHS_HEIGHT, false);
    }

    /**************************************************************************/

    @Override
    public void onVideoOverlayAdded(VideoOverlayLayer layer) {
        _mapView.addLayer(MapView.RenderStack.MAP_SURFACE_OVERLAYS, layer);
    }

    @Override
    public void onVideoOverlayRemoved(VideoOverlayLayer layer) {
        _mapView.removeLayer(MapView.RenderStack.MAP_SURFACE_OVERLAYS, layer);
    }
}
