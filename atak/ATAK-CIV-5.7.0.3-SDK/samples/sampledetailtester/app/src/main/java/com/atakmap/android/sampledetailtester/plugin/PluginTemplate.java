
package com.atakmap.android.sampledetailtester.plugin;

import android.content.Context;

import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.maps.MapComponent;
import com.atakmap.android.sampledetailtester.StudentMapComponent;

import gov.tak.api.plugin.IPlugin;
import gov.tak.api.plugin.IServiceController;

public class PluginTemplate implements IPlugin {

    IServiceController serviceController;
    StudentMapComponent pluginMapComponent;
    Context pluginContext;

    public PluginTemplate(IServiceController serviceController) {
        this.serviceController = serviceController;
        final PluginContextProvider ctxProvider = serviceController
                .getService(PluginContextProvider.class);
        if (ctxProvider != null)
            pluginContext = ctxProvider.getPluginContext();
    }

    @Override
    public void onStart() {

        pluginMapComponent = new StudentMapComponent();

        serviceController.registerComponent(MapComponent.class,
                pluginMapComponent);
    }

    @Override
    public void onStop() {
        serviceController.unregisterComponent(MapComponent.class,
                pluginMapComponent);

    }
}
