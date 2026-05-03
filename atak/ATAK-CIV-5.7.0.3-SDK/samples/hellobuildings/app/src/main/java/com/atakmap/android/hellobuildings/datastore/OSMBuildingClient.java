
package com.atakmap.android.hellobuildings.datastore;

import java.io.File;
import java.io.FileOutputStream;
import java.net.URL;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;

import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;

import android.util.Log;
import android.util.LruCache;
import android.util.Pair;

import com.atakmap.android.hellobuildings.parser.Building;
import com.atakmap.android.hellobuildings.parser.BuildingList;
import com.atakmap.android.hellobuildings.parser.NodeList;
import com.atakmap.android.hellobuildings.parser.OSMParser;
import com.atakmap.android.hellobuildings.parser.ParserHandler;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.map.layer.control.AttributionControl;
import com.atakmap.map.layer.control.Controls;
import com.atakmap.map.layer.feature.AttributeSet;
import com.atakmap.map.layer.feature.DataStoreException;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureCursor;
import com.atakmap.map.layer.feature.FeatureDataSource;
import com.atakmap.map.layer.feature.FeatureDefinition2;
import com.atakmap.map.layer.feature.FeatureSetCursor;
import com.atakmap.map.layer.feature.FeatureSet;
import com.atakmap.map.layer.feature.Utils;
import com.atakmap.map.layer.feature.datastore.AbstractReadOnlyFeatureDataStore2;
import com.atakmap.map.layer.feature.datastore.RuntimeFeatureDataStore2;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.style.BasicFillStyle;
import com.atakmap.map.layer.raster.osm.OSMUtils;

public class OSMBuildingClient extends AbstractReadOnlyFeatureDataStore2
        implements Controls {

    private final static String TAG = "OSMBuildingDataStore2";

    public final static int MIN_DISPLAY_LEVEL = 17;

    private String serverUrl;

    final LruCache<Long, Boolean> featureCache;
    final RuntimeFeatureDataStore2 localCache;

    private final Set<Object> controls;
    private final boolean requireResolutionForQueries;

    public OSMBuildingClient(String baseUrl) {
        this(baseUrl, true);
    }

    OSMBuildingClient(String baseUrl, boolean requireResForQuerues) {
        super(0, VISIBILITY_SETTINGS_FEATURESET);

        this.serverUrl = baseUrl;

        this.requireResolutionForQueries = requireResForQuerues;

        this.localCache = new RuntimeFeatureDataStore2();
        this.featureCache = new LruCache<Long, Boolean>(100) {
            @Override
            protected void entryRemoved(boolean evicted, Long key,
                    Boolean oldValue,
                    Boolean newValue) {

                if (newValue == null)
                    try {
                        localCache.deleteFeature(key);
                    } catch (DataStoreException e) {
                        // XXX - no failover
                        throw new RuntimeException(e);
                    }
            }
        };

        try {
            this.localCache.insertFeatureSet(
                    new FeatureSet(1L,
                            "OSM", // what generated the features
                            "OSM", // the type of the featuers
                            "Buildings", // the feature set name
                            OSMUtils.mapnikTileResolution(MIN_DISPLAY_LEVEL), // min resolution threshold 
                            0d, // max resolution threshold
                            FEATURESET_VERSION_NONE));
        } catch (DataStoreException e) {
            // RuntimeFeatureDataStore2 won't throw
            throw new IllegalStateException(e);
        }

        this.controls = new HashSet<Object>();
        this.controls.add(new AttributionControlImpl());
    }

    @Override
    public FeatureCursor queryFeatures(FeatureQueryParameters params)
            throws DataStoreException {
        final boolean isFiltered = (params != null) &&
                (params.spatialFilter != null) &&
                (!this.requireResolutionForQueries ||
                        (params.featureSetFilter != null &&
                                params.featureSetFilter.maxResolution <= OSMUtils
                                        .mapnikTileResolution(
                                                MIN_DISPLAY_LEVEL)));

        if (!isFiltered) {
            // XXX - can't issue network calls on main thread
            return localCache.queryFeatures(params);
        }

        return new FeatureCursorImpl(params.spatialFilter.getEnvelope());
    }

    @Override
    public int queryFeaturesCount(FeatureQueryParameters params)
            throws DataStoreException {
        // XXX - 
        return Utils.queryFeaturesCount(this, params);
    }

    @Override
    public FeatureSetCursor queryFeatureSets(FeatureSetQueryParameters params)
            throws DataStoreException {
        return this.localCache.queryFeatureSets(params);
    }

    @Override
    public int queryFeatureSetsCount(FeatureSetQueryParameters params)
            throws DataStoreException {
        return Utils.queryFeatureSetsCount(this, params);
    }

    @Override
    public void dispose() {
        // TODO Auto-generated method stub

    }

    @Override
    protected boolean setFeatureVisibleImpl(long fid, boolean visible) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public void setFeaturesVisible(FeatureQueryParameters params,
            boolean visible) {
        // no-op, everything is visible
    }

    @Override
    protected boolean setFeatureSetVisibleImpl(long setId, boolean visible) {
        // TODO Auto-generated method stub
        return false;
    }

    @Override
    public void setFeatureSetsVisible(FeatureSetQueryParameters params,
            boolean visible) {
        // no-op, everything is visible
    }

    @Override
    public void clearCache() {
    }

    @Override
    public long getCacheSize() {
        return 0;
    }

    @Override
    public boolean hasCache() {
        return false;
    }

    @Override
    public boolean hasTimeReference() {
        return false;
    }

    @Override
    public long getMinimumTimestamp() {
        return 0L;
    }

    @Override
    public long getMaximumTimestamp() {
        return 0L;
    }

    @Override
    public String getUri() {
        return this.serverUrl;
    }

    @Override
    public <T> T getControl(Class<T> controlClazz) {
        for (Object ctrl : this.controls) {
            if (controlClazz.isAssignableFrom(ctrl.getClass()))
                return controlClazz.cast(ctrl);
        }
        return null;
    }

    @Override
    public void getControls(Collection<Object> controls) {
        controls.addAll(this.controls);
    }

    private final class FeatureCursorImpl
            implements FeatureCursor, FeatureDefinition2 {

        private FeatureDataSource.FeatureDefinition row;
        private long rowId;
        private long rowVersion;
        private long rowFsid;
        private Iterator<Building> impl;
        private Building rowData;

        public FeatureCursorImpl(Envelope aoi) throws DataStoreException {
            try {
                BuildingList buildings = download(serverUrl, aoi);
                if (buildings == null)
                    throw new RuntimeException("Failed to download OSM chip");
                impl = buildings.values().iterator();
            } catch (Throwable t) {
                throw new DataStoreException(t);
            }

            this.row = new FeatureDataSource.FeatureDefinition();
        }

        @Override
        public boolean moveToNext() {
            if (this.impl == null)
                return false;
            if (!this.impl.hasNext())
                return false;

            this.rowData = this.impl.next();

            // XXX - do we need to aggregate based on ID???

            this.rowFsid = 1L;
            this.rowId = this.rowData.getId();
            this.row.name = "Building " + this.rowData.getId();
            this.row.geomCoding = GEOM_ATAK_GEOMETRY;
            this.row.rawGeom = this.rowData.asPolygon(true);
            this.row.styleCoding = STYLE_ATAK_STYLE;
            this.row.rawStyle = new BasicFillStyle(0xC07F7F7F);
            this.row.attributes = new AttributeSet();
            this.rowVersion = 1L;

            // cache the feature locally for non-rendering lookups
            synchronized (OSMBuildingClient.this.featureCache) {
                Feature f = this.get();
                try {
                    if (OSMBuildingClient.this.featureCache
                            .get(this.getId()) == null)
                        localCache.insertFeature(f);
                    else
                        localCache.updateFeature(
                                this.getId(),
                                PROPERTY_FEATURE_ATTRIBUTES
                                        | PROPERTY_FEATURE_GEOMETRY
                                        | PROPERTY_FEATURE_NAME
                                        | PROPERTY_FEATURE_STYLE,
                                this.getName(),
                                f.getGeometry(),
                                f.getStyle(),
                                this.getAttributes(),
                                UPDATE_ATTRIBUTES_SET);

                    OSMBuildingClient.this.featureCache.put(this.getId(),
                            Boolean.TRUE);
                } catch (DataStoreException e) {
                    Log.w(TAG, "Failed to cache feature FID=" + f.getId()
                            + " name=" + f.getName(), e);
                }
            }

            return true;
        }

        @Override
        public void close() {
            this.impl = null;
        }

        @Override
        public boolean isClosed() {
            return (this.impl == null);
        }

        @Override
        public Object getRawGeometry() {
            return this.row.rawGeom;
        }

        @Override
        public int getGeomCoding() {
            return this.row.geomCoding;
        }

        @Override
        public String getName() {
            return this.row.name;
        }

        @Override
        public int getStyleCoding() {
            return this.row.styleCoding;
        }

        @Override
        public Object getRawStyle() {
            return this.row.rawStyle;
        }

        @Override
        public AttributeSet getAttributes() {
            return this.row.attributes;
        }

        @Override
        public Feature get() {
            Feature f = this.row.get();
            return new Feature(this.getFsid(),
                    this.getId(),
                    this.getName(),
                    f.getGeometry(),
                    f.getStyle(),
                    this.getAttributes(),
                    this.getTimestamp(),
                    this.getVersion());
        }

        @Override
        public long getId() {
            return this.rowId;
        }

        @Override
        public long getVersion() {
            return this.rowVersion;
        }

        @Override
        public long getFsid() {
            return this.rowFsid;
        }

        @Override
        public long getTimestamp() {
            // TODO Auto-generated method stub
            return 0;
        }
    }

    private class AttributionControlImpl implements AttributionControl {

        Set<Pair<String, String>> attribution;

        public AttributionControlImpl() {
            attribution = Collections
                    .singleton(Pair.create("Buildings", "(C) OpenStreetMap"));
        }

        @Override
        public Set<Pair<String, String>> getContentAttribution() {
            return this.attribution;
        }

        @Override
        public void addOnAttributionUpdatedListener(
                OnAttributionUpdatedListener l) {
            // attribution does not change, no-op
        }

        @Override
        public void removeOnAttributionUpdatedListener(
                OnAttributionUpdatedListener l) {
            // attribution does not change, no-op        }
        }
    }

    private static BuildingList download(String serverUrl, Envelope bounds)
            throws Exception {
        File cacheFile = null;
        try {
            cacheFile = File.createTempFile("osm", ".xml");

            final double sLat = bounds.minY;
            final double wLng = bounds.minX;
            final double nLat = bounds.maxY;
            final double eLng = bounds.maxX;

            long s, e;

            s = System.currentTimeMillis();
            URL url = new URL(
                    OSMParser.getOsmURI(serverUrl, sLat, wLng, nLat, eLng));
            FileSystemUtils.copyStream(url.openStream(),
                    true,
                    new FileOutputStream(cacheFile),
                    true);
            e = System.currentTimeMillis();

            Log.d(TAG, "Downloaded building tile " + nLat + "," + wLng + " "
                    + sLat + "," + eLng + " in " + (e - s) + "ms");

            SAXParserFactory factory = SAXParserFactory.newInstance();
            SAXParser saxParser;

            s = System.currentTimeMillis();
            saxParser = factory.newSAXParser();
            NodeList nl = new NodeList();
            final BuildingList bl = new BuildingList();
            final ParserHandler userhandler = new ParserHandler(nl, bl);
            saxParser.parse(cacheFile, userhandler);
            e = System.currentTimeMillis();

            Log.d(TAG, "Parsed building tile " + nLat + "," + wLng + " " + sLat
                    + "," + eLng + " in " + (e - s) + "ms");

            return bl;
        } catch (Exception t) {
            final double sLat = bounds.minY;
            final double wLng = bounds.minX;
            final double nLat = bounds.maxY;
            final double eLng = bounds.maxX;

            Log.d(TAG, "Failed to parsed building tile " + nLat + "," + wLng
                    + " " + sLat + "," + eLng, t);
            Log.d(TAG, new String(FileSystemUtils.read(cacheFile)));
            throw t;
        } finally {
            if (cacheFile != null)
                FileSystemUtils.delete(cacheFile);
        }
    }
}
