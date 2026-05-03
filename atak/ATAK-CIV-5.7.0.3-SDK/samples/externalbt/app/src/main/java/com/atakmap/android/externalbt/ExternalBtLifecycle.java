package com.atakmap.android.externalbt;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;

import android.content.Context;


/**
 *
 * 
 *
 */
public class ExternalBtLifecycle extends AbstractPlugin {

   private final static String TAG = "ExternalBtLifecycle";

   public ExternalBtLifecycle(IServiceController serviceController) {
        super(serviceController, new ExternalBtMapComponent());
    }
}

