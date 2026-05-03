package com.atakmap.android.metricsapi.plugin.categories;

import android.os.Bundle;

import com.atakmap.android.metrics.MetricsUtils;

public class Category {

    public static Category create(String category, Bundle bundle) {
        switch (category) {
            case MetricsUtils.CATEGORY_ACTIVITY:
                return new ActivityCategory(bundle);
            case MetricsUtils.CATEGORY_CHAT:
                return new ChatCategory(bundle);
            case MetricsUtils.CATEGORY_MAPITEM:
                return new MapItemCategory(bundle);
            case MetricsUtils.CATEGORY_PREFERENCE:
                return new MapItemCategory(bundle);
            case MetricsUtils.CATEGORY_MAPWIDGET:
                return new MapWidgetCategory(bundle);
            case MetricsUtils.CATEGORY_TOOL:
                return new ToolCategory(bundle);
            case MetricsUtils.CATEGORY_UNKNOWN:
            default:
                return null;

        }
    }
}
