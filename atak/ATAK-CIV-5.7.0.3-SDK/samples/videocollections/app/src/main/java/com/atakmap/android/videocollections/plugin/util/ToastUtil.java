package com.atakmap.android.videocollections.plugin.util;

import android.os.Handler;
import android.widget.Toast;

import com.atakmap.android.maps.MapView;

public class ToastUtil {
    private static final Toast toast = Toast.makeText(MapView.getMapView().getContext(), "", Toast.LENGTH_LONG);

    public static final int
            LENGTH_LONG = 3000,
            LENGTH_SHORT = 1500,
            LENGTH_VERY_SHORT = 750;

    public static void show(String msg) {
        show(msg, LENGTH_SHORT);
    }

    public static void show(String msg, int duration) {
        if (duration == Toast.LENGTH_SHORT)
            duration = LENGTH_SHORT;
        if (duration == Toast.LENGTH_LONG)
            duration = LENGTH_LONG;

        toast.cancel();
        toast.setText(msg);
        toast.show();

        new Handler().postDelayed(new Runnable() {
            @Override
            public void run() {
                toast.cancel();
            }
        }, duration);
    }
}