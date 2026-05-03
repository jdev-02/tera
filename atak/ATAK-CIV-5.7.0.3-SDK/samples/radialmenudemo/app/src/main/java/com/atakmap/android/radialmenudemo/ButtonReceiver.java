
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
import com.atakmap.android.maps.MapView;
import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.coremap.log.Log;

public class ButtonReceiver extends BroadcastReceiver
{
    public static final String TAG = ButtonReceiver.class
            .getSimpleName();

    public static final String EDIT_BUTTON = "com.atakmap.android.radialmenudemo.EDIT_BUTTON";
    public static final String EDIT_PROPS = "com.atakmap.android.radialmenudemo.EDIT_PROPS";

    private final Context pluginContext;
    private final Context atakContext;

    private ButtonDialogHandler buttonDialogHandler;
    private PrefsDialogHandler prefsDialogHandler;

    public ButtonReceiver(final MapView mapView,
                          final Context context) {
        super();
        this.pluginContext = context;
        this.atakContext = mapView.getContext();

        AtakBroadcast.DocumentedIntentFilter buttonFilter = new AtakBroadcast.DocumentedIntentFilter();
        buttonFilter.addAction(ButtonReceiver.EDIT_BUTTON,
                "Edit an existing MapMenuWidget's MapMenuButtonWidget",
                new DocumentedExtra[] {
                        new DocumentedExtra("buttonWidgetHash",
                                "MapMenuButtonWidget instance for editing",
                                false, Integer.class)
                });
        buttonFilter.addAction(ButtonReceiver.EDIT_PROPS,
                "Edit a MapMenuButtonWidget's properties",
                new DocumentedExtra[] {
                        new DocumentedExtra("buttonWidgetHash",
                                "MapMenuButtonWidget instance for editing",
                                false, Integer.class)
                });
        AtakBroadcast.getInstance().registerReceiver(this, buttonFilter);
    }

    MapMenuButtonWidget resolveButtonWidget(Intent intent) {
        int buttonHash = intent.getIntExtra("buttonWidgetHash", 0);
        if (0 == buttonHash)
            return null;
        MapMenuButtonWidget buttonWidget = WidgetResolver.resolveButtonWidget(buttonHash);
        return buttonWidget;
    }

    void showDialog(View dialogView, String dialogTitle,
                    DialogInterface.OnClickListener handler) {

        AlertDialog.Builder alertBuilder = new AlertDialog.Builder(atakContext);
        alertBuilder.setTitle(dialogTitle);
        alertBuilder.setView(dialogView);

        final AlertDialog alertDialog = alertBuilder.create();
        alertDialog.setButton(AlertDialog.BUTTON_POSITIVE, "Update", handler);
        alertDialog.setButton(AlertDialog.BUTTON_NEGATIVE, "Cancel", handler);
        alertDialog.setCancelable(true);

        Log.d(TAG, "showing dialog " + dialogTitle);
        alertDialog.show();
    }

    @Override
    public void onReceive(Context context, Intent intent) {

        final String action = intent.getAction();
        if (action == null)
            return;

        switch (action) {
            case EDIT_BUTTON: {
                final MapMenuButtonWidget buttonWidget = resolveButtonWidget(intent);

                if (null != buttonWidget) {
                    AlertButtonView alertButtonView = (AlertButtonView) PluginLayoutInflater
                            .inflate(pluginContext, R.layout.alert_button, null);
                    alertButtonView.populateLayout(buttonWidget);

                    buttonDialogHandler =
                            new ButtonDialogHandler(alertButtonView, buttonWidget);

                    showDialog(alertButtonView,"Edit Menu Button",
                            buttonDialogHandler);
                }
            }
            break;
            case EDIT_PROPS: {
                final MapMenuButtonWidget buttonWidget = resolveButtonWidget(intent);

                if (null != buttonWidget) {

                    AlertPrefsView alertPrefsView = (AlertPrefsView) PluginLayoutInflater
                            .inflate(pluginContext, R.layout.alert_prefs, null);
                    alertPrefsView.populateLayout(buttonWidget);

                    prefsDialogHandler =
                            new PrefsDialogHandler(alertPrefsView, buttonWidget);

                    showDialog(alertPrefsView, "Edit Pref Keys and Values",
                            prefsDialogHandler);
                }
            }
            break;
            default:
                Log.w(TAG, "Logic error; unexpected action: " + action);
                break;
        }
    }
}
