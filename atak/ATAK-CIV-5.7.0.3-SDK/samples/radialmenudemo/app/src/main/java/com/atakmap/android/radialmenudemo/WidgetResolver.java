package com.atakmap.android.radialmenudemo;

import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.menu.MapMenuReceiver;
import com.atakmap.android.menu.MapMenuWidget;

import gov.tak.api.widgets.IMapMenuWidget;
import gov.tak.api.widgets.IMapWidget;
import gov.tak.api.widgets.IParentWidget;

// collection of brute force searches,
// but good enough for infrequent queries over small hierarchies
public class WidgetResolver {

    public static MapMenuButtonWidget
    resolveButtonWidget(final int buttonHash, final IParentWidget rootWidget) {
        for (IMapWidget childWidget : rootWidget.getChildren()) {
            if (childWidget instanceof MapMenuWidget) {
                MapMenuWidget menuWidget = (MapMenuWidget) childWidget;
                MapMenuButtonWidget buttonWidget =
                        resolveButtonWidget(buttonHash, menuWidget);
                if (null != buttonWidget)
                    return buttonWidget;
            } else if (childWidget instanceof MapMenuButtonWidget) {
                MapMenuButtonWidget buttonWidget = (MapMenuButtonWidget) childWidget;
                if (buttonHash == buttonWidget.hashCode())
                    return buttonWidget;
                IMapMenuWidget menuWidget = buttonWidget.getSubmenu();
                if (null != menuWidget) {
                    buttonWidget = resolveButtonWidget(buttonHash, menuWidget);
                    if (null != buttonWidget)
                        return buttonWidget;
                }
            }
        }
        return null;
    }

    public static MapMenuButtonWidget resolveButtonWidget(final int buttonHash) {
        return resolveButtonWidget(buttonHash, MapMenuReceiver.getMenuWidget());
    }

    public static IMapMenuWidget
    resolveMenuWidget(final int menuHash, final IParentWidget rootWidget) {
        for (IMapWidget childWidget : rootWidget.getChildren()) {
            if (childWidget instanceof MapMenuWidget) {
                IMapMenuWidget menuWidget = (MapMenuWidget) childWidget;
                if (menuHash == menuWidget.hashCode())
                    return menuWidget;
                menuWidget = resolveMenuWidget(menuHash, menuWidget);
                if (null != menuWidget)
                    return menuWidget;
            } else if (childWidget instanceof MapMenuButtonWidget) {
                MapMenuButtonWidget buttonWidget = (MapMenuButtonWidget) childWidget;
                IMapMenuWidget menuWidget = buttonWidget.getSubmenu();
                if (null != menuWidget) {
                    if (menuHash == menuWidget.hashCode()) {
                        return menuWidget;
                    } else {
                        menuWidget = resolveMenuWidget(menuHash, menuWidget);
                        if (null != menuWidget)
                            return menuWidget;
                    }
                }
            }
        }
        return null;
    }
    public static IMapMenuWidget resolveMenuWidget(final int menuHash) {
        return resolveMenuWidget(menuHash, MapMenuReceiver.getMenuWidget());
    }

    public static MapMenuWidget
    resolveButtonParentWidget(final int buttonHash, final IParentWidget rootWidget) {
        for (IMapWidget childWidget : rootWidget.getChildren()) {
            if (childWidget instanceof MapMenuWidget) {
                MapMenuWidget menuWidget = (MapMenuWidget) childWidget;
                MapMenuWidget parentWidget =
                        resolveButtonParentWidget(buttonHash, menuWidget);
                if (null != parentWidget)
                    return parentWidget;
            } else if (childWidget instanceof MapMenuButtonWidget) {
                MapMenuButtonWidget buttonWidget = (MapMenuButtonWidget) childWidget;
                if (buttonHash == buttonWidget.hashCode())
                    return (MapMenuWidget) rootWidget;
                IMapMenuWidget menuWidget = buttonWidget.getSubmenu();
                if (null != menuWidget) {
                    MapMenuWidget parentWidget =
                            resolveButtonParentWidget(buttonHash, menuWidget);
                    if (null != parentWidget)
                        return parentWidget;
                }
            }
        }
        return null;
    }

    public static MapMenuWidget resolveButtonParentWidget(final int buttonHash) {
        return resolveButtonParentWidget(buttonHash, MapMenuReceiver.getMenuWidget());
    }
}
