
package com.atakmap.android.windprovider;

import android.content.Context;
import android.content.Intent;

import com.atakmap.android.databridge.DatasetProvider;
import com.atakmap.android.databridge.DatasetProviderManager;
import com.atakmap.android.maps.AbstractMapComponent;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.windprovider.importwind.ImportWindManager;
import com.atakmap.android.windprovider.importwind.parsers.WindParser;
import com.atakmap.android.windprovider.plugin.R;

import java.util.ArrayList;
import java.util.List;

public class WindProviderMapComponent extends AbstractMapComponent {

    private static final String TAG = "WindProviderMapComponent";

    private Context pluginContext;

    List<DatasetProvider> providers = new ArrayList<>();


    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        context.setTheme(R.style.ATAKPluginTheme);
        pluginContext = context;


        ImportWindManager iww = ImportWindManager.getInstance(pluginContext);
        List<WindParser> windParser = iww.getOnlineImport().getParsers();
        for (WindParser parser : windParser) {
            WindDatasetProvider wdp = new WindDatasetProvider(iww.getOnlineImport(), parser, context);
            providers.add(wdp);
            DatasetProviderManager.getInstance().registerDatasetProvider(wdp);

        }

    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        super.onDestroy(context, view);
        for (DatasetProvider wdp : providers) {
            DatasetProviderManager.getInstance().unregisterDatasetProvider(wdp);
        }
        providers.clear();
    }

}
