
package com.atakmap.android.windconsumer.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.windconsumer.WindConsumerMapComponent;


/**
 *
 * AbstractPluginLifeCycle shipped with
 *     the plugin.
 */
public class WinConsumerLifecycle extends AbstractPlugin {

    private final static String TAG = "WinConsumerLifecycle";

    public WinConsumerLifecycle(IServiceController serviceController) {
        super(serviceController, new WindConsumerTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new WindConsumerMapComponent());
        PluginNativeLoader.init(serviceController.getService(PluginContextProvider.class).getPluginContext());
    }

}
