
package com.atakmap.android.hellobuildings;

import android.util.Log;

import com.atakmap.android.hellobuildings.datastore.OSMBuildingDataStore2;
import com.atakmap.android.hellobuildings.parser.OSMParser;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.map.layer.AbstractLayer;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.datastore.caching.CachingFeatureDataStore;

public final class BuildingsExample extends AbstractLayer {
    private final static String TAG = "BuildingsExample";

    private FeatureDataStore2 dataStore;

    public BuildingsExample() {
        super("Buildings Example");
        Log.d(TAG, "Extruded PolygonsExample");

        this.dataStore = new OSMBuildingDataStore2(
                FileSystemUtils.getItem("osmcache.buildings"),
                OSMParser.DEFAULT_SERVER);
        //this.dataStore = new OSMBuildingDataStore2(null, OSMParser.DEFAULT_SERVER);
        //this.dataStore = new CachingFeatureDataStore(this.dataStore, 1, 25000, FileSystemUtils.getItem("osmcache.buildings"));
    }

    public FeatureDataStore2 getDataStore() {
        return this.dataStore;
    }
}
