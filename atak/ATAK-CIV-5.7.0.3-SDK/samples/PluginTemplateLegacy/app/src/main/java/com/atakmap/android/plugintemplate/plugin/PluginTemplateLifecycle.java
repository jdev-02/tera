
package com.atakmap.android.plugintemplate.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.plugintemplate.PluginTemplateMapComponent;
import android.content.Context;


/**
 *
 * AbstractPluginLifeCycle shipped with
 *     the plugin.
 */
public class PluginTemplateLifecycle extends AbstractPlugin {

    private final static String TAG = "PluginTemplateLifecycle";

    public PluginTemplateLifecycle(IServiceController serviceController) {
        super(serviceController, new PluginTemplateTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new PluginTemplateMapComponent());
        PluginNativeLoader.init(serviceController.getService(PluginContextProvider.class).getPluginContext());
    }

}
