package com.atakmap.android.hello3d.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.hello3d.Hello3DMapComponent;
import android.content.Context;


/**
 *
 * 
 *
 */
public class Hello3DLifecycle extends AbstractPlugin {

   private final static String TAG = "Hello3DLifecycle";

   public Hello3DLifecycle(IServiceController serviceController) {
        super(serviceController, new Hello3DMapComponent());
    }
}

