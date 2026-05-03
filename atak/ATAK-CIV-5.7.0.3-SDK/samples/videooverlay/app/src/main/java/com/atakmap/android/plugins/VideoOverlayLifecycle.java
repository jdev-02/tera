
package com.atakmap.android.plugins;

import android.content.Context;

import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;

public class VideoOverlayLifecycle extends AbstractPlugin {

    private final static String TAG = "VideoOverlaysLifecycle";



    public VideoOverlayLifecycle(IServiceController serviceController) {
        super(serviceController, new VideoOverlayTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new VideoOverlayComponent());
        PluginNativeLoader.init(serviceController.getService(PluginContextProvider.class).getPluginContext());
    }
}
