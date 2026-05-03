package com.atakmap.android.metricsapi.plugin;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;

import com.atakmap.android.metrics.MetricsApi;
import com.atakmap.android.metricsapi.plugin.categories.Category;

public class MetricsBroadcastReceiver extends BroadcastReceiver {

    private final static String TAG = "MetricsBroadcastReceiver";


    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null)
            return;

        final String action = intent.getAction();
        final Bundle extras = intent.getExtras();


        if (extras == null)
            return;


        final String category = extras.getString(MetricsApi.METRIC_KEY_CATEGORY);
        final Bundle bundle = extras.getBundle(MetricsApi.METRIC_KEY_BUNDLE);
        if (category == null || bundle == null)
            return;

        Category c = Category.create(category, bundle);
        if (c != null)
            Log.d(TAG, "metric captured: " + c);
        else
            Log.d(TAG, "unidentified: " + bundle);
    }
}
