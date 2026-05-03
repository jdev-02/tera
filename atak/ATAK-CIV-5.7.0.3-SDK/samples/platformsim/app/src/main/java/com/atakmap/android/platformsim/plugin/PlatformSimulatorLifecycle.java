package com.atakmap.android.platformsim.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.platformsim.PlatformSimulatorMapComponent;
import android.content.Context;


/**
 *
 * 
 *
 */
public class PlatformSimulatorLifecycle extends AbstractPlugin {

   private final static String TAG = "PlatformSimulatorLifecycle";

   public PlatformSimulatorLifecycle(IServiceController serviceController) {
        super(serviceController, new PlatformSimulatorTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new PlatformSimulatorMapComponent());
    }
}

