
package com.atakmap.android.plugins.videomosaic;

import android.content.Context;
import android.content.Intent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;

import com.atakmap.android.importexport.ImporterManager;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.dropdown.DropDownMapComponent;
import com.atakmap.android.overlay.MapOverlayParent;
import com.atakmap.android.plugins.videomosaic.plugin.PluginNativeLoader;
import com.atakmap.android.plugins.videomosaic.tiles.GLMosaickingTileLayer;
import com.atakmap.android.plugins.videomosaic.tiles.MosaickingTileLayer;
import com.atakmap.coremap.log.Log;
import com.atakmap.map.layer.opengl.GLLayerFactory;
import com.partech.pgscmedia.MediaException;
import com.partech.pgscmedia.MediaProcessor;

public class VideoMosaicComponent extends DropDownMapComponent {

    /* Static block to do native library loading and Gv2F Initialization */
    static {
        try {
            /* Loading gnustl_shared is required BEFORE Gv2F init */
            PluginNativeLoader.loadLibrary("gnustl_shared");

            MediaProcessor.PGSCMediaInit(com.atakmap.android.maps.MapView.getMapView().getContext().getApplicationContext());
        } catch (MediaException e) {
            Log.e(TAG,
                    "Error when initializing native components for video player",
                    e);
            throw new RuntimeException(e);
        }
    }

    public final static String SHOW_VIDEO_OVERLAY_TOOL = "com.atakmap.android.plugins.videomosaic.VideoOverlayComponent.SHOW_TOOL";

    private VideoMosaicReceiver _videoMosaicReceiver;
    private VideoImporter importer;
    private VideoMosaicManager mgr;

    @Override
    public void onCreate(Context context, Intent intent, MapView view) {
        GLLayerFactory.register(GLMosaickingTileLayer.SPI);

        MapOverlayParent airOverlays = new MapOverlayParent2(view,
                "airoverlays",
                "Air Overlays",
                null,
                -1,
                true);


        super.onCreate(context, intent, view);

        this.mgr = new VideoMosaicManager();

        _videoMosaicReceiver = new VideoMosaicReceiver(context, view, mgr);

        this.importer = new VideoImporter(this.mgr);
        ImporterManager.registerImporter(this.importer);

        DocumentedIntentFilter filter = new DocumentedIntentFilter();
        filter.addAction(SHOW_VIDEO_OVERLAY_TOOL);
        registerDropDownReceiver(_videoMosaicReceiver, filter);
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        if(mgr != null) {
            for(MosaickingTileLayer overlay : mgr.getOverlays())
                mgr.remove(overlay);
        }
        if (_videoMosaicReceiver != null) {
            _videoMosaicReceiver.dispose();
            _videoMosaicReceiver = null;
        }

        if (this.importer != null) {
            ImporterManager.unregisterImporter(this.importer);
            this.importer = null;
        }

        super.onDestroyImpl(context, view);
    }
}
