package com.atakmap.android.metricsapi.plugin.categories;

import android.content.Intent;
import android.os.Bundle;

import androidx.annotation.NonNull;

import com.atakmap.android.metrics.MetricsApi;
import com.atakmap.android.metrics.MetricsUtils;

public class MapWidgetCategory extends Category {

    final public String widgetState;
    final public String mapItemUid;
    final public String element;
    final public String state;
    final public Intent intent;
   

    public MapWidgetCategory(Bundle bundle) {
        widgetState = bundle.getString(MetricsUtils.EVENT_WIDGET_STATE);
        mapItemUid = bundle.getString(MetricsUtils.FIELD_MAPITEM_UID);
        element = bundle.getString(MetricsUtils.FIELD_ELEMENT_NAME);
        state = bundle.getString(MetricsUtils.FIELD_STATE);
        intent = bundle.getParcelable(MetricsApi.METRIC_KEY_INTENT);
    }

    @NonNull
    @Override
    public String toString() {
        return "MapWidgetCategory{" +
                "widgetState='" + widgetState + '\'' +
                ", mapItemUid='" + mapItemUid + '\'' +
                ", element='" + element + '\'' +
                ", state='" + state + '\'' +
                ", intent=" + intent +
                '}';
    }
}
