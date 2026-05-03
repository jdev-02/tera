package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.util.AttributeSet;
import android.widget.LinearLayout;

import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.radialmenudemo.plugin.R;

import java.util.List;

public class AlertPrefsView extends LinearLayout {

    public AlertPrefsView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    void populateLayout(MapMenuButtonWidget buttonWidget) {

        AlertPrefsListView keyView = (AlertPrefsListView) findViewById(R.id.prefKeys);
        keyView.populateLayout(R.string.prefsKeys, buttonWidget.getPrefKeys());
        AlertPrefsListView valueView = (AlertPrefsListView) findViewById(R.id.prefValues);
        valueView.populateLayout(R.string.prefsValues, buttonWidget.getPrefValues());
    }

    List<String> getPrefKeys() {
        AlertPrefsListView keyView = (AlertPrefsListView) findViewById(R.id.prefKeys);
        return keyView.get();
    }

    List<String> getPrefValues() {
        AlertPrefsListView valueView = (AlertPrefsListView) findViewById(R.id.prefValues);
        return valueView.get();
    }
}
