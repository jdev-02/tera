
package com.atakmap.android.platformsim;

import com.atakmap.android.platformsim.plugin.R;

import android.content.Context;
import android.content.Intent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;
import com.atakmap.coremap.log.Log;

import com.atakmap.android.dropdown.DropDownMapComponent;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.platformsim.plugin.ContextHelperSingleton;

public class PlatformSimulatorMapComponent extends DropDownMapComponent {
    public Context pluginContext;
    public static final String TAG = PlatformSimulatorMapComponent.class
            .getSimpleName();
    private PlatformSimulatorReceiver ddr;

    public void onCreate(final Context context, Intent intent,
            final MapView view) {
        context.setTheme(R.style.ATAKPluginTheme);
        super.onCreate(context, intent, view);
        pluginContext = context;
        ddr = new PlatformSimulatorReceiver(view, context);
        ContextHelperSingleton.getInstance().setMapView(view);

        DocumentedIntentFilter ddFilter = new DocumentedIntentFilter();
        ddFilter.addAction(PlatformSimulatorReceiver.SHOW_PLATFORM_SIM);
        this.registerReceiver(context, ddr, ddFilter);
    }

    protected void onDestroyImpl(Context context, MapView view) {
        super.onDestroyImpl(context, view);
        unregisterReceiver(context, ddr);
    }
}
