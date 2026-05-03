package com.atakmap.android.radialmenudemo;

import com.atakmap.android.maps.MapItem;
import com.atakmap.android.menu.MapMenuWidget;

import java.util.LinkedList;
import java.util.List;

public class MenuWidgetFactoryObserver extends MenuWidgetFactory {

    private static final String TAG = MenuWidgetFactoryObserver.class
            .getSimpleName();

    public interface MapMenuFactoryListener {
        boolean onMenuWidgetCreation(MapMenuWidget menuWidget, MapItem mapItem);
    }

    private final List<MapMenuFactoryListener> listeners;

    public MenuWidgetFactoryObserver() {
        super();

        listeners = new LinkedList<>();
    }

    @Override
    public MapMenuWidget create(MapItem mapItem) {
        MapMenuWidget menuWidget = super.create(mapItem);
        for(MapMenuFactoryListener listener : listeners) {
            if (listener.onMenuWidgetCreation(menuWidget, mapItem))
                break;
        }

        return menuWidget;
    }

    boolean registerMapMenuFactoryListener(MapMenuFactoryListener listener) {
        boolean result = false;
        if (!listeners.contains(listener)) {
            listeners.add(0, listener);
            result = true;
        }
        return result;
    }

    boolean unregisterMapMenuFactoryListener(MapMenuFactoryListener listener) {
        return listeners.remove(listener);
    }
}
