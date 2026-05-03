
package com.atakmap.android.windconsumer.plugin;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.windconsumer.WindConsumerDropDownReceiver;
import android.content.Context;
import gov.tak.api.util.Disposable;


public class WindConsumerTool extends AbstractPluginTool implements Disposable {

    public WindConsumerTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                WindConsumerDropDownReceiver.SHOW_PLUGIN);
    }

    @Override
    public void dispose() {
    }
}
