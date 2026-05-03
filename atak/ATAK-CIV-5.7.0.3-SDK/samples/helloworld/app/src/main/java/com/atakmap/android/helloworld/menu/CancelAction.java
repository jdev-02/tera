
package com.atakmap.android.helloworld.menu;

import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.Intent;

import com.atakmap.android.action.MapAction;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;

import gov.tak.api.widgets.IMapMenuButtonWidget;

public class CancelAction implements MapAction, IMapMenuButtonWidget.OnButtonClickHandler {

    final static String[] cancelIntents = {
            "com.atakmap.android.maps.UNFOCUS",
            "com.atakmap.android.maps.HIDE_DETAILS",
            "com.atakmap.android.maps.HIDE_MENU"
    };

    final DialogInterface.OnClickListener handler = new DialogInterface.OnClickListener() {
        @Override
        public void onClick(DialogInterface dialog, int which) {
            for (String cancel : cancelIntents) {
                Intent intent = new Intent(cancel);
                AtakBroadcast.getInstance().sendBroadcast(intent);
            }
        }
    };

    @Override
    public boolean isSupported(Object opaque) {
        return (opaque == null) || (opaque instanceof MapItem);
    }

    @Override
    public void performAction(Object opaque) {
        if (isSupported(opaque))
            performAction(MapView.getMapView(), (MapItem) opaque);
    }

    @Override
    public void performAction(MapView mapView, MapItem mapItem) {

        AlertDialog.Builder alertBuilder = new AlertDialog.Builder(
                mapView.getContext());
        alertBuilder.setTitle("Example Action");
        alertBuilder.setMessage("Can you hear me now?");

        final AlertDialog alertDialog = alertBuilder.create();
        alertDialog.setButton(AlertDialog.BUTTON_POSITIVE, "OK", handler);
        alertDialog.setCancelable(true);
        alertDialog.show();
    }
}
