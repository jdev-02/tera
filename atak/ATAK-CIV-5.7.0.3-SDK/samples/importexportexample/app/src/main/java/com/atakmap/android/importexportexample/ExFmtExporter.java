package com.atakmap.android.importexportexample;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Environment;
import android.preference.PreferenceManager;
import android.widget.Toast;

import com.atakmap.android.hierarchy.HierarchyListItem;
import com.atakmap.android.importexport.ExportFileMarshal;

import com.atakmap.android.importexport.Exportable;
import com.atakmap.android.importexport.FormatNotSupportedException;
import com.atakmap.android.maps.MapGroup;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.maps.Marker;

import com.atakmap.android.missionpackage.export.MissionPackageExportWrapper;

import com.atakmap.coremap.filesystem.FileSystemUtils;

import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.conversion.EGM96;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPointMetaData;


import java.io.File;
import java.io.FileOutputStream;

import java.io.IOException;
import java.io.PrintStream;

import java.util.Collection;

import java.util.LinkedList;


public class ExFmtExporter extends ExportFileMarshal {

    private static final String TAG = "ExFmtExporter";

    private Collection<String> exportItemUIDs;

    public ExFmtExporter(Context context) {
        super(context, ExFmtImporter.CONTENT_TYPE, ExFmtImporter.TEXT_CSV, -1);

        this.exportItemUIDs = new LinkedList<>();
    }

    @Override
    public Class getTargetClass() {
        // We're going to use the `MissionPackageExportWrapper` -- this class
        // will gather up the UIDs of all items from the Overlay Manager that
        // the user has selected for export.
        return MissionPackageExportWrapper.class;
    }

    @Override
    public File getFile() {
        // The filename is provided by the base class member, `filename`. This
        // method should generate the full file path, based on a known export
        // directory for export type.

        // For purposes of this example, we'll export to the `exfmt_exports`
        // in the storage root
        File exportDir = new File(Environment.getExternalStorageDirectory(), "exfmt_exports");
        if(!exportDir.exists())
            exportDir.mkdir();

        // create the absolute path to the export file
        return new File(
                exportDir,
                filename);
    }

    @Override
    protected boolean marshal(Exportable export)
            throws FormatNotSupportedException {

        // This method will get invoked for every `HierarchyListItem` that the
        // user has selected for export. We use this method to transform those
        // selected items into the representation that we'll require for the
        // actual export operation.
        if (export == null || !export.isSupported(getTargetClass())) {
            Log.d(TAG, "Skipping unsupported export "
                    + (export == null ? "" : export.getClass().getName()));
            return false;
        }

        // For purposes of this example, we're leveraging the
        // `MissionPackageExportWrapper` to obtain the UIDs of all
        // selections. We'll pull the actual `MapItem` instances from the UIDs
        // at export time.
        MissionPackageExportWrapper mp = (MissionPackageExportWrapper) export.toObjectOf(getTargetClass(), getFilters());
        if (mp == null || mp.getUIDs() == null || mp.getUIDs().isEmpty()) {
            Log.d(TAG, "Skipping empty folder");
            return false;
        }

        // append the UIDs for the selection
        this.exportItemUIDs.addAll(mp.getUIDs());
        return true;
    }

    @Override
    protected String getExtension() {
        return "exfmt";
    }

    @Override
    public void finalizeMarshal() throws IOException {
        // perform the actual export
        try {
            exportImpl();
        } catch(Throwable t) {
            MapView.getMapView().post(new Runnable() {
                public void run() {
                    Toast.makeText(MapView.getMapView().getContext(), "Export Failed", Toast.LENGTH_LONG).show();
                }
            });
            if(t instanceof IOException)
                throw (IOException)t;
            IOException toThrow = new IOException();
            toThrow.initCause(t);
            throw toThrow;
        }
    }

    private void exportImpl() throws IOException {
        try {
            synchronized (this) {
                if (this.isCancelled) {
                    Log.d(TAG, "Cancelled, in finalizeMarshal");
                    return;
                }
            }

            if (this.exportItemUIDs.isEmpty()) {
                throw new IOException("No Items Selected");
            }

            final File file = getFile();
            PrintStream writer = null;
            try {
                // delete existing file, and then serialize TGS out to file
                if (file.exists()) {
                    FileSystemUtils.deleteFile(file);
                }

                writer = new PrintStream(new FileOutputStream(file));

                int i = 0;
                final int limit = this.exportItemUIDs.size();
                final MapGroup rootGroup = MapView.getMapView().getRootGroup();
                for (String uid : this.exportItemUIDs) {
                    i++;
                    synchronized (this) {
                        if (this.isCancelled) {
                            Log.d(TAG, "Cancelled, in finalizeMarshal");
                            return;
                        }
                    }

                    // find the item corresponding to the UID
                    MapItem item = rootGroup.deepFindUID(uid);

                    // only handling `Marker` for purposes of the example
                    if(item instanceof Marker) {
                        StringBuilder line = new StringBuilder();
                        line.append(item.getUID()); // uid
                        line.append(',').append(((Marker)item).getTitle()); // callsign
                        line.append(',').append(item.getType()); // type
                        GeoPointMetaData lla = ((Marker)item).getGeoPointMetaData();
                        line.append(',').append(lla.get().getLatitude()); // latitude
                        line.append(',').append(lla.get().getLongitude()); // longitude
                        // altitude
                        line.append(',');
                        if(!Double.isNaN(lla.get().getAltitude())) line.append(lla.get().getAltitude());
                        // remarks
                        line.append(',');
                        if(item.getRemarks() != null) line.append(item.getRemarks());

                        writer.println(line);
                    }
                    if (hasProgress()) {
                        this.progress.publish((int) (((double) i / (double) limit) * 100d));
                    }
                }

                Log.d(TAG, "Exported: " + file.getAbsolutePath());
            } finally {
                if(writer != null)
                    writer.close();
            }
        } finally {
            this.exportItemUIDs.clear();
        }
    }

    @Override
    public boolean filterListItemImpl(HierarchyListItem item) {
        // specific filter for `HierarchyListItem` instances -- returns `true`
        // if the supplied item should be filtered out from the items available
        // for the user to choose; `false` if the item should be displayed to
        // the user.
        return !this.accept(item);
    }
    @Override
    public boolean accept(HierarchyListItem item) {
        // returns `true` if the specified item should be displayed to the user
        // in the export list, `false` if it should be filtered out. Note that
        // the result of `accept` is the _opposite_ of the result of `filter`!
        final Object userObject = item.getUserObject();
        if (!(userObject instanceof MapItem))
            return true;
        return !filterItem((MapItem) userObject);
    }

    @Override
    public boolean filterItem(MapItem item) {
        // specific filter for `MapItem` instances -- returns `true` if the
        // supplied item should be filtered out from the items available for
        // the user to choose; `false` if the item should be displayed to
        // the user.
        if (item == null || !(item instanceof Exportable))
            return true;

        // verify item is a marker
        if(!(item instanceof Marker))
            return true;

        // the item meets all our criteria, allow it to pass
        return false;
    }
}
