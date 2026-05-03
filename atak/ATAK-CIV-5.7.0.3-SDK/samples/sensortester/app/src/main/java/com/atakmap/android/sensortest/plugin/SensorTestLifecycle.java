
package com.atakmap.android.sensortest.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;
import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.sensortest.SensorTestMapComponent;


/**
 *
 * AbstractPluginLifeCycle shipped with
 *     the plugin.
 */
public class SensorTestLifecycle extends AbstractPlugin {

    private final static String TAG = "SensorTestLifecycle";

    public SensorTestLifecycle(IServiceController serviceController) {
        super(serviceController, new SensorTestTool(serviceController.getService(PluginContextProvider.class).getPluginContext()), new SensorTestMapComponent());
    }

}
