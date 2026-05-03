package com.atakmap.android.metricsapi.plugin.categories;

import android.os.Bundle;
import android.view.InputEvent;

import androidx.annotation.NonNull;

import com.atakmap.android.maps.MapItem;
import com.atakmap.android.metrics.MetricsUtils;

public class ToolCategory extends Category {


    final public String clazz;

    final public String event;

    final public String elementName;

    final public String info;

    final public String mapItemType;

    final public String pallet;

    final public String pallet_name;

    final public String value;

    public ToolCategory(Bundle bundle) {
        clazz = bundle.getString(MetricsUtils.FIELD_CLASS);
        event = bundle.getString(MetricsUtils.FIELD_EVENT);
        elementName = bundle.getString(MetricsUtils.FIELD_ELEMENT_NAME);
        info = bundle.getString(MetricsUtils.FIELD_INFO);
        mapItemType  = bundle.getString(MetricsUtils.FIELD_MAPITEM_TYPE);
        pallet = bundle.getString("pallet");
        pallet_name = bundle.getString("pallet_name");
        value = bundle.getString("value");
    }


    @Override
    public String toString() {
        return "ToolCategory{" +
                "clazz='" + clazz + '\'' +
                ", event='" + event + '\'' +
                ", elementName='" + elementName + '\'' +
                ", info='" + info + '\'' +
                ", mapItemType='" + mapItemType + '\'' +
                ", pallet='" + pallet + '\'' +
                ", pallet_name='" + pallet_name + '\'' +
                ", value='" + value + '\'' +
                '}';
    }
}
