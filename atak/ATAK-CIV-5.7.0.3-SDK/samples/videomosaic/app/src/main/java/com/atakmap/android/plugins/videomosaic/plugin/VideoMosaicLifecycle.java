
package com.atakmap.android.plugins.videomosaic.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.plugins.videomosaic.VideoMosaicComponent;

public class VideoMosaicLifecycle extends AbstractPlugin {

    private final static String TAG = "VideoMosaicLifecycle";

    private MapView mapView;

    public VideoMosaicLifecycle(IServiceController serviceController) {
        super(serviceController, new VideoMosaicTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new VideoMosaicComponent());
        PluginNativeLoader.init(serviceController.getService(PluginContextProvider.class).getPluginContext());
    }

}
