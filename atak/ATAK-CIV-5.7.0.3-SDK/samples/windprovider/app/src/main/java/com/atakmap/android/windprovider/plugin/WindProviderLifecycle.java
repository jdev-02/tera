
package com.atakmap.android.windprovider.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.windprovider.WindProviderMapComponent;


/**
 *
 * AbstractPluginLifeCycle shipped with
 *     the plugin.
 */
public class WindProviderLifecycle extends AbstractPlugin {

    private final static String TAG = "WindProviderLifecycle";

    public WindProviderLifecycle(IServiceController serviceController) {
        super(serviceController, new WindProviderMapComponent());
        PluginNativeLoader.init(serviceController.getService(PluginContextProvider.class).getPluginContext());
    }

}
