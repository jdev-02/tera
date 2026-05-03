package com.atakmap.android.customtiles;

import android.graphics.Point;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.GeometryFactory;
import com.atakmap.map.layer.raster.mosaic.MosaicDatabase2;
import com.atakmap.map.layer.raster.mosaic.MosaicDatabaseFactory2;
import com.atakmap.map.layer.raster.mosaic.MosaicDatabaseSpi2;
import com.atakmap.map.layer.raster.mosaic.MultiplexingMosaicDatabaseCursor2;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;
import com.atakmap.map.layer.raster.tilematrix.TileContainerFactory;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.map.layer.raster.tilereader.TileReaderFactory;
import com.atakmap.map.projection.Projection;
import com.atakmap.map.projection.ProjectionFactory;
import com.atakmap.math.MathUtils;
import com.atakmap.math.PointD;
import com.atakmap.math.Rectangle;
import com.atakmap.spatial.GeometryTransformer;
import com.atakmap.util.ReferenceCount;

import java.io.File;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Created by Developer on 7/31/2018.
 */

public class TileContainerMosaicDatabase implements MosaicDatabase2 {
    private final static MosaicDatabase2.Cursor EMPTY = new MultiplexingMosaicDatabaseCursor2(Collections.<Cursor>emptySet(), null);

    private static Map<String, TileContainer> activeContainers = new HashMap<String, TileContainer>();
    private static Map<String, MosaicDatabaseSpi2> spis = new HashMap<String, MosaicDatabaseSpi2>();

    private TileContainerRef impl;
    private String datasetType;
    private Coverage coverage;

    TileContainerMosaicDatabase(String datasetType) {
        this.datasetType = datasetType;
    }

    @Override
    public String getType() {
        return this.datasetType;
    }

    @Override
    public synchronized void open(File file) {
        if(this.impl != null)
            throw new IllegalStateException();
        TileContainer tiles = TileContainerFactory.open(file.getAbsolutePath(), true, null);
        if(tiles == null) // failed to open
            return;
        this.impl = new TileContainerRef(tiles);

        // obtain the bounds for the tiles. the returned bounts will be in the native spatial
        // reference of the container
        Envelope bounds = this.impl.value.getBounds();
        // transform the bounds to WGS84 if needed
        if(this.impl.value.getSRID() != 4326) {
            // obtain a geometry object (polygon) from the bounds Envelope
            Geometry boundsGeom = GeometryFactory.fromEnvelope(bounds);
            // transform the geometry from the native spatial reference to EPSG:4326 (WGS84)
            Geometry boundsWgs84 = GeometryTransformer.transform(boundsGeom, this.impl.value.getSRID(), 4326);
            // re-assign the bounds to the WGS84 extent
            bounds = boundsWgs84.getEnvelope();
        }
        // find min and max resolution
        final TileMatrix.ZoomLevel[] zoomLevels = this.impl.value.getZoomLevel();
        double minResolution = zoomLevels[0].resolution;
        double maxResolution = zoomLevels[0].resolution;
        for(int i = 1; i < zoomLevels.length; i++) {
            // NOTE: resolution is expressed in meters-per-pixel. The number of meters-per-pizel for
            // "higher" resolution tiles is numerically less than the number of meters-per-pixel for
            // "lower" resolution tiles, e.g. 5m tiles are higher resolution than 10m tiles
            if(zoomLevels[i].resolution > minResolution)
                minResolution = zoomLevels[i].resolution;
            if(zoomLevels[i].resolution < maxResolution)
                maxResolution = zoomLevels[i].resolution;
        }
        // construct the coverage object, which is the composition of the @GS84 bounds, as a
        // Geometry object, and the minimum and maximum display thresholds, expressed in
        // meters-per-pixel
        this.coverage = new Coverage(GeometryFactory.fromEnvelope(bounds), minResolution, maxResolution);
    }

    @Override
    public synchronized void close() {
        if(this.impl == null)
            return;
        this.impl.dereference();
        this.impl = null;
        this.coverage = null;
    }

    @Override
    public synchronized Coverage getCoverage() {
        return this.coverage;
    }

    @Override
    public synchronized void getCoverages(Map<String, Coverage> map) {
        if(this.impl != null)
            map.put(this.impl.value.getName(), this.coverage);
    }

    @Override
    public synchronized Coverage getCoverage(String s) {
        if(this.impl == null)
            return null;
        else if(s == null || s.equals(this.impl.value.getName()))
            return this.coverage;
        else
            return null;
    }

    @Override
    public synchronized Cursor query(QueryParameters queryParameters) {
        if(this.impl == null)
            return EMPTY;

        TileMatrix.ZoomLevel[] zoomLevels = this.impl.value.getZoomLevel();
        int queryMinZoomIdx = 0;
        int queryMaxZoomIdx = zoomLevels.length-1;
        Envelope queryBounds = this.impl.value.getBounds();
        if(queryParameters != null) {
            // precision imagery is imagery that is capable of producing mensurated coordinates via
            // a special Image-to-Ground (I2G) function. Since this format does not support such
            // a capability, if precision imagery is being requested, return the empty set
            if(queryParameters.precisionImagery != null && queryParameters.precisionImagery.booleanValue())
                return EMPTY;
            // if display thesholds are specified, make sure that
            if(!Double.isNaN(queryParameters.minGsd)) {
                // the minimum GSD (Ground Sample Distance, or resolution) of the query parameters
                // will filter out all images with a resolution lower than the specified resolution.
                // In other words the minimum GSD constraint is saying, "give me all imagery with
                // this resolution or higher". For example, if 'minGsd' is 20, that means that all
                // images with a resolution of 20 meters-per-pixel or higher (e.g. 10m, 5m, 1m)
                // should be returned, while imagery with a resolution lower than 20m
                // (e.g. 25m, 50m, 100m) should be excluded

                // if the minimum requested resolution is higher than the highest resolution
                // available in the container, return the empty set
                if(queryParameters.minGsd < this.coverage.maxGSD)
                    return EMPTY;

                // find the minimum zoom level that satisfies the filter
                while(queryMinZoomIdx < (zoomLevels.length-2) &&
                      zoomLevels[queryMinZoomIdx].resolution > queryParameters.minGsd) {

                    queryMinZoomIdx++;
                }
            }
            if(!Double.isNaN(queryParameters.maxGsd)) {
                // the maximum GSD (Ground Sample Distance, or resolution) of the query parameters
                // will filter out all images with a resolution higher than the specified
                // resolution. In other words the maximum GSD constraint is saying, "give me all
                // imagery with this resolution or lower". For example, if 'maxGsd' is 20, that
                // means that all images with a resolution of 20 meters-per-pixel or lower
                // (e.g. 25m, 50m, 100m) should be returned, while imagery with a resolution higher
                // than 20m (e.g. 10m, 5m, 1m) should be excluded

                // if the maximum requested resolution is lower than the lowest resolution
                // available in the container, return the empty set
                if(queryParameters.maxGsd > this.coverage.minGSD)
                    return EMPTY;

                // find the minimum zoom level that satisfies the filter
                while(queryMaxZoomIdx > 0 &&
                      zoomLevels[queryMaxZoomIdx].resolution < queryParameters.maxGsd) {

                    queryMaxZoomIdx--;
                }
            }

            // ensure the values are still sane -- a malformed argument may result in an invalid
            // combination of min and max GSD filters
            if(queryMaxZoomIdx < queryMinZoomIdx)
                return EMPTY;

            // restrict the query bounds to the intersection with the specified spatial filter
            if(queryParameters.spatialFilter != null) {
                Envelope filterBounds = queryParameters.spatialFilter.getEnvelope();
                Envelope coverageBounds = this.coverage.geometry.getEnvelope();

                // check that the request region intersects the region of coverage
                if(!Rectangle.intersects(filterBounds.minX,
                                         filterBounds.minY,
                                         filterBounds.maxX,
                                         filterBounds.maxY,
                                         coverageBounds.minX,
                                         coverageBounds.minY,
                                         coverageBounds.maxX,
                                         coverageBounds.maxY)) {

                    return EMPTY;
                }

                // compute the intersection of the filter and coverage bounds
                Envelope filteredCoverage =
                        new Envelope(Math.max(filterBounds.minX, coverageBounds.minX),
                                     Math.max(filterBounds.minY, coverageBounds.minY),
                                     0d,
                                     Math.min(filterBounds.maxX, coverageBounds.maxX),
                                     Math.min(filterBounds.maxY, coverageBounds.maxY),
                                     0d);

                // transform the filtered coverage into the native spatial reference
                Geometry filteredGeom = GeometryTransformer.transform(GeometryFactory.fromEnvelope(filteredCoverage), 4326, this.impl.value.getSRID());

                // update the query bounds to the intersection
                queryBounds = filteredGeom.getEnvelope();
            }

            // check for matching SRID
            if(queryParameters.srid != -1 && queryParameters.srid != this.impl.value.getSRID())
                return EMPTY;

            if(queryParameters.types != null && !queryParameters.types.contains(this.impl.value.getName()))
                return EMPTY;
        }

        return new CursorImpl(this.impl, queryBounds, queryMinZoomIdx, queryMaxZoomIdx);
    }

    /**********************************************************************************************/

    static TileContainer find(String id) {
        synchronized(activeContainers) {
            return activeContainers.get(id);
        }
    }

    public static void registerType(String datasetType) {
        MosaicDatabaseSpi2 spi;
        synchronized(spis) {
            if(spis.containsKey(datasetType))
                return;
            spi = new Spi(datasetType);
            // if this is the first registration, also register the custom TileReader implementation
            // to support TileReader construction for results returned from queries against
            // TileContainerMosaicDatabase instances
            if(spis.isEmpty())
                TileReaderFactory.registerSpi(TileContainerTileReader.SPI);
            spis.put(spi.getName(), spi);
        }
        MosaicDatabaseFactory2.register(spi);
    }

    public static void unregisterType(String datasetType) {
        MosaicDatabaseSpi2 spi;
        synchronized(spis) {
            spi = spis.remove(datasetType);
            if(spi == null)
                return;
            // if this is the last unregistration, also un register the custom TileReader
            // implementation as we should no longer have any requests for TileReader construction
            // for results coming out of TIleContainerMosaicDatabase instances
            if(spis.isEmpty())
                TileReaderFactory.unregisterSpi(TileContainerTileReader.SPI);
        }
        MosaicDatabaseFactory2.register(spi);
    }

    /**********************************************************************************************/

    private static class TileContainerRef extends ReferenceCount<TileContainer> {

        public final String id;

        public TileContainerRef(TileContainer value) {
            super(value, true);

            this.id = UUID.randomUUID().toString();

            synchronized(activeContainers) {
                activeContainers.put(this.id, value);
            }
        }

        @Override
        protected void onDereferenced() {
            synchronized(activeContainers) {
                activeContainers.remove(this.id);
            }

            try {
                this.value.dispose();
            } finally {
                super.onDereferenced();
            }
        }
    };

    /**********************************************************************************************/

    private static class CursorImpl implements MosaicDatabase2.Cursor {

        private TileContainerRef tiles;
        private int minZoomLevelIdx;
        private int maxZoomLevelIdx;
        private Envelope queryBounds;
        private TileMatrix.ZoomLevel[] zoomLevels;
        private Projection proj;

        private int zoomLevelIdx;
        private int tileRow;
        private int tileColumn;
        private Point zoomMinTile;
        private Point zoomMaxTile;
        private GeoPoint tileUL;
        private GeoPoint tileUR;
        private GeoPoint tileLR;
        private GeoPoint tileLL;

        public CursorImpl(TileContainerRef tiles, Envelope queryBounds, int minZoomLevelIdx, int maxZoomLevelIdx) {
            this.tiles = tiles;
            this.queryBounds = queryBounds;
            this.minZoomLevelIdx = minZoomLevelIdx;
            this.maxZoomLevelIdx = maxZoomLevelIdx;

            this.zoomLevels = this.tiles.value.getZoomLevel();
            this.proj = ProjectionFactory.getProjection(this.tiles.value.getSRID());

            // prepare the iteration state variables to point at the tile immediately before the
            // first tile we want to return. We'll set the zoom level index to the maximum plus
            // one, then set the tile row/column equal to the max for the zoom level
            this.zoomLevelIdx = this.maxZoomLevelIdx+1;
            this.tileRow = 0;
            this.tileColumn = 0;
            this.zoomMinTile = new Point(0, 0);
            this.zoomMaxTile = new Point(0, 0);

            this.tiles.reference();
        }

        @Override
        public boolean moveToNext() {
            if(this.isClosed())
                return false;

            // iteration will be in row-major order by zoom level
            do {
                if (tileColumn < zoomMaxTile.x) {
                    // advance the column
                    tileColumn++;
                } else if (tileRow < zoomMaxTile.y) {
                    // reset the column
                    tileColumn = zoomMinTile.x;
                    // advance the row
                    tileRow++;
                } else if (zoomLevelIdx > minZoomLevelIdx) {
                    // advance the zoom
                    zoomLevelIdx--;
                    // recompute the tile indices
                    zoomMinTile = TileMatrix.Util.getTileIndex(this.tiles.value,
                                                               this.zoomLevels[this.zoomLevelIdx].level,
                                                               queryBounds.minX, queryBounds.maxY);
                    zoomMaxTile = TileMatrix.Util.getTileIndex(this.tiles.value,
                                                               this.zoomLevels[this.zoomLevelIdx].level,
                                                               queryBounds.maxX, queryBounds.minY);
                    // set to the first tile of the zoom level
                    tileColumn = zoomMinTile.x;
                    tileRow = zoomMinTile.y;
                } else {
                    return false;
                }

                // ensure we have a tile at this location. this is important as the downstream
                // consumer will be building up an occlusion mask for all images that have
                // intersected the query bounds. missing tiles in sparsely populated containers will
                // end up occluding lower resolution data containing regions
                if(this.tiles.value.getTileData(this.zoomLevels[this.zoomLevelIdx].level, tileColumn, tileRow, null) == null)
                    continue;

                // obtain the corner coordinates for the tile in the native spatial reference
                PointD ulProj = TileMatrix.Util.getTilePoint(this.tiles.value, this.zoomLevels[this.zoomLevelIdx].level, this.tileColumn, this.tileRow, 0, 0);
                PointD urProj = TileMatrix.Util.getTilePoint(this.tiles.value, this.zoomLevels[this.zoomLevelIdx].level, this.tileColumn, this.tileRow, this.zoomLevels[this.zoomLevelIdx].tileWidth, 0);
                PointD lrProj = TileMatrix.Util.getTilePoint(this.tiles.value, this.zoomLevels[this.zoomLevelIdx].level, this.tileColumn, this.tileRow, this.zoomLevels[this.zoomLevelIdx].tileWidth, this.zoomLevels[this.zoomLevelIdx].tileHeight);
                PointD llProj = TileMatrix.Util.getTilePoint(this.tiles.value, this.zoomLevels[this.zoomLevelIdx].level, this.tileColumn, this.tileRow, 0, this.zoomLevels[this.zoomLevelIdx].tileHeight);

                // transform the corner coordinates to WGS84 (if necessary)
                this.tileUL = this.proj.inverse(ulProj, null);
                this.tileUR = this.proj.inverse(urProj, null);
                this.tileLR = this.proj.inverse(lrProj, null);
                this.tileLL = this.proj.inverse(llProj, null);

                return true;
            } while(true);
        }

        @Override
        public GeoPoint getUpperLeft() {
            return this.tileUL;
        }

        @Override
        public GeoPoint getUpperRight() {
            return this.tileUR;
        }

        @Override
        public GeoPoint getLowerRight() {
            return this.tileLR;
        }

        @Override
        public GeoPoint getLowerLeft() {
            return this.tileLL;
        }

        @Override
        public double getMinLat() {
            return MathUtils.min(this.tileUL.getLatitude(),
                                 this.tileUR.getLatitude(),
                                 this.tileLR.getLatitude(),
                                 this.tileLL.getLatitude());
        }

        @Override
        public double getMinLon() {
            return MathUtils.min(this.tileUL.getLongitude(),
                                 this.tileUR.getLongitude(),
                                 this.tileLR.getLongitude(),
                                 this.tileLL.getLongitude());
        }

        @Override
        public double getMaxLat() {
            return MathUtils.max(this.tileUL.getLatitude(),
                                 this.tileUR.getLatitude(),
                                 this.tileLR.getLatitude(),
                                 this.tileLL.getLatitude());
        }

        @Override
        public double getMaxLon() {
            return MathUtils.max(this.tileUL.getLongitude(),
                                 this.tileUR.getLongitude(),
                                 this.tileLR.getLongitude(),
                                 this.tileLL.getLongitude());
        }

        @Override
        public String getPath() {
            // we will return a custom URI here that will provide us with the information needed to
            // construct a TileReader instance
            return "tiles://" + this.tiles.id + "/" + this.zoomLevels[this.zoomLevelIdx].level + "/" + this.tileRow + "/" + this.tileColumn;
        }

        @Override
        public String getType() {
            return this.tiles.value.getName();
        }

        @Override
        public double getMinGSD() {
            return this.zoomLevels[this.zoomLevelIdx].resolution;
        }

        @Override
        public double getMaxGSD() {
            return this.zoomLevels[this.zoomLevelIdx].resolution;
        }

        @Override
        public int getWidth() {
            return this.zoomLevels[this.zoomLevelIdx].tileWidth;
        }

        @Override
        public int getHeight() {
            return this.zoomLevels[this.zoomLevelIdx].tileHeight;
        }

        @Override
        public int getId() {
            // this should be a unique identifier for the image within the Mosaic Database, however,
            // it is currently ignored. the use of an 'int' is prohibitive for datasets that could
            // potentially contain ore than 2^32 image chips
            return 0;
        }

        @Override
        public int getSrid() {
            return this.tiles.value.getSRID();
        }

        @Override
        public boolean isPrecisionImagery() {
            // the content is not precision imagery
            return false;
        }

        @Override
        public Frame asFrame() {
            return new MosaicDatabase2.Frame(this);
        }

        @Override
        public void close() {
            if(this.tiles != null) {
                this.tiles.dereference();
                this.tiles = null;
            }
        }

        @Override
        public boolean isClosed() {
            return (this.tiles == null);
        }
    }

    /**********************************************************************************************/

    private static class Spi implements MosaicDatabaseSpi2 {

        public final String type;

        Spi(String type) {
            this.type = type;
        }

        @Override
        public String getName() {
            return this.type;
        }

        @Override
        public MosaicDatabase2 createInstance() {
            return new TileContainerMosaicDatabase(this.type);
        }
    }
}
