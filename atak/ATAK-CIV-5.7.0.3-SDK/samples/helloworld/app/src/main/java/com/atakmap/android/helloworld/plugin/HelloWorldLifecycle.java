
package com.atakmap.android.helloworld.plugin;

import com.atak.plugins.impl.AbstractPlugin;
import com.atak.plugins.impl.PluginContextProvider;
import gov.tak.api.plugin.IServiceController;
import com.atakmap.android.helloworld.HelloWorldMapComponent;

public class HelloWorldLifecycle extends AbstractPlugin {

    public HelloWorldLifecycle(IServiceController serviceController) {
        super(serviceController, new HelloWorldTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new HelloWorldMapComponent());
    }
}
