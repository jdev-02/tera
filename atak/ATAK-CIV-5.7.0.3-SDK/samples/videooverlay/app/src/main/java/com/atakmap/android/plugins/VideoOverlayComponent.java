
package com.atakmap.android.plugins;

import android.content.Context;
import android.content.Intent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;

import com.atakmap.android.importexport.ImporterManager;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.dropdown.DropDownMapComponent;
import com.atakmap.coremap.log.Log;
import com.atakmap.map.layer.opengl.GLLayerFactory;
import com.partech.pgscmedia.MediaException;
import com.partech.pgscmedia.MediaProcessor;

public class VideoOverlayComponent extends DropDownMapComponent {

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

    public final static String SHOW_VIDEO_OVERLAY_TOOL = "com.atakmap.android.plugins.VideoOverlayComponent.SHOW_TOOL";

    private VideoOverlayReceiver _videoOverlayReceiver;
    private VideoOverlayImporter importer;
    private VideoOverlayManager mgr;

    @Override
    public void onCreate(Context context, Intent intent, MapView view) {
        GLLayerFactory.register(GLVideoOverlayLayer.SPI);

        super.onCreate(context, intent, view);

        this.mgr = new VideoOverlayManager();

        _videoOverlayReceiver = new VideoOverlayReceiver(context, view, mgr);

        this.importer = new VideoOverlayImporter(this.mgr);
        ImporterManager.registerImporter(this.importer);

        DocumentedIntentFilter filter = new DocumentedIntentFilter();
        filter.addAction(SHOW_VIDEO_OVERLAY_TOOL);
        registerDropDownReceiver(_videoOverlayReceiver, filter);
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        if (_videoOverlayReceiver != null) {
            _videoOverlayReceiver.dispose();
            _videoOverlayReceiver = null;
        }

        if (this.importer != null) {
            ImporterManager.unregisterImporter(this.importer);
            this.importer = null;
        }

        super.onDestroyImpl(context, view);
    }
}
