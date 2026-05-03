
package com.atakmap.android.demoflavor.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.demoflavor.DemoFlavorMapComponent;


/**
 *
 * AbstractPluginLifeCycle shipped with
 *     the plugin.
 */
public class DemoFlavorLifecycle extends AbstractPlugin {

    private final static String TAG = "DemoFlavorLifecycle";

    public DemoFlavorLifecycle(IServiceController serviceController) {
        super(serviceController, new DemoFlavorTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new DemoFlavorMapComponent());
        PluginNativeLoader.init(serviceController.getService(PluginContextProvider.class).getPluginContext());
    }

}
