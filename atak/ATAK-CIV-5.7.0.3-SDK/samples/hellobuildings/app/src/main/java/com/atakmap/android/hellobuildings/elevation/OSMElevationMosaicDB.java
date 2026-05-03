
package com.atakmap.android.hellobuildings.elevation;

import java.io.File;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.Set;

import com.atakmap.android.hellobuildings.datastore.OSMBuildingClient;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.database.RowIteratorWrapper;
import com.atakmap.map.elevation.ElevationData;
import com.atakmap.map.elevation.ElevationDataSpi;
import com.atakmap.map.layer.feature.DataStoreException;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureCursor;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.GeometryFactory;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.ImageInfo;
import com.atakmap.map.layer.raster.mosaic.MosaicDatabase2;
import com.atakmap.map.layer.raster.osm.OSMUtils;

public class OSMElevationMosaicDB implements ElevationDataSpi {


    private final static Geometry world = DatasetDescriptor
            .createSimpleCoverage(
                    new GeoPoint(90, -180),
                    new GeoPoint(90, 180),
                    new GeoPoint(-90, 180),
                    new GeoPoint(-90, -180));

    private final static MosaicDatabase2.Coverage worldCov = new MosaicDatabase2.Coverage(
            GeometryFactory
                    .fromEnvelope(new Envelope(-180d, -90d, 0d, 180d, 90d, 0d)),
            OSMUtils.mapnikTileResolution(OSMBuildingClient.MIN_DISPLAY_LEVEL),
            OSMUtils.mapnikTileResolution(OSMBuildingClient.MIN_DISPLAY_LEVEL));

    private FeatureDataStore2 dataStore;

    private Set<Thread> queryThreads = Collections
            .newSetFromMap(new IdentityHashMap<Thread, Boolean>());

    public OSMElevationMosaicDB(FeatureDataStore2 ds) {
        dataStore = ds;
    }

    // Required so that proguard does not mash the implementation of getType with the 
    // ElevationDataSpi.

    public class OSMMosaicDatabase implements MosaicDatabase2 {

        @Override
        public String getType() {
            return "OSM";
        }

        @Override
        public void open(File f) {
        }

        @Override
        public void close() {
        }

        @Override
        public Coverage getCoverage() {
            return worldCov;
        }

        @Override
        public void getCoverages(Map<String, Coverage> coverages) {
            coverages.put(getType(), worldCov);
        }

        @Override
        public Coverage getCoverage(String type) {
            if (type == null)
                return worldCov;
            if (!type.equals(getType()))
                return null;
            // XXX - efficiency
            Map<String, Coverage> covs = new HashMap<String, Coverage>();
            this.getCoverages(covs);
            return covs.get(type);
        }
    
        @Override
        public synchronized Cursor query(QueryParameters params) {
            if (queryThreads.contains(Thread.currentThread()))
                return MosaicDatabase2.Cursor.EMPTY;
    
            Envelope mbb;
    
            if (params != null) {
                if (params.spatialFilter != null)
                    mbb = params.spatialFilter.getEnvelope();
                else
                    mbb = world.getEnvelope();
    
                if (params.types != null && !params.types.contains(getType()))
                    return MosaicDatabase2.Cursor.EMPTY;
                if (!Double.isNaN(params.minGsd) && worldCov.maxGSD > params.minGsd)
                    return MosaicDatabase2.Cursor.EMPTY;
                if (!Double.isNaN(params.maxGsd) && worldCov.minGSD < params.maxGsd)
                    return MosaicDatabase2.Cursor.EMPTY;
            } else {
                mbb = world.getEnvelope();
            }
    
            return new CursorImpl(mbb, Thread.currentThread());
        }
    }
    private FeatureCursor query(Envelope mbb) {
        FeatureDataStore2.FeatureQueryParameters params = new FeatureDataStore2.FeatureQueryParameters();
        if (mbb != null)
            params.spatialFilter = GeometryFactory.fromEnvelope(mbb);
        params.featureSetFilter = new FeatureDataStore2.FeatureSetQueryParameters();
        params.featureSetFilter.maxResolution = OSMUtils
                .mapnikTileResolution(OSMBuildingClient.MIN_DISPLAY_LEVEL);
        try {
            return dataStore.queryFeatures(params);
        } catch (DataStoreException e) {
            return FeatureCursor.EMPTY;
        }
    }

    private class CursorImpl extends RowIteratorWrapper implements MosaicDatabase2.Cursor {

        private Feature rowData;
        private Envelope rowDataBounds;
        private Thread queryThread;

        CursorImpl(final Envelope mbb, Thread queryThread) {
            super(query(mbb));
            this.queryThread = queryThread;

            synchronized (OSMElevationMosaicDB.this) {
                queryThreads.add(queryThread);
            }
        }

        @Override
        public void close() {
            synchronized (OSMElevationMosaicDB.this) {
                queryThreads.remove(queryThread);
            }
        }

        @Override
        public boolean moveToNext() {
            this.rowData = null;
            this.rowDataBounds = null;
            if (!super.moveToNext())
                return false;
            this.rowData = ((FeatureCursor) this.filter).get();
            final Geometry g = this.rowData.getGeometry();
            if (g != null)
                this.rowDataBounds = g.getEnvelope();
            return true;
        }

        @Override
        public GeoPoint getUpperLeft() {
            return new GeoPoint(this.getMaxLat(), this.getMinLon());
        }

        @Override
        public GeoPoint getUpperRight() {
            return new GeoPoint(this.getMaxLat(), this.getMaxLon());
        }

        @Override
        public GeoPoint getLowerRight() {
            return new GeoPoint(this.getMinLat(), this.getMaxLon());
        }

        @Override
        public GeoPoint getLowerLeft() {
            return new GeoPoint(this.getMinLat(), this.getMinLon());
        }

        @Override
        public double getMinLat() {
            return this.rowDataBounds.minY;
        }

        @Override
        public double getMinLon() {
            return this.rowDataBounds.minX;
        }

        @Override
        public double getMaxLat() {
            return this.rowDataBounds.maxY;
        }

        @Override
        public double getMaxLon() {
            return this.rowDataBounds.maxX;
        }

        @Override
        public String getPath() {
            return "OSM::" + String.format("%8X", dataStore.hashCode()) + "::"
                    + String.format("%8X", rowData.getId());
        }

        @Override
        public String getType() {
            return getType();
        }

        @Override
        public double getMinGSD() {
            return worldCov.minGSD;
        }

        @Override
        public double getMaxGSD() {
            return worldCov.maxGSD;
        }

        @Override
        public int getWidth() {
            // XXX - 
            return 0;
        }

        @Override
        public int getHeight() {
            // XXX - 
            return 0;
        }

        @Override
        public int getId() {
            return (int) this.rowData.getId();
        }

        @Override
        public int getSrid() {
            return 4326;
        }

        @Override
        public boolean isPrecisionImagery() {
            return false;
        }

        @Override
        public MosaicDatabase2.Frame asFrame() {
            return new MosaicDatabase2.Frame(this);
        }
    }

    @Override
    public ElevationData create(ImageInfo object) {
        if (!object.path
                .matches("OSM\\:\\:[\\da-fA-F]{1,8}\\:\\:[\\da-fA-F]{1,16}"))
            return null;
        String[] splits = object.path.split("::");
        try {
            final int dsIf = Integer.parseInt(splits[1], 16);
            if (dsIf != dataStore.hashCode())
                return null;
            FeatureDataStore2.FeatureQueryParameters params = new FeatureDataStore2.FeatureQueryParameters();
            params.ids = Collections
                    .singleton(Long.valueOf(Long.parseLong(splits[2], 16)));
            params.limit = 1;
            FeatureCursor result = null;
            try {
                result = dataStore.queryFeatures(params);
                if (!result.moveToNext())
                    return null;
                return new BuildingElevationData(result.get());
            } catch (DataStoreException e) {
                return null;
            } finally {
                if (result != null)
                    result.close();
            }
        } catch (NumberFormatException e) {
            return null;
        }
    }

    @Override
    public int getPriority() {
        return 1;
    }
}
