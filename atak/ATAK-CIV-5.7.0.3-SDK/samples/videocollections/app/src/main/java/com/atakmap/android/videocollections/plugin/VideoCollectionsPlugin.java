package com.atakmap.android.videocollections.plugin;

import android.content.Context;

import com.atak.plugins.impl.PluginContextProvider;
import com.atakmap.android.cot.detail.CotDetailManager;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.menu.MapMenuReceiver;
import com.atakmap.android.videocollections.plugin.ui.VideoCollectionsInfoPane;
import com.atakmap.android.videocollections.plugin.ui.VideoMenuFactory;

import gov.tak.api.plugin.IPlugin;
import gov.tak.api.plugin.IServiceController;

public class VideoCollectionsPlugin implements IPlugin {

    Context pluginCtx;
    final VideoCollectionsInfoPane infoPane;
    final VideoCollectionsDetailHandler detailHandler;
    final VideoMenuFactory menuFactory;

    public VideoCollectionsPlugin(IServiceController serviceController) {
        final PluginContextProvider ctxProvider = serviceController
                .getService(PluginContextProvider.class);
        if (ctxProvider != null) {
            pluginCtx = ctxProvider.getPluginContext();
            pluginCtx.setTheme(R.style.ATAKPluginTheme);
        }
        infoPane = new VideoCollectionsInfoPane(MapView.getMapView(), pluginCtx);
        detailHandler = new VideoCollectionsDetailHandler();
        menuFactory = new VideoMenuFactory(pluginCtx, infoPane);
    }

    @Override
    public void onStart() {
        CotDetailManager.getInstance().registerHandler(detailHandler);
        MapMenuReceiver.getInstance().registerMapMenuFactory(menuFactory);
    }

    @Override
    public void onStop() {
        CotDetailManager.getInstance().unregisterHandler(detailHandler);
        MapMenuReceiver.getInstance().unregisterMapMenuFactory(menuFactory);
    }
}