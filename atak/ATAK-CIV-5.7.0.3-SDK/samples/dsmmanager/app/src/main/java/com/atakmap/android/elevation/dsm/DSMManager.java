
package com.atakmap.android.elevation.dsm;

import androidx.annotation.NonNull;

import com.atakmap.coremap.conversions.Span;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.map.elevation.ElevationData;
import com.atakmap.map.gdal.GdalElevationChunk;
import com.atakmap.map.gdal.GdalLibrary;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.DatasetDescriptorSpiArgs;
import com.atakmap.map.layer.raster.ImageDatasetDescriptor;
import com.atakmap.map.layer.raster.MosaicDatasetDescriptor;
import com.atakmap.map.layer.raster.gdal.GdalLayerInfo;
import com.atakmap.map.layer.raster.mosaic.MosaicDatabase2;
import com.atakmap.map.layer.raster.mosaic.MosaicDatabaseFactory2;

import org.gdal.gdal.Dataset;

import java.io.File;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class DSMManager {
    private DSMManager() {
    }

    final static public String TAG = "DSMManager";

    private static File[] dsmDirs;
    private static DSMDatabase db;
    private static int _model = ElevationData.MODEL_SURFACE;
    private static Span _span = Span.METER;
    private static String _reference = "HAE";

    private static ExecutorService _refreshThread = Executors.newSingleThreadExecutor();

    public static void initialize() {
        try {
            File primaryDsmDir = FileSystemUtils.getItem("tools/dsm");
            if (!primaryDsmDir.exists()) {
                if (!primaryDsmDir.mkdir()) {
                    Log.d(TAG, "error creating dsm directory");
                }
            }
        } catch (Exception e) {
            Log.d(TAG, "error creating dsm directory", e);
        }
        dsmDirs = FileSystemUtils.getItems("tools/dsm");
        db = new DSMDatabase(FileSystemUtils.getItem("Databases/dsm.db"));
    }

    public static void teardown() {
        dsmDirs = null;
        if (db != null) {
            db.close();
            db = null;
        }
    }

    public static DSMDatabase getDb() {
        return db;
    }

    /**
     * Sets the defaults used by the DSM Manager when importing a new dataset
     * @param model the model from ElevationData constancts
     * @param span the span (meters or feet)
     * @param reference the reference (HAE or MSL)
     *
     *
     */
    public static void setDefaults(final int model, final Span span, @NonNull final String reference) {
        _model = model;
        _span = span;
        _reference = reference;
    }

    public static void refresh() {
        _refreshThread.submit(new Runnable() {
            @Override
            public void run() {
                db.validateCatalog();
                refreshImpl(dsmDirs);
            }
        });
    }

    
    static void refreshSync(File f) {
        db.validateCatalog();
        refreshImpl(new File[] { f });
    }

    static void refreshImpl(File[] files) {
        if (files != null) {
            for (File file : files) {
                if (file.isDirectory()) {
                    File[] children = file.listFiles();
                    if (children != null)
                        refreshImpl(children);
                } else if (!db.contains(file.getAbsolutePath())) {
                    // parse out elevation info
                    final ElevationInfo parsed = parse(file);
                    if (parsed != null)
                        db.insert(parsed);
                }
            }
        }
    }

    private static ElevationInfo parse(File file) {
        File workingDir = null;
        try {
            // use the GDAL dataset handler to the parsing
            workingDir = FileSystemUtils.getItem("Databases/dsm.data/" + UUID.randomUUID().toString());
            workingDir.mkdirs();
            Set<DatasetDescriptor> descs = GdalLayerInfo.INSTANCE
                    .create(new DatasetDescriptorSpiArgs(file, workingDir));
            if (descs == null || descs.isEmpty())
                return null;

            // XXX - 
            for (DatasetDescriptor desc : descs) {
                if (desc instanceof ImageDatasetDescriptor) {
                    ImageDatasetDescriptor image = (ImageDatasetDescriptor) desc;
                    String reference = _reference;
                    Dataset ds = null;
                    try {
                        ds = GdalLibrary.openDatasetFromPath(GdalLayerInfo.getGdalFriendlyUri(image));
                        if(ds != null)
                            reference = GdalElevationChunk.isMsl(ds) ? "MSL" : "HAE";
                    } finally {
                        if(ds != null)
                            ds.delete();
                    }
                    return new ElevationInfo(
                            file.getAbsolutePath(),
                            "geotiff",
                            image.getUpperLeft(),
                            image.getUpperRight(),
                            image.getLowerRight(),
                            image.getLowerLeft(),
                            image.getMinResolution(null),
                            image.getMaxResolution(null),
                            image.getWidth(),
                            image.getHeight(),
                            image.getSpatialReferenceID(),
                            _model,
                            reference,
                            _span,
                            GdalLayerInfo.getGdalFriendlyUri(image));
                } else if(desc instanceof MosaicDatasetDescriptor) {
                    MosaicDatasetDescriptor mosaic = (MosaicDatasetDescriptor)desc;
                    MosaicDatabase2 db = MosaicDatabaseFactory2.create(mosaic.getMosaicDatabaseProvider());
                    try {
                        db.open(mosaic.getMosaicDatabaseFile());
                        try(MosaicDatabase2.Cursor result = db.query(null)) {
                            if(result.moveToNext()) {
                                String reference = _reference;
                                Dataset ds = null;
                                try {
                                    ds = GdalLibrary.openDatasetFromPath(result.getPath());
                                    if (ds != null)
                                        reference = GdalElevationChunk.isMsl(ds) ? "MSL" : "HAE";
                                } finally {
                                    if (ds != null)
                                        ds.delete();
                                }
                                return new ElevationInfo(
                                        file.getAbsolutePath(),
                                        "geotiff",
                                        result.getUpperLeft(),
                                        result.getUpperRight(),
                                        result.getLowerRight(),
                                        result.getLowerLeft(),
                                        result.getMinGSD(),
                                        result.getMaxGSD(),
                                        result.getWidth(),
                                        result.getHeight(),
                                        result.getSrid(),
                                        _model,
                                        reference,
                                        _span,
                                        result.getPath());
                            }
                        }
                    } finally {
                        db.close();
                    }
                }
            }

            return null;
        } catch (Throwable t) {
            // XXX - log error
            return null;
        } finally {
            if(workingDir != null)
                FileSystemUtils.deleteDirectory(workingDir, false);
        }
    }
}
