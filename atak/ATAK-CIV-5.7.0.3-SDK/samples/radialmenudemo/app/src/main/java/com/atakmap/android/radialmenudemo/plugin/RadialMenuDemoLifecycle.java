
package com.atakmap.android.radialmenudemo.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.radialmenudemo.RadialMenuDemoMapComponent;

public class RadialMenuDemoLifecycle extends AbstractPlugin {
    public RadialMenuDemoLifecycle(IServiceController serviceController) {
        super(serviceController, new RadialMenuDemoTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new RadialMenuDemoMapComponent());
    }
}
