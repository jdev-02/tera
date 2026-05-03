package com.atakmap.android.hellobuildings.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.hellobuildings.HelloBuildingsMapComponent;
import android.content.Context;


/**
 *
 * 
 *
 */
public class HelloBuildingsLifecycle extends AbstractPlugin {

   private final static String TAG = "HelloBuildingsLifecycle";

   public HelloBuildingsLifecycle(IServiceController serviceController) {
        super(serviceController, new HelloBuildingsMapComponent());
    }
}

