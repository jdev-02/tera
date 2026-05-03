
package com.atakmap.android.hellobuildings.datastore;

import java.io.File;
import java.io.FileOutputStream;
import java.net.URL;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;

import android.util.Log;
import android.util.LruCache;

import com.atakmap.android.hellobuildings.parser.Building;
import com.atakmap.android.hellobuildings.parser.BuildingList;
import com.atakmap.android.hellobuildings.parser.NodeList;
import com.atakmap.android.hellobuildings.parser.OSMParser;
import com.atakmap.android.hellobuildings.parser.ParserHandler;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.feature.AttributeSet;
import com.atakmap.map.layer.feature.FeatureCursor;
import com.atakmap.map.layer.feature.FeatureDataStore.FeatureQueryParameters.RegionSpatialFilter;
import com.atakmap.map.layer.feature.FeatureSet;
import com.atakmap.map.layer.feature.RuntimeFeatureDataStore;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.map.layer.feature.style.BasicFillStyle;
import com.atakmap.map.layer.raster.osm.OSMUtils;

public class OSMBuildingDataStore extends RuntimeFeatureDataStore {

    private final static String TAG = "OSMBuildingDataStore";

    private final static int CACHE_LEVEL = 16;
    private final static int MIN_DISPLAY_LEVEL = 17;

    private ExecutorService fileCacheWorker;
    private ExecutorService downloadWorker;

    private Set<Long> queuedFiles;
    private Set<Long> queuedDownloads;
    private LruCache<Long, Long> loaded;

    private File cacheDir;
    private String serverUrl;

    public OSMBuildingDataStore(File cacheDir, String serverUrl) {
        this.cacheDir = cacheDir;
        this.serverUrl = serverUrl;

        this.cacheDir.mkdirs();

        this.fileCacheWorker = Executors.newFixedThreadPool(3);
        this.downloadWorker = Executors.newFixedThreadPool(3);
        this.queuedDownloads = new HashSet<Long>();
        this.queuedFiles = new HashSet<Long>();
        this.loaded = new LruCache<Long, Long>(64) {
            @Override
            protected void entryRemoved(boolean evicted, Long key,
                    Long oldValue, Long newValue) {
                int column = (int) (key.longValue() >> 32L);
                int row = (int) (key.longValue() & 0xFFFFFFFFL);
                Log.d(TAG, "Evicting LRU building tile " + column + "," + row);
                deleteFeatureSetImpl(oldValue.longValue());
            }
        };
    }

    @Override
    public synchronized FeatureCursor queryFeatures(
            FeatureQueryParameters params) {
        if (params != null)
            checkCache(params);
        return super.queryFeatures(params);
    }

    @Override
    public synchronized int queryFeaturesCount(FeatureQueryParameters params) {
        if (params != null)
            checkCache(params);
        return super.queryFeaturesCount(params);
    }

    private void checkCache(FeatureQueryParameters params) {
        if (params.spatialFilter == null)
            return;

        RegionSpatialFilter sf = (RegionSpatialFilter) params.spatialFilter;

        // XXX - compute tiles in view
        int stx = OSMUtils.mapnikTileX(CACHE_LEVEL,
                sf.upperLeft.getLongitude());
        int sty = OSMUtils.mapnikTileY(CACHE_LEVEL, sf.upperLeft.getLatitude());
        int ftx = OSMUtils.mapnikTileX(CACHE_LEVEL,
                sf.lowerRight.getLongitude());
        int fty = OSMUtils.mapnikTileY(CACHE_LEVEL,
                sf.lowerRight.getLatitude());

        final int ntx = ftx - stx + 1;
        final int nty = fty - sty + 1;

        final boolean prefetchOnly = (Double.isNaN(params.maxResolution)
                || params.maxResolution > OSMUtils
                        .mapnikTileResolution(MIN_DISPLAY_LEVEL));
        if ((ntx * nty) > 49 && prefetchOnly)
            return;

        for (int ty = sty; ty <= fty; ty++) {
            for (int tx = stx; tx <= ftx; tx++) {
                final int col = tx;
                final int row = ty;
                final Long k = Long
                        .valueOf(((long) col << 32L) | (row & 0xFFFFFFFFL));

                // XXX - check LRU cache
                synchronized (loaded) {
                    if (loaded.get(k) != null)
                        continue;
                }
                // if not loaded, check file cache
                final File cacheFile = getCacheFile(this.cacheDir, CACHE_LEVEL,
                        tx, ty);
                if (cacheFile.exists()) {
                    if (prefetchOnly)
                        continue;

                    synchronized (fileCacheWorker) {
                        if (queuedFiles.contains(k))
                            continue;
                        queuedFiles.add(k);
                        Log.d(TAG, "Queueing building tile from file cache "
                                + col + "," + row);
                        fileCacheWorker.execute(new Runnable() {
                            public void run() {
                                try {
                                    loadFromDisk(CACHE_LEVEL, col, row);
                                } catch (Exception e) {
                                    Log.e(TAG,"error",e);
                                } finally {
                                    queuedFiles.remove(k);
                                }
                            }
                        });
                    }
                } else {
                    // download in background
                    synchronized (downloadWorker) {
                        if (queuedDownloads.contains(k))
                            continue;
                        queuedDownloads.add(k);
                        Log.d(TAG, "Queueing building tile download " + col
                                + "," + row);
                        downloadWorker.execute(new Runnable() {
                            public void run() {
                                try {
                                    download(CACHE_LEVEL, col, row,
                                            prefetchOnly);
                                } catch (Exception e) {
                                    Log.e(TAG,"error",e);
                                } finally {
                                    queuedDownloads.remove(k);
                                }
                            }
                        });
                    }
                }
            }
        }
    }

    private void loadFromDisk(int zoom, int column, int row) throws Exception {
        final File cacheFile = getCacheFile(this.cacheDir, zoom, column, row);

        SAXParserFactory factory = SAXParserFactory.newInstance();
        SAXParser saxParser;

        long s = System.currentTimeMillis();
        saxParser = factory.newSAXParser();
        NodeList nl = new NodeList();
        final BuildingList bl = new BuildingList();
        final ParserHandler userhandler = new ParserHandler(nl, bl);
        saxParser.parse(cacheFile, userhandler);
        long e = System.currentTimeMillis();

        Log.d(TAG, "Loaded building tile from file cache " + column + "," + row
                + " in " + (e - s) + "ms");

        synchronized (this) {
            this.beginBulkModificationImpl();
            try {
                // all features must be members of a Feature Set. The Feature Set is
                // some logical grouping of features. Hierarchical representations may
                // be emulated by specifying Feature Sets as paths
                FeatureSet tile = this.insertFeatureSetImpl(
                        "HelloBuildings", // what generated the features
                        "Buildings", // the type of the featuers
                        "Buildings", // the feature set name
                        OSMUtils.mapnikTileResolution(MIN_DISPLAY_LEVEL), // min resolution threshold 
                        0d, // max resolution threshold
                        true);
                final long fsid = tile.getId();

                for (Building B : bl.values()) {
                    // for each of the footprints defined, we will create a Feature. A
                    // Feature is the composition of: geometry, style and attribtues
                    // (metadata).

                    this.insertFeatureImpl(
                            fsid,
                            "Building " + B.getId(),
                            //heightOffsetPolygonToVolume(poly),
                            B.asPolygon(true),
                            new BasicFillStyle(0xC07F7F7F),
                            new AttributeSet(),
                            false);
                }

                final Long k = Long
                        .valueOf(((long) column << 32L) | (row & 0xFFFFFFFFL));
                synchronized (loaded) {
                    loaded.put(k, fsid);
                }
            } finally {
                this.endBulkModificationImpl(true);
                this.dispatchDataStoreContentChangedNoSync();
            }
        }
    }

    private void download(final int zoom, final int column, final int row,
            boolean prefetchOnly) throws Exception {
        final File cacheFile = getCacheFile(this.cacheDir, zoom, column, row);
        cacheFile.getParentFile().mkdirs();

        final double sLat = OSMUtils.mapnikTileLat(zoom, row + 1);
        final double wLng = OSMUtils.mapnikTileLng(zoom, column);
        final double nLat = OSMUtils.mapnikTileLat(zoom, row);
        final double eLng = OSMUtils.mapnikTileLng(zoom, column + 1);

        long s = System.currentTimeMillis();
        URL url = new URL(
                OSMParser.getOsmURI(this.serverUrl, sLat, wLng, nLat, eLng));
        FileSystemUtils.copyStream(url.openStream(),
                true,
                new FileOutputStream(cacheFile),
                true);
        long e = System.currentTimeMillis();

        Log.d(TAG, "Downloaded building tile " + column + "," + row + " in "
                + (e - s) + "ms");

        if (prefetchOnly)
            return;

        synchronized (fileCacheWorker) {
            final Long k = Long
                    .valueOf(((long) column << 32L) | (row & 0xFFFFFFFFL));
            queuedFiles.add(k);
            fileCacheWorker.execute(new Runnable() {
                public void run() {
                    try {
                        loadFromDisk(zoom, column, row);
                    } catch (Throwable t) {
                        t.printStackTrace();
                    } finally {
                        queuedFiles.remove(k);
                    }
                }
            });
        }
    }

    private static File getCacheFile(File cacheDir, int zoom, int column,
            int row) {
        return new File(cacheDir, zoom + "/" + column + "." + row + ".osm");
    }
}
