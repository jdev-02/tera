package com.atakmap.android.metricsapi.plugin.categories;

import android.os.Bundle;
import android.view.InputEvent;
import android.view.KeyEvent;

import androidx.annotation.NonNull;

import com.atakmap.android.metrics.MetricsUtils;

public class ActivityCategory extends Category {


    final public String clazz;

    /**
     * one of onCreate, onStart, onStop, onDestroy set when the activity is moving through states
     * otherwise null
     */
    final public String state;


    /**
     * If the activity has performed a key event which can either be a motion event or a key event
     * and would be considered null if there are no events associated with this activity category
     */
    final public InputEvent keyEvent;


    public ActivityCategory(Bundle bundle) {
        clazz = bundle.getString(MetricsUtils.FIELD_CLASS);
        state = bundle.getString(MetricsUtils.FIELD_STATE);
        keyEvent = bundle.getParcelable(MetricsUtils.FIELD_KEYEVENT);
    }


    @NonNull
    @Override
    public String toString() {
        return "ActivityCategory{" +
                "clazz='" + clazz + '\'' +
                ", state='" + state + '\'' +
                ", keyEvent=" + keyEvent +
                '}';
    }
}
