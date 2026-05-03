
package com.atakmap.android.elevation.dsm;

import android.content.Context;
import android.graphics.drawable.Drawable;
import android.util.Pair;

import com.atakmap.android.elevation.dsm.plugin.R;
import com.atakmap.android.importfiles.sort.ImportResolver;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.locale.LocaleUtil;
import com.atakmap.coremap.log.Log;
import com.atakmap.filesystem.HashingUtils;
import com.atakmap.map.gdal.GdalElevationChunk;
import com.atakmap.map.gdal.GdalLibrary;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.DatasetDescriptorSpiArgs;
import com.atakmap.map.layer.raster.ImageDatasetDescriptor;
import com.atakmap.map.layer.raster.gdal.GdalLayerInfo;

import org.gdal.gdal.Dataset;
import org.gdal.gdalconst.gdalconst;
import org.gdal.osr.SpatialReference;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.Vector;

import gov.tak.api.util.Disposable;


public class ImportDSMSort extends ImportResolver implements Disposable {

    static class ImportInfo {
        public File file;
        public Set<SortFlags> flags;
    }

    private static final String TAG = "ImportDSMSort";
    private final Context _context;

    public ImportDSMSort(Context context) {
        super(null, null, "DSM Importer", context.getDrawable(R.drawable.dsm));
        _context = context;
    }

    @Override
    public boolean match(File file) {
        return isDSM(file);
    }


    @Override
    public void filterFoundResolvers(List<ImportResolver> importResolvers, File file) {
        importResolvers.clear();
        importResolvers.add(this);
        //super.filterFoundResolvers(importResolvers, file);
    }

    private static boolean isDSM(final File file) {

        // for now do not try to take a data package with a ton of dsm files and create a mosaic
        if (FileSystemUtils.checkExtension(file, "zip"))
            return false;

        File workingDir = null;
        try {
            // use the GDAL dataset handler to the parsing
            workingDir = FileSystemUtils.getItem("Databases/dsm.data/" + UUID.randomUUID().toString());
            workingDir.mkdirs();
            Set<DatasetDescriptor> descs = GdalLayerInfo.INSTANCE
                    .create(new DatasetDescriptorSpiArgs(file, workingDir));
            if (descs == null || descs.isEmpty())
                return false;

            for (DatasetDescriptor desc : descs) {
                if (desc instanceof ImageDatasetDescriptor) {
                    ImageDatasetDescriptor image = (ImageDatasetDescriptor) desc;
                    Dataset ds = null;
                    try {
                        ds = GdalLibrary.openDatasetFromPath(GdalLayerInfo.getGdalFriendlyUri(image));
                        return isDSM(ds);
                    } catch (Exception e) {}
                }
            }
        } catch (Exception e) {
        } finally {
            if (workingDir != null)
                FileSystemUtils.delete(workingDir);
        }
        return false;
    }



    /**
     * Send intent so CoT will be dispatched internally within ATAK Also sort file to proper
     * location
     * 
     * @param file the file to import
     * @return true if the file was imported successfully
     */
    @Override
    public boolean beginImport(File file) {
        return beginImport(file, Collections.emptySet());
    }

    @Override
    public boolean beginImport(File src, Set<SortFlags> flags) {

        File dst = getDestinationPath(src);
        if (flags.contains(SortFlags.IMPORT_COPY)) {
            // honor the copy file flag
            try {
                FileSystemUtils.copyFile(src, dst);
                DSMManager.refreshSync(dst);
            } catch (Exception ignore) {
            }
        } else if (flags.contains(SortFlags.IMPORT_MOVE)) {
            try {
                FileSystemUtils.renameTo(src, dst);
                DSMManager.refreshSync(dst);
            } catch (Exception ignore) {
                try {
                    FileSystemUtils.copyFile(src, dst);
                    DSMManager.refreshSync(dst);
                } catch (Exception ignore2) {
                }
            }
        } else {
            dst = src;
            DSMManager.refreshSync(dst);
        }

        return DSMManager.getDb().contains(dst.getAbsolutePath());

    }

    @Override
    public File getDestinationPath(File file) {
        return new File(FileSystemUtils.getItem("tools/dsm"), file.getName());
    }

@Override
    public String getDisplayableName() {
        return _context.getString(com.atakmap.android.elevation.dsm.plugin.R.string.app_name);
    }

    @Override
    public Drawable getIcon() {
        return _context.getDrawable(R.drawable.dsm);
    }

    @Override
    public Pair<String, String> getContentMIME() {
        return new Pair<>("DSM", "application/dsm");
    }


    @Override
    public void dispose() {
    }


    public static boolean isDSM(Dataset dataset) {

        // check to see if any vertical srid is defined and present the user the option to import it as DSM
        // will not be perfect

        final String driver = dataset.GetDriver().GetDescription();
        switch(driver) {
            case "SRTMHGT" :
            case "DTED" :
                return true;
            default :
                break;
        }

        String wkt = dataset.GetProjectionRef();
        if(wkt != null && driver.equals("GTiff")) {
            Dataset geotiff = null;
            try {
                String desc = dataset.GetDescription();

                Method openImpl = GdalLibrary.class.getDeclaredMethod("openImpl", String.class, Long.TYPE, Vector.class, Vector.class);
                openImpl.setAccessible(true);
                geotiff = (Dataset) openImpl.invoke(null,
                        desc,
                        gdalconst.GA_ReadOnly,
                        new Vector(Collections.singleton(driver)),
                        null);
                if (geotiff != null) {
                    Method setThreadLocalConfigOption = GdalLibrary.class.getDeclaredMethod("setThreadLocalConfigOption", String.class, String.class);
                    setThreadLocalConfigOption.setAccessible(true);
                    setThreadLocalConfigOption.invoke(null, "GTIFF_REPORT_COMPD_CS", "YES");
                    wkt = geotiff.GetProjectionRef();
                    setThreadLocalConfigOption.invoke(null, "GTIFF_REPORT_COMPD_CS", null);
                }
            } catch (InvocationTargetException | NoSuchMethodException | IllegalAccessException e) {
                Log.e(TAG, "error", e);
            } finally {
                if(geotiff != null)
                    geotiff.delete();
            }
        }
        if(wkt == null)
            return false;

        String vert_cs = null;
        final int vert_csStart = wkt.indexOf("VERT_CS");
        if(vert_csStart == 0)
            vert_cs = wkt;
        else if(vert_csStart > 0)
            vert_cs = extractWkt(wkt.substring(vert_csStart));
        String vertcrs = null;
        final int vertcrsStart = wkt.indexOf("VERTCRS");
        if(vertcrsStart == 0)
            vertcrs = wkt;
        else if(vertcrsStart > 0)
            vertcrs = extractWkt(wkt.substring(vertcrsStart));
        if(vertcrs != null && vertcrs.toLowerCase(LocaleUtil.getCurrent()).contains("gravity-related height"))
            return true;
        if(vert_cs != null && GdalLibrary.getSpatialReferenceID(new SpatialReference(vert_cs)) > 0)
            return true;
        return false;
    }

    private static String extractWkt(String s) {
        int in = 0;
        for(int i = 0; i < s.length(); i++) {
            if(s.charAt(i) == '[') {
                in++;
            } else if(s.charAt(i) == ']') {
                in--;
                if(in == 0)
                    return s.substring(0, i+1);
            }
        }
        return null;
    }


}
