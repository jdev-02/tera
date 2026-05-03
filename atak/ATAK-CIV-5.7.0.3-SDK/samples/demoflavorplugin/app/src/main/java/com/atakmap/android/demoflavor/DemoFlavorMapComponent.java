
package com.atakmap.android.demoflavor;

import android.content.Context;
import android.content.Intent;

import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.dropdown.DropDownMapComponent;

import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.android.demoflavor.plugin.R;

import java.io.IOException;
import java.io.InputStream;

public class DemoFlavorMapComponent extends DropDownMapComponent {

    private static final String TAG = "DemoFlavorMapComponent";

    private DemoFlavorDropDownReceiver ddr;
    private static CalculationProvider calculationProvider;


    public interface CalculationProvider {
        int calculate();
    }

    /**
     * In my imaginary plugin I am supplying different calculations for different flavors
     * @param c the calculation provider
     */
    public static void setCalculationProvider(CalculationProvider c) {
        calculationProvider = c;
    }

    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        context.setTheme(R.style.ATAKPluginTheme);
        super.onCreate(context, intent, view);

        ddr = new DemoFlavorDropDownReceiver(
                view, context);

        Log.d(TAG, "registering the plugin filter");
        DocumentedIntentFilter ddFilter = new DocumentedIntentFilter();
        ddFilter.addAction(DemoFlavorDropDownReceiver.SHOW_PLUGIN);
        registerDropDownReceiver(ddr, ddFilter);

        FlavorSpecificClass cf = new FlavorSpecificClass();
        Log.d(TAG, cf.getString());

        InputStream is =
                FileSystemUtils.getInputStreamFromAsset(context, "license.txt");
        try {
            FileSystemUtils.copyStreamToString(is, true, FileSystemUtils.UTF8_CHARSET);
        } catch (IOException e) {
            Log.e(TAG, "could not find the license.txt asset file");
        }

        runFlavorSpecificComputation();
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        super.onDestroyImpl(context, view);
    }

    private void runFlavorSpecificComputation() {
        if (calculationProvider != null) {
            int i = calculationProvider.calculate();
            double d = i / 2.0d;
            double e = Math.sin(d);
            Log.e(TAG, "variables: " + i + " " + d + " " + e);
        }
    }

}
