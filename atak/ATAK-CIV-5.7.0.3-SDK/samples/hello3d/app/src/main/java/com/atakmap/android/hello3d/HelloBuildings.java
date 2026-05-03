
package com.atakmap.android.hello3d;

import com.atakmap.map.layer.AbstractLayer;
import com.atakmap.map.layer.feature.FeatureDataStore;
import com.atakmap.map.layer.feature.FeatureDataStore2;

public class HelloBuildings extends AbstractLayer {

    private FeatureDataStore2 dataStore;

    public HelloBuildings(FeatureDataStore2 dataStore) {
        super("Hello Buildings");

        this.dataStore = dataStore;
    }

    public FeatureDataStore2 getDataStore() {
        return this.dataStore;
    }
}
