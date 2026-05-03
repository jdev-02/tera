package com.atakmap.android.metricsapi.plugin.categories;

import android.os.Bundle;

import androidx.annotation.NonNull;

import com.atakmap.android.metrics.MetricsUtils;

public class MapItemCategory extends Category {

    final public String clazz;
    final public String event;

    final public String callsign;
    final public String mapItemUid;
    final public String mapItemType;
    final public String info;

    final public String status;
    
    final public String oldName;
    final public String newName;

    // for routes;
    final public String routingType;

    final public String action;
    final public String point;


    public MapItemCategory(Bundle bundle) {
        event = bundle.getString(MetricsUtils.FIELD_EVENT);
        clazz = bundle.getString(MetricsUtils.FIELD_CLASS);
        callsign = bundle.getString(MetricsUtils.FIELD_CALLSIGN);
        mapItemUid = bundle.getString(MetricsUtils.FIELD_MAPITEM_UID);
        mapItemType = bundle.getString(MetricsUtils.FIELD_MAPITEM_TYPE);
        oldName = bundle.getString("old_name");
        newName = bundle.getString("new_name");
        status = bundle.getString(MetricsUtils.FIELD_STATUS);
        routingType = bundle.getString("routing_type");
        info = bundle.getString(MetricsUtils.FIELD_INFO);
        action = bundle.getString("action");
        point = bundle.getString("point");
    }

    @NonNull
    @Override
    public String toString() {
        return "MapItemCategory{" +
                "clazz='" + clazz + '\'' +
                ", event='" + event + '\'' +
                ", callsign='" + callsign + '\'' +
                ", mapItemUid='" + mapItemUid + '\'' +
                ", mapItemType='" + mapItemType + '\'' +
                ", info='" + info + '\'' +
                ", status='" + status + '\'' +
                ", oldName='" + oldName + '\'' +
                ", newName='" + newName + '\'' +
                ", routingType='" + routingType + '\'' +
                ", action='" + action + '\'' +
                ", point='" + point + '\'' +
                '}';
    }
}
