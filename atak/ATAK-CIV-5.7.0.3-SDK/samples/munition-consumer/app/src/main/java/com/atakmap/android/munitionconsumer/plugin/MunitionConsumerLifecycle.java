
package com.atakmap.android.munitionconsumer.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.munitionconsumer.MunitionConsumerMapComponent;


/**
 *
 * AbstractPluginLifeCycle shipped with
 *     the plugin.
 */
public class MunitionConsumerLifecycle extends AbstractPlugin {

    private final static String TAG = "MunitionConsumerLifecycle";

    public MunitionConsumerLifecycle(IServiceController serviceController) {
        super(serviceController, new MunitionConsumerTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new MunitionConsumerMapComponent());
        PluginNativeLoader.init(serviceController.getService(PluginContextProvider.class).getPluginContext());
    }

}
