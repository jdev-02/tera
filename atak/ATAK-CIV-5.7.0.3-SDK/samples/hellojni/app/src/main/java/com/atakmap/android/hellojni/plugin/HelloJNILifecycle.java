package com.atakmap.android.hellojni.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.hellojni.HelloJNIMapComponent;
import android.content.Context;


/**
 *
 * 
 *
 */
public class HelloJNILifecycle extends AbstractPlugin {

   private final static String TAG = "HelloJNILifecycle";

   public HelloJNILifecycle(IServiceController serviceController) {
        super(serviceController, new HelloJNITool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new HelloJNIMapComponent());
    }
}

