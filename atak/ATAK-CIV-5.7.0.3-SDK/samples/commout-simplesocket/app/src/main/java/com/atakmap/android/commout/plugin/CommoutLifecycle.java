package com.atakmap.android.commout.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.commout.CommoutMapComponent;
import android.content.Context;


/**
 *
 * 
 *
 */
public class CommoutLifecycle extends AbstractPlugin {

   private final static String TAG = "CommoutLifecycle";

   public CommoutLifecycle(IServiceController serviceController) {
        super(serviceController, new CommoutMapComponent());
    }
}

