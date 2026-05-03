
package com.atakmap.android.elevation.dsm;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;

import com.atakmap.android.elevation.dsm.plugin.R;
import com.atakmap.android.elevation.dsm.util.RasterLayerAdapter;
import com.atakmap.android.importexport.ImportExportMapComponent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;
import com.atakmap.android.maps.AbstractMapComponent;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.preference.AtakPreferences;
import com.atakmap.app.preferences.ToolsPreferenceFragment;
import com.atakmap.coremap.conversions.Span;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.map.elevation.ElevationData;
import com.atakmap.map.elevation.ElevationManager;

import java.io.File;

public class DSMMapComponent extends AbstractMapComponent implements
        SharedPreferences.OnSharedPreferenceChangeListener {

    public Context pluginContext;
    public static final String TAG = "DSMManagerMapComponent";

    public static final String DIRECTORY_PATH = "tools" + File.separator + "dsm";
    public static final String USER_GUIDE = "ATAK_DSM User Guide 1.0 ATAK 4.9.pdf";

    private DSMManagerDropDownReceiver receiver;
    private AtakPreferences prefs;

    private ImportDSMSort importDSMSort;

    public void onCreate(Context context, Intent intent, MapView view) {
        context.setTheme(R.style.ATAKPluginTheme);
        pluginContext = context;
        prefs = AtakPreferences.getInstance(view.getContext());
        prefs.registerListener(this);
        DSMManager.initialize();
        onSharedPreferenceChanged(prefs.getSharedPrefs(), "dsm.");

        // register data spi with elevation service
        ElevationManager.registerDataSpi(DSMElevationData.SPI);
        // register DSM DB with elevation service
        if (prefs.get("dsm.enabled", true)) {
            // evict any stale entries before showing
            DSMManager.getDb().validateCatalog();
            ElevationManager.registerElevationSource(DSMManager.getDb().dsmmdb);
        }

        // refresh on background thread
        DSMManager.refresh();

        this.receiver = new DSMManagerDropDownReceiver(view, context,
                RasterLayerAdapter.INSTANCE);
        this.registerReceiver(view.getContext(), this.receiver,
                new DocumentedIntentFilter(
                        DSMManagerDropDownReceiver.SHOW_DSM_TOOL));

        DsmManagerPreferenceFragment preferenceFragment = new DsmManagerPreferenceFragment(pluginContext);

        ToolsPreferenceFragment.register(
                new ToolsPreferenceFragment.ToolPreference(
                        "DSM Manager Preferences",
                        "Adjust the DSM Manager preferences",
                        "dsm_manager_preferences",
                        context.getResources().getDrawable(
                                R.drawable.dsm),
                        preferenceFragment));

        ImportExportMapComponent.getInstance().addImporterClass(importDSMSort = new ImportDSMSort(pluginContext));

    }

    @Override
    public void onSharedPreferenceChanged(SharedPreferences sharedPreferences, String s) {
        if (s == null)
            return;
        if (s.startsWith("dsm.")) {
            DSMManager.setDefaults(
                    getModel(prefs.get("dsm.defaultmodel", "Surface")),
                    getUnits(prefs.get("dsm.defaultunits", "meters")),
                    prefs.get("dsm.defaultreference", "HAE"));
            if (s.equals("dsm.enabled")) {
                boolean b = prefs.get(s, true);
                if (b) {
                    ElevationManager.registerElevationSource(DSMManager.getDb().dsmmdb);
                } else {
                    ElevationManager.unregisterElevationSource(DSMManager.getDb().dsmmdb);
                }
            }
        }
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        prefs.unregisterListener(this);
        ElevationManager.unregisterElevationSource(DSMManager.getDb().dsmmdb);

        ElevationManager.unregisterDataSpi(DSMElevationData.SPI);

        DSMManager.teardown();

        //unregister the preference fragment with core
        ToolsPreferenceFragment.unregister("dsm_manager_preferences");
        ImportExportMapComponent.getInstance().removeImporterClass(importDSMSort);
    }

    @Override
    public void onStart(Context context, MapView view) {
    }

    @Override
    public void onStop(Context context, MapView view) {
    }

    @Override
    public void onPause(Context context, MapView view) {
    }

    @Override
    public void onResume(Context context, MapView view) {
    }


    private int getModel(String s) {
        int editModel = ElevationData.MODEL_SURFACE;
        if (s != null) {
            if (s.equalsIgnoreCase("Terrain"))
                editModel = ElevationData.MODEL_TERRAIN;
            else if (s.equalsIgnoreCase("Terrain+Surface"))
                editModel = ElevationData.MODEL_TERRAIN
                        | ElevationData.MODEL_SURFACE;
        }
        return editModel;
    }
    private Span getUnits(String s) {
        Span span = Span.findFromPluralName(s);
        if (span == null)
            span = Span.METER;
        return span;

    }
}
