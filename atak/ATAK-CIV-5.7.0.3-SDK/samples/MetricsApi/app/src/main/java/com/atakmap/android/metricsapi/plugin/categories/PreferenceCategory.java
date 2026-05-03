package com.atakmap.android.metricsapi.plugin.categories;

import android.os.Bundle;
import android.view.InputEvent;

import androidx.annotation.NonNull;

import com.atakmap.android.metrics.MetricsUtils;

public class PreferenceCategory extends Category {


    final public String eventPreferenceClicked;
    final public String key;

    public PreferenceCategory(Bundle bundle) {
        eventPreferenceClicked = bundle.getString(MetricsUtils.EVENT_PREFERENCE_CLICKED);
        key = bundle.getString(MetricsUtils.FIELD_INFO);
    }

    @NonNull
    @Override
    public String toString() {
        return "PreferenceCategory{" +
                "eventPreferenceClicked='" + eventPreferenceClicked + '\'' +
                ", key='" + key + '\'' +
                '}';
    }
}
