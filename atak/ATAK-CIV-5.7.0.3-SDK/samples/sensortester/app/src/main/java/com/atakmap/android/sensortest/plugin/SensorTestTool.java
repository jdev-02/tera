
package com.atakmap.android.sensortest.plugin;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.sensortest.SensorTestDropDownReceiver;

import android.content.Context;
import gov.tak.api.util.Disposable;


public class SensorTestTool extends AbstractPluginTool implements Disposable {

    public SensorTestTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                SensorTestDropDownReceiver.SHOW_PLUGIN);
    }

    @Override
    public void dispose() {
    }
}
