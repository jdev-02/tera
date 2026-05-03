
package com.atakmap.android.customtiles;

import android.content.Context;
import android.content.Intent;

import com.atakmap.android.customtiles.plugin.R;
import com.atakmap.android.importexport.ImportExportMapComponent;
import com.atakmap.android.importfiles.sort.ImportResolver;
import com.atakmap.android.importfiles.task.ImportFilesTask;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.maps.AbstractMapComponent;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.dropdown.DropDownMapComponent;

import com.atakmap.map.layer.raster.DatasetDescriptorFactory2;
import com.atakmap.map.layer.raster.mobileimagery.MobileImageryRasterLayer2;
import com.atakmap.map.layer.raster.nativeimagery.NativeImageryRasterLayer2;
import com.atakmap.map.layer.raster.opengl.GLMapLayerFactory;
import com.atakmap.map.layer.raster.tilematrix.TileContainerFactory;

import java.io.File;
import java.util.Set;

/**
 * This is an example of a MapComponent within the ATAK 
 * ecosphere.   A map component is the building block for all
 * activities within the system.   This defines a concrete 
 * thought or idea. 
 */
public class CustomTilesMapComponent extends AbstractMapComponent {

    public static final String TAG = "CustomTilesMapComponent";

    private Context pluginContext;
    private CustomTilesMonitor monitor;

    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        // Set the theme.  Otherwise, the plugin will look vastly different
        // than the main ATAK experience.   The theme needs to be set 
        // programatically because the AndroidManifest.xml is not used.
        context.setTheme(R.style.ATAKPluginTheme);

        pluginContext = context;

        // register the custom renderer. When ATAK needs to render imagery for datasets with our
        // custom dataset type, our GLMapLayerSpi implementation will be invoked and create the
        // renderer
        GLMapLayerFactory.registerSpi(GLCustomTilesLayerSpi.INSTANCE);

        // register the custom tiles "dataset type" as "Mobile" imagery. Once registered, datasets
        // of the type will be displayed on the MOBILE tab of the Map Manager in ATAK.
        MobileImageryRasterLayer2.registerDatasetType(CustomTilesDatasetDescriptorSpi.DATASET_TYPE);
        NativeImageryRasterLayer2.registerDatasetType(CustomTilesDatasetDescriptorSpi.DATASET_TYPE);

        TileContainerMosaicDatabase.registerType(CustomTilesDatasetDescriptorSpi.DATASET_TYPE);

        // register the dataset parser for the custom tiles format. For the rest of the current
        // runtime -- unless unregistered -- ATAK will automatically invoke the custom
        // DatsetDescriptorSpi whenever trying to ingest an imagery file
        DatasetDescriptorFactory2.register(CustomTilesDatasetDescriptorSpi.INSTANCE);

        // register the TileContainerSpi for the custom TileContainer implementation with the
        // TileContainer factory here. For the rest of the current runtime -- unless unregistered --
        // ATAK will automatically invoke the custom TileContainerSpi whenever opening a tile
        // container
        TileContainerFactory.registerSpi(CustomTilesTileContainerSpi.INSTANCE);

        // register the format extension so the files will show up in the Import Manager. Note that
        // for this particular example, we are piggy-backing on the existing imagery framework so
        // we will use the application provided import machinery for imagery. If we were importing
        // some other new content (e.g. specific to the plugin), there are additional interfaces
        // we would want to implement and register

        // XXX - the extension registration is being done on the UI thread as it is not thread-safe.
        //       Runtime accesses of the extension list should be conducted on the UI thread so this
        //       should avoid concurrent access issues. This will be resolved in a future version of
        //       ATAK
        view.post(new Runnable() {
            public void run() {
                ImportFilesTask.registerExtension(".customtiles");
            }
        });

        AtakBroadcast.getInstance().sendBroadcast(new Intent("com.atakmap.android.maps.REFRESH_LAYER_MANAGER"));

        // Create the Custom Tiles dataset monitor and start monitoring. This will integrate any
        // features found in any Custom Tiles datasets and will listen for new datasets being added.
        this.monitor = new CustomTilesMonitor(view);
        this.monitor.start();
    }

    @Override
    public void onStart(Context context, MapView mapView) {

    }

    @Override
    public void onStop(Context context, MapView mapView) {

    }

    @Override
    public void onPause(Context context, MapView mapView) {

    }

    @Override
    public void onResume(Context context, MapView mapView) {

    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        // unwind all of the registration that occurred during 'onCreate'
        TileContainerFactory.unregisterSpi(CustomTilesTileContainerSpi.INSTANCE);
        DatasetDescriptorFactory2.unregister(CustomTilesDatasetDescriptorSpi.INSTANCE);
        GLMapLayerFactory.unregisterSpi(GLCustomTilesLayerSpi.INSTANCE);

        this.monitor.stop();
    }
}
