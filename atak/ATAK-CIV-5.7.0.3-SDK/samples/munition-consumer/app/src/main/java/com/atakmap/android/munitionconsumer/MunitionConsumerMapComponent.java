
package com.atakmap.android.munitionconsumer;

import android.content.Context;
import android.content.Intent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.dropdown.DropDownMapComponent;

import com.atakmap.coremap.log.Log;
import com.atakmap.android.munitionconsumer.plugin.R;

public class MunitionConsumerMapComponent extends DropDownMapComponent {

    private static final String TAG = "MunitionConsumerMapComponent";

    private Context pluginContext;

    private MunitionConsumerDropDownReceiver ddr;

    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        context.setTheme(R.style.ATAKPluginTheme);
        super.onCreate(context, intent, view);
        pluginContext = context;

        ddr = new MunitionConsumerDropDownReceiver(
                view, context);

        DocumentedIntentFilter ddFilter = new DocumentedIntentFilter();
        ddFilter.addAction(MunitionConsumerDropDownReceiver.SHOW_PLUGIN);
        registerDropDownReceiver(ddr, ddFilter);
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        super.onDestroyImpl(context, view);
    }

}
