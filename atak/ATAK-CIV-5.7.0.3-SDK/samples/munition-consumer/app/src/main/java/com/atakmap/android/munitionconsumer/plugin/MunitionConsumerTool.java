
package com.atakmap.android.munitionconsumer.plugin;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.munitionconsumer.MunitionConsumerDropDownReceiver;
import android.content.Context;
import gov.tak.api.util.Disposable;


public class MunitionConsumerTool extends AbstractPluginTool implements Disposable {

    public MunitionConsumerTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                MunitionConsumerDropDownReceiver.SHOW_PLUGIN);
    }

    @Override
    public void dispose() {
    }
}
