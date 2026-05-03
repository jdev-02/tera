package com.atakmap.android.customtiles;

import com.atakmap.android.features.FeatureDataStoreDeepMapItemQuery;
import com.atakmap.android.features.FeatureDataStoreMapOverlay;
import com.atakmap.android.layers.LayersMapComponent;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.overlay.MapOverlay;
import com.atakmap.android.overlay.MapOverlayParent;
import com.atakmap.coremap.log.Log;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.FeatureLayer3;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.RasterDataStore;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.Map;

/**
 * Monitors the imagery holdings in ATAK and manages feature data (AOIs and POIs) contained within
 * Custom Tiles datasets.
 *
 * Created by Developer on 8/22/2018.
 */
public class CustomTilesMonitor implements RasterDataStore.OnDataStoreContentChangedListener {

    private MapView map;
    private Map<String, DatasetInfo> datasets;
    private MapOverlayParent customTilesOverlayRoot;

    public CustomTilesMonitor(MapView map) {
        this.map = map;
        this.customTilesOverlayRoot = new MapOverlayParent(this.map,
                                                          "Custom Tiles",
                                                          "Custom Tiles",
                                                          null,
                                                          -1,
                                                          false);

        this.map.getMapOverlayManager().addOverlay(this.customTilesOverlayRoot);
        this.datasets = new HashMap<String, DatasetInfo>();
    }

    /**
     * Starts monitoring. Any currently ingested Custom Tiles datasets will undergo feature
     * extraction. A callback listener will be installed on the imagery data store to and any newly
     * added Custom Tiles datasets will be processed.
     */
    public void start() {
        RasterDataStore ds = LayersMapComponent.getLayersDatabase();
        if(ds != null) {
            ds.addOnDataStoreContentChangedListener(this);
            this.onDataStoreContentChanged(ds);
        }
    }

    /**
     * Stops monitoring.
     */
    public void stop() {
        RasterDataStore ds = LayersMapComponent.getLayersDatabase();
        if(ds != null) {
            ds.removeOnDataStoreContentChangedListener(this);
        }
    }

    @Override
    public synchronized void onDataStoreContentChanged(RasterDataStore rasterDataStore) {
        RasterDataStore.DatasetDescriptorCursor result = null;
        try {
            // set up a query filter that will return datasets with our dataset type
            RasterDataStore.DatasetQueryParameters params = new RasterDataStore.DatasetQueryParameters();
            params.datasetTypes = Collections.<String>singleton(CustomTilesDatasetDescriptorSpi.DATASET_TYPE);

            // copy the currently tracked items into an "invalid" map. we'll use this to track any
            // datasets that have been removed so we can cleanup
            Map<String, DatasetInfo> invalid = new HashMap<String, DatasetInfo>(datasets);
            Collection<DatasetDescriptor> toAdd = new LinkedList<DatasetDescriptor>();
            // query the data store
            result = rasterDataStore.queryDatasets(params);
            while(result.moveToNext()) {
                DatasetDescriptor desc = result.get();

                // if we have an entry for the dataset, remove it from the invalid list, if not, add
                // it to the list of items to be added
                if(invalid.remove(desc.getUri()) == null)
                    toAdd.add(desc);
            }

            // any items in 'invalid' are no longer present, remove them
            for(DatasetInfo info : invalid.values()) {
                // remove from the Overlay Manager
                this.customTilesOverlayRoot.remove(info.listItem);
                // remove the layer from the Map
                this.map.removeLayer(MapView.RenderStack.MAP_SURFACE_OVERLAYS, info.features);
            }

            // XXX - add all items in 'toAdd'
            for(DatasetDescriptor desc : toAdd) {
                // extract the features from the dataset
                FeatureDataStore2 features = CustomTilesFeatureExtractor.extractFeatures(desc.getUri());
                // if no features were available, continue
                if(features == null)
                    continue;

                // create the data structure we are using to keep track of the features and menu
                // item we are associating with a dataset
                DatasetInfo info = new DatasetInfo();
                info.features = new FeatureLayer3(desc.getName(), features);
                info.listItem = new FeatureDataStoreMapOverlay(this.map.getContext(), features, null, desc.getName(), null, new FeatureDataStoreDeepMapItemQuery(info.features), null, null);

                // add the features layer to the map
                this.map.addLayer(MapView.RenderStack.MAP_SURFACE_OVERLAYS, info.features);
                // add the submenu to the Overlay Manager
                this.map.getMapOverlayManager().addOverlay(this.customTilesOverlayRoot, info.listItem);

                // update our bookkeeping
                this.datasets.put(desc.getUri(), info);
            }
        } catch(Throwable t) {
            Log.e("CustomTilesMonitor", "Unexpected error updating monitored items", t);
        } finally {
            if(result != null)
                result.close();
        }
    }

    private static class DatasetInfo {
        public MapOverlay listItem;
        public FeatureLayer3 features;
    }
}
