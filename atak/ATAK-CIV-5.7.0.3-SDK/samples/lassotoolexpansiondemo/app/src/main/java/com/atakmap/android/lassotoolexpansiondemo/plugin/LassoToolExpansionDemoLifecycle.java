
package com.atakmap.android.lassotoolexpansiondemo.plugin;


import com.atak.plugins.impl.AbstractPlugin;
import gov.tak.api.plugin.IServiceController;

import com.atakmap.android.lassotoolexpansiondemo.LassoToolExpansionDemoMapComponent;


/**
 *
 * AbstractPluginLifeCycle shipped with
 *     the plugin.
 */
public class LassoToolExpansionDemoLifecycle extends AbstractPlugin {

    private final static String TAG = "LassoToolExpansionDemoLifecycle";

    public LassoToolExpansionDemoLifecycle(IServiceController serviceController) {
        super(serviceController, new LassoToolExpansionDemoMapComponent());
    }

}
