package com.atakmap.android.elevation.dsm.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.elevation.dsm.DSMMapComponent;

import gov.tak.api.plugin.IServiceController;


/**
 *
 * 
 *
 */
public class DSMManagerLifecycle extends AbstractPlugin {

   private final static String TAG = "DSMManagerLifecycle";

   public DSMManagerLifecycle(IServiceController serviceController) {
        super(serviceController, new DSMManagerTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new DSMMapComponent());
    }
}

