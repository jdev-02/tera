
package com.atakmap.android.metricsapi.plugin;

import android.content.BroadcastReceiver;
import android.content.Context;

import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.metrics.MetricsApi;

import gov.tak.api.plugin.IPlugin;
import gov.tak.api.plugin.IServiceController;
import gov.tak.api.ui.IHostUIService;

public class MetricApiPlugin implements IPlugin {

    IServiceController serviceController;
    Context pluginContext;

    BroadcastReceiver br;

    public MetricApiPlugin(IServiceController serviceController) {
        this.serviceController = serviceController;
        final PluginContextProvider ctxProvider = serviceController
                .getService(PluginContextProvider.class);
        if (ctxProvider != null) {
            pluginContext = ctxProvider.getPluginContext();
            pluginContext.setTheme(R.style.ATAKPluginTheme);
        }


    }

    @Override
    public void onStart() {


        MetricsApi.register(br = new MetricsBroadcastReceiver());
    }

    @Override
    public void onStop() {

        MetricsApi.unregister(br);
    }


}
