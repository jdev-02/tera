package com.atakmap.android.radialmenudemo;

import android.app.AlertDialog;
import android.content.DialogInterface;

import com.atakmap.android.menu.MapMenuButtonWidget;

public class PrefsDialogHandler implements DialogInterface.OnClickListener {

    public interface CompletionHandler {
        void OnComplete(AlertPrefsView alertPrefsView,
                        MapMenuButtonWidget buttonWidget);
    }

    private final AlertPrefsView alertPrefsView;
    private final MapMenuButtonWidget buttonWidget;
    private final CompletionHandler handler;

    public PrefsDialogHandler(AlertPrefsView alertPrefsView,
                              MapMenuButtonWidget buttonWidget,
                              CompletionHandler handler) {
        this.alertPrefsView = alertPrefsView;
        this.buttonWidget = buttonWidget;
        this.handler = handler;
    }

    public PrefsDialogHandler(AlertPrefsView alertPrefsView,
                              MapMenuButtonWidget buttonWidget) {
        this(alertPrefsView, buttonWidget, null);
    }

    @Override
    public void onClick(DialogInterface dialogInterface, int which) {

        if (which == AlertDialog.BUTTON_POSITIVE) {
            buttonWidget.setPrefKeys(alertPrefsView.getPrefKeys());
            buttonWidget.setPrefValues(alertPrefsView.getPrefValues());

            if (null != handler)
                handler.OnComplete(alertPrefsView, buttonWidget);
        }
    }
}
