
package com.atakmap.android.importexportexample;

import android.content.Context;
import android.content.Intent;
import android.graphics.drawable.Drawable;

import com.atakmap.android.importexport.ExporterManager;
import com.atakmap.android.importexport.ImportExportMapComponent;
import com.atakmap.android.importexport.ImporterManager;
import com.atakmap.android.importexport.MarshalManager;
import com.atakmap.android.importexportexample.plugin.R;
import com.atakmap.android.importfiles.sort.ImportResolver;
import com.atakmap.android.importfiles.task.ImportFilesTask;
import com.atakmap.android.maps.AbstractMapComponent;
import com.atakmap.android.maps.MapView;

public class ImportExportExampleMapComponent extends AbstractMapComponent {
    public static Context pluginContext;
    public static final String TAG = "ImportExportExampleMapComponent";

    public void onCreate(Context context, Intent intent, MapView view) {

        //context.setTheme(R.style.ATAKPluginTheme);
        pluginContext = context;

        /*************************************/
        // register the ExFmt importer -- performs the actual import duties
        ImporterManager.registerImporter(ExFmtImporter.INSTANCE);
        // register the ExFmt marshal -- performs file format identification
        MarshalManager.registerMarshal(ExFmtMarshal.INSTANCE);
        // register the ExFmt ImportResolver -- this is the special handling
        // that occurs when the file is selected in the Import Manager. For
        // our case, we want to _import-in-place_ and defer to the Marshal
        // to identify the file type
        ImportExportMapComponent.getInstance().addImporterClass(
                ImportResolver.fromMarshal(ExFmtMarshal.INSTANCE));
        // register the extension so the files will show up in the Import
        // Manager
        ImportFilesTask.registerExtension(".exfmt");

        // register the ExFmt exporter; we need to use the `Drawable` overload
        // as the application does not have access to the plugin's `Context`
        Drawable exportIcon = context.getDrawable(R.drawable.ic_launcher);
        ExporterManager.registerExporter(
                ExFmtImporter.CONTENT_TYPE,
                exportIcon, ExFmtExporter.class);
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        // unwind our registrations
        ImporterManager.unregisterImporter(ExFmtImporter.INSTANCE);
        MarshalManager.unregisterMarshal(ExFmtMarshal.INSTANCE);
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
}
