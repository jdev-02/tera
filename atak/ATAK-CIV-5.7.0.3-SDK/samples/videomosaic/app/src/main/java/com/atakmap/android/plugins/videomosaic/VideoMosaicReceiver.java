
package com.atakmap.android.plugins.videomosaic;

import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.view.LayoutInflater;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.plugins.VideoOverlay.R;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.plugins.videomosaic.tiles.MosaickingTileLayer;

class VideoMosaicReceiver extends DropDownReceiver implements
        VideoMosaicManager.OnVideoOverlayListener {

    private final MapView _mapView;
    private final Context pluginContext;
    private final VideoMosaicManager mgr;

    public VideoMosaicReceiver(Context pluginContext, MapView mapView,
                               VideoMosaicManager mgr) {
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
                VideoMosaicComponent.SHOW_VIDEO_OVERLAY_TOOL)) {
            showManagerView(context);
        }
    }

    private void showManagerView(Context context) {
        LayoutInflater inflater = (LayoutInflater) this.pluginContext
                .getSystemService(Service.LAYOUT_INFLATER_SERVICE);
        VideoMosaicView settingsView = (VideoMosaicView) inflater.inflate(
                R.layout.video_overlay_manager, null);

        settingsView.initView(_mapView, this.mgr);

        showDropDown(settingsView, THREE_EIGHTHS_WIDTH, FULL_HEIGHT,
                FULL_WIDTH, THREE_EIGHTHS_HEIGHT, false);
    }

    /**************************************************************************/

    @Override
    public void onVideoOverlayAdded(MosaickingTileLayer layer) {
        _mapView.addLayer(MapView.RenderStack.MAP_SURFACE_OVERLAYS, layer);
    }

    @Override
    public void onVideoOverlayRemoved(MosaickingTileLayer layer) {
        _mapView.removeLayer(MapView.RenderStack.MAP_SURFACE_OVERLAYS, layer);
    }
}
