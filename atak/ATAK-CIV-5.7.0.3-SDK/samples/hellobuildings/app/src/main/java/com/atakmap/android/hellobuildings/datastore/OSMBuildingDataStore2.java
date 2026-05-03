
package com.atakmap.android.hellobuildings.datastore;

import java.io.File;
import java.util.Arrays;
import java.util.List;

import com.atakmap.map.layer.feature.AbstractFeatureDataStore3;
import com.atakmap.map.layer.feature.AttributeSet;
import com.atakmap.map.layer.feature.DataStoreException;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureCursor;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.FeatureDefinition2;
import com.atakmap.map.layer.feature.FeatureSet;
import com.atakmap.map.layer.feature.FeatureSetCursor;
import com.atakmap.map.layer.feature.Utils;
import com.atakmap.map.layer.feature.style.Style;
import com.atakmap.map.layer.feature.datastore.caching.CachingFeatureDataStore;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.raster.osm.OSMUtils;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;

import com.atakmap.coremap.log.Log;

public final class OSMBuildingDataStore2 implements FeatureDataStore2 {

    private static String TAG = "OSMBuildingDataStore2";

    private final static List<TileMatrix.ZoomLevel> CACHE_MATRIX = Arrays
            .asList(new TileMatrix.ZoomLevel[] {
                    createZoomLevel(0, 0.01d),
    });

    private final OSMBuildingClient client;
    private final CachingFeatureDataStore cache;

    public OSMBuildingDataStore2(File cacheDir, String serverUrl) {
        this.client = new OSMBuildingClient(serverUrl, false);
        if (cacheDir != null)
            this.cache = new CachingFeatureDataStore(this.client, 1, 5000,
                    cacheDir, CACHE_MATRIX);
        else
            this.cache = null;
    }

    @Override
    public FeatureCursor queryFeatures(FeatureQueryParameters params)
            throws DataStoreException {
        boolean cacheQuery = true;
        if (params != null) {
            cacheQuery &= (params.featureSetFilter != null
                    && params.featureSetFilter.maxResolution <= OSMUtils
                            .mapnikTileResolution(
                                    OSMBuildingClient.MIN_DISPLAY_LEVEL));
        }
        if (this.cache != null && cacheQuery)
            return this.cache.queryFeatures(params);
        try { 
            return this.client.queryFeatures(params);
        } catch (Exception e) { 
            // before this would return a FileNotFoundException which is not expected.
            // if the file is not found, just consider the FeatureCursor to be empty.
            Log.d(TAG, "error has occured, returnning empty cursor", e);
            return FeatureCursor.EMPTY;
        }
    }

    @Override
    public FeatureSetCursor queryFeatureSets(FeatureSetQueryParameters params)
            throws DataStoreException {

        return this.client.queryFeatureSets(params);
    }

    @Override
    public boolean hasTimeReference() {
        return this.client.hasTimeReference();
    }

    @Override
    public long getMinimumTimestamp() {
        return this.client.getMinimumTimestamp();
    }

    @Override
    public long getMaximumTimestamp() {
        return this.client.getMaximumTimestamp();
    }

    @Override
    public String getUri() {
        return this.client.getUri();
    }

    @Override
    public boolean supportsExplicitIDs() {
        return this.client.supportsExplicitIDs();
    }

    @Override
    public boolean hasCache() {
        return this.client.hasCache() || (this.cache != null);
    }

    @Override
    public void clearCache() {
        if (this.cache != null)
            this.cache.clearCache();
        this.client.clearCache();
    }

    @Override
    public long getCacheSize() {
        long retval = this.client.getCacheSize();
        if (this.cache != null)
            retval += this.cache.getCacheSize();
        return retval;
    }

    @Override
    public void dispose() {
        if (this.cache != null)
            this.cache.dispose();
        this.client.dispose();
    }

    @Override
    public void setFeatureSetVisible(long fsid, boolean visible)
            throws DataStoreException {
        if (this.cache != null)
            this.cache.setFeatureSetVisible(fsid, visible);
        this.client.setFeatureSetVisible(fsid, visible);
    }

    @Override
    public int queryFeaturesCount(FeatureQueryParameters params)
            throws DataStoreException {
        return Utils.queryFeaturesCount(this, params);
    }

    @Override
    public int queryFeatureSetsCount(FeatureSetQueryParameters params)
            throws DataStoreException {
        return Utils.queryFeatureSetsCount(this, params);
    }

    @Override
    public long insertFeature(long fsid, long fid, FeatureDefinition2 def,
            long version)
            throws DataStoreException {

        throw new UnsupportedOperationException();
    }

    @Override
    public long insertFeature(Feature feature) throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void insertFeatures(FeatureCursor features)
            throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public long insertFeatureSet(FeatureSet featureSet)
            throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void insertFeatureSets(FeatureSetCursor featureSet)
            throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void updateFeature(long fid, int updatePropertyMask, String name,
            Geometry geometry,
            Style style, AttributeSet attributes, int attrUpdateType)
            throws DataStoreException {

        throw new UnsupportedOperationException();
    }

    @Override
    public void updateFeatureSet(long fsid, String name, double minResolution,
            double maxResolution)
            throws DataStoreException {

        throw new UnsupportedOperationException();
    }

    @Override
    public void updateFeatureSet(long fsid, String name)
            throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void updateFeatureSet(long fsid, double minResolution,
            double maxResolution)
            throws DataStoreException {

        throw new UnsupportedOperationException();
    }

    @Override
    public void deleteFeature(long fid) throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void deleteFeatures(FeatureQueryParameters params)
            throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void deleteFeatureSet(long fsid) throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void deleteFeatureSets(FeatureSetQueryParameters params)
            throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void setFeatureVisible(long fid, boolean visible)
            throws DataStoreException {
        throw new UnsupportedOperationException();
    }

    @Override
    public void setFeaturesVisible(FeatureQueryParameters params,
            boolean visible)
            throws DataStoreException {

        Utils.setFeaturesVisible(this, params, visible);
    }

    @Override
    public void setFeatureSetsVisible(FeatureSetQueryParameters params,
            boolean visible)
            throws DataStoreException {

        Utils.setFeatureSetsVisible(this, params, visible);
    }

    @Override
    public int getModificationFlags() {
        return 0;
    }

    @Override
    public int getVisibilityFlags() {
        return VISIBILITY_SETTINGS_FEATURESET;
    }

    @Override
    public void acquireModifyLock(boolean bulkModification)
            throws InterruptedException {
    }

    @Override
    public void releaseModifyLock() {
    }

    @Override
    public void addOnDataStoreContentChangedListener(
            OnDataStoreContentChangedListener l) {
        this.client.addOnDataStoreContentChangedListener(l);
        if (this.cache != null)
            this.cache.addOnDataStoreContentChangedListener(l);
    }

    @Override
    public void removeOnDataStoreContentChangedListener(
            OnDataStoreContentChangedListener l) {
        this.client.removeOnDataStoreContentChangedListener(l);
        if (this.cache != null)
            this.cache.removeOnDataStoreContentChangedListener(l);
    }

    private static TileMatrix.ZoomLevel createZoomLevel(int level, double deg) {
        TileMatrix.ZoomLevel retval = new TileMatrix.ZoomLevel();
        retval.level = level;
        retval.pixelSizeX = deg;
        retval.pixelSizeY = deg;
        retval.resolution = OSMUtils
                .mapnikTileResolution(OSMBuildingClient.MIN_DISPLAY_LEVEL);
        retval.tileWidth = 1;
        retval.tileHeight = 1;
        return retval;
    }
}
