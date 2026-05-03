
package com.atakmap.android.radialmenudemo;

import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.view.View;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.ipc.DocumentedExtra;
import com.atakmap.android.maps.MapDataRef;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.menu.MapMenuWidget;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.android.widgets.MapWidget;
import com.atakmap.android.widgets.WidgetIcon;
import com.atakmap.coremap.log.Log;

import gov.tak.api.widgets.IMapMenuWidget;
import gov.tak.api.widgets.IMapWidget;

public class MenuReceiver extends BroadcastReceiver
{
    public static final String TAG = MenuReceiver.class
            .getSimpleName();

    public static final String EDIT_MENU = "com.atakmap.android.radialmenudemo.EDIT_MENU";
    public static final String ADD_BUTTON = "com.atakmap.android.radialmenudemo.ADD_BUTTON";
    public static final String DELETE_BUTTON = "com.atakmap.android.radialmenudemo.DELETE_BUTTON";

    private final Context pluginContext;
    private final Context atakContext;

    MenuDialogHandler menuDialogHandler;
    ButtonDialogHandler buttonDialogHandler;

    public MenuReceiver(final MapView mapView,
                        final Context context) {
        super();
        this.pluginContext = context;
        this.atakContext = mapView.getContext();

        AtakBroadcast.DocumentedIntentFilter menuFilter = new AtakBroadcast.DocumentedIntentFilter();
        menuFilter.addAction(EDIT_MENU,
                "Edit an existing MapMenuWidget",
                new DocumentedExtra[] {
                        new DocumentedExtra("menuWidgetHash",
                                "MapMenuWidget instance",
                                false, Integer.class)
                });
        menuFilter.addAction(ADD_BUTTON,
                "Add a new MapMenuButtonWidget to an existing MapMenuWidget",
                new DocumentedExtra[] {
                        new DocumentedExtra("menuWidgetHash",
                                "MapMenuWidget parent to new button",
                                false, Integer.class)
                });
        menuFilter.addAction(DELETE_BUTTON,
                "Remove an existing MapMenuWidget's MapMenuButtonWidget",
                new DocumentedExtra[] {
                        new DocumentedExtra("buttonWidgetHash",
                                "MapMenuWidget instance to be removed",
                                false, Integer.class)
                });
        AtakBroadcast.getInstance().registerReceiver(this, menuFilter);
    }

    public void showAlert(View alertWidgetView,
                          String alertTitle, String positiveTitle,
                          DialogInterface.OnClickListener listener) {

        AlertDialog.Builder alertBuilder = new AlertDialog.Builder(atakContext);
        alertBuilder.setTitle(alertTitle);
        alertBuilder.setView(alertWidgetView);

        final AlertDialog alertDialog = alertBuilder.create();
        alertDialog.setButton(AlertDialog.BUTTON_POSITIVE, positiveTitle, listener);
        alertDialog.setButton(AlertDialog.BUTTON_NEGATIVE, "Cancel", listener);
        alertDialog.setCancelable(true);

        Log.d(TAG, "showing menu dialog");
        alertDialog.show();
    }

    private MapMenuButtonWidget createButtonWidget(IMapMenuWidget menuWidget) {

        MapMenuButtonWidget buttonWidget = new MapMenuButtonWidget(atakContext);
        // populate with menuWidget default dimensions
        buttonWidget.setOrientation(buttonWidget.getOrientationAngle(),
                menuWidget.getInnerRadius());

        if (menuWidget instanceof MapMenuWidget) {
            buttonWidget.setButtonSize(buttonWidget.getButtonSpan(),
                    ((MapMenuWidget) menuWidget).getButtonWidth());
        }
        
        // and figure out an average weight to start with ...
        float buttonWeight = 0f;
        for (IMapWidget child : menuWidget.getChildren()) {
            if (child instanceof MapMenuButtonWidget) {
                MapMenuButtonWidget childButton = (MapMenuButtonWidget) child;
                buttonWeight += childButton.getLayoutWeight();
            }
        }
        buttonWeight /= menuWidget.getChildWidgetCount();
        buttonWidget.setLayoutWeight(buttonWeight);

        // and need a WidgetIcon; arbitrary choice here ...
        final MapDataRef mapDataRef = MapDataRef.parseUri("asset:///icons/incomplete.png");
        final WidgetIcon.Builder builder = new WidgetIcon.Builder();
        final WidgetIcon widgetIcon = builder
                .setAnchor(16, 16)
                .setSize(32, 32)
                .setImageRef(0, mapDataRef)
                .build();
        buttonWidget.setIcon(widgetIcon);

        return buttonWidget;
    }

    @Override
    public void onReceive(Context context, Intent intent) {

        final String action = intent.getAction();
        if (action == null)
            return;

        switch (action) {
            case EDIT_MENU: {
                int menuHash = intent.getIntExtra("menuWidgetHash", 0);
                if (0 == menuHash)
                    return;
                IMapMenuWidget menuWidget = WidgetResolver.resolveMenuWidget(menuHash);
                if (null == menuWidget)
                    return;

                AlertMenuView alertMenuView = (AlertMenuView) PluginLayoutInflater
                        .inflate(pluginContext, R.layout.alert_menu, null);
                alertMenuView.populateLayout(menuWidget);

                menuDialogHandler = new MenuDialogHandler(alertMenuView, menuWidget);

                showAlert(alertMenuView,
                        "Edit Menu", "Update", menuDialogHandler);
            }
            break;
            case ADD_BUTTON: {
                int menuHash = intent.getIntExtra("menuWidgetHash", 0);
                if (0 == menuHash)
                    return;
                final IMapMenuWidget menuWidget = WidgetResolver.resolveMenuWidget(menuHash);
                if (null == menuWidget)
                    return;

                final MapMenuButtonWidget buttonWidget = createButtonWidget(menuWidget);

                AlertButtonView alertButtonView = (AlertButtonView) PluginLayoutInflater
                        .inflate(pluginContext, R.layout.alert_button, null);
                alertButtonView.populateLayout(buttonWidget);

                buttonDialogHandler = new ButtonDialogHandler(alertButtonView, buttonWidget,
                        new ButtonDialogHandler.CompletionHandler() {
                            @Override
                            public void OnComplete(AlertButtonView buttonView, MapMenuButtonWidget buttonWidget) {
                                menuWidget.addChildWidget(buttonWidget);
                            }
                        });

                showAlert(alertButtonView,
                        "Add Button", "Add", buttonDialogHandler);
            }
            break;
            case DELETE_BUTTON: {
                int buttonHash = intent.getIntExtra("buttonWidgetHash", 0);
                if (0 == buttonHash)
                    return;
                MapMenuWidget parentWidget =
                        WidgetResolver.resolveButtonParentWidget(buttonHash);
                if (null == parentWidget) {
                    Log.w(TAG, "Logic error; can't resolve parentWidget for button");
                } else {
                    MapMenuButtonWidget buttonWidget =
                            WidgetResolver.resolveButtonWidget(buttonHash, parentWidget);
                    if (null == buttonWidget) {
                        Log.w(TAG, "Logic error; can't resolve buttonWidget from parent");
                    } else {
                        parentWidget.removeWidget(buttonWidget);
                    }
                }
            }
            break;
            default:
                Log.w(TAG, "Logic error; unexpected action: " + action);
                break;
        }
    }
}
