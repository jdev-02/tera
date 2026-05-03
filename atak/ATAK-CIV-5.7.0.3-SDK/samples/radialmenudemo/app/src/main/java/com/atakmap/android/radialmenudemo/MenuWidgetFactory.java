package com.atakmap.android.radialmenudemo;

import com.atakmap.android.action.MapAction;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.maps.assets.MapAssets;
import com.atakmap.android.menu.MapMenuFactory;
import com.atakmap.android.menu.MapMenuWidget;
import com.atakmap.android.menu.MenuMapAdapter;
import com.atakmap.android.menu.MenuResourceFactory;
import com.atakmap.coremap.log.Log;

import java.io.IOException;

public class MenuWidgetFactory implements MapMenuFactory {

    private static final String TAG = MenuWidgetFactory.class
            .getSimpleName();

    private final MenuResourceFactory defaultFactory;

    public MenuWidgetFactory() {
        final MapView mapView = MapView.getMapView();
        // using application, not plugin, assets, hence the application context
        final MapAssets mapAssets = new MapAssets(mapView.getContext());
        final MenuMapAdapter adapter = new MenuMapAdapter();
        try {
            adapter.loadMenuFilters(mapAssets, "filters/menu_filters.xml");
        } catch (IOException e) {
            Log.w(TAG, e);
        }
        defaultFactory =
                    new MenuResourceFactory(mapView, mapView.getMapData(), mapAssets, adapter);
    }

    @Override
    public MapMenuWidget create(MapItem mapItem) {
        MapMenuWidget menuWidget = defaultFactory.create(mapItem);

        return menuWidget;
    }

    public MapMenuWidget resolveMenu(String xmlResource) {
        return defaultFactory.resolveMenu(xmlResource);
    }

    public MapAction resolveAction(String xmlResource) {
        return defaultFactory.resolveAction(xmlResource);
    }
}
