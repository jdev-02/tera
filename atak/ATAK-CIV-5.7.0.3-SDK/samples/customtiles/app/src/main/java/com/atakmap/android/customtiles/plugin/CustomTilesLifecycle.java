package com.atakmap.android.customtiles.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.customtiles.CustomTilesMapComponent;
import android.content.Context;


/**
 *
 * 
 *
 */
public class CustomTilesLifecycle extends AbstractPlugin {

   private final static String TAG = "CustomTilesLifecycle";

   public CustomTilesLifecycle(IServiceController serviceController) {
        super(serviceController, new CustomTilesMapComponent());
    }
}

