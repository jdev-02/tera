
package com.atakmap.android.plugins;

import java.io.File;
import java.io.IOException;
import java.util.List;

import com.atakmap.android.importexport.Importer;
import com.atakmap.android.importexport.ImporterManager;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.plugins.VideoOverlay.R;
import com.atakmap.android.util.NotificationUtil;
import com.atakmap.coremap.log.Log;
import com.atakmap.comms.CommsMapComponent.ImportResult;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.SharedPreferences;
import android.graphics.Point;
import android.net.Uri;
import android.os.Environment;
import android.preference.PreferenceManager;
import android.util.AttributeSet;
import android.view.Display;
import android.view.LayoutInflater;
import android.view.View;
import android.view.WindowManager;
import android.view.View.OnClickListener;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.RelativeLayout;
import android.widget.TextView;
import android.widget.Toast;

public class VideoOverlayView extends LinearLayout {

    private static final String TAG = "ImportManagerView";

    private static final String IMPORT_LINKS_XML = "import_links.xml";

    private MapView _mapView;
    private VideoOverlayAdapter _adapter;
    private ListView _list;
    private SharedPreferences defaultPrefs;

    /**
    * Each time ATAK starts, auto refresh is disabled, user must explicitly enable it
    */
    boolean bFirstLoad;

    public VideoOverlayView(Context context, AttributeSet attrs) {
        super(context, attrs);

        defaultPrefs = PreferenceManager.getDefaultSharedPreferences(context);
    }

    public VideoOverlayAdapter getAdapter() {
        return _adapter;
    }

    void initView(MapView mapView, VideoOverlayManager mgr) {
        _mapView = mapView;

        Button btnNewImportResourcee = (Button) findViewById(
                R.id.importmgr_importBtn);
        btnNewImportResourcee.setOnClickListener(new OnClickListener() {

            @Override
            public void onClick(View v) {
                importLocalFile();
            }
        });

        _list = (ListView) findViewById(R.id.importmgr_resource_list);
        _adapter = new VideoOverlayAdapter(_mapView, this, mgr);
        _list.setAdapter(_adapter);
    }

    private void importLocalFile() {
        LayoutInflater inflater = LayoutInflater.from(this.getContext());
        final VideoOverlayManagerFileBrowser importView = (VideoOverlayManagerFileBrowser) inflater
                .inflate(R.layout.import_manager_file_browser, null);

        final String _lastDirectory = defaultPrefs.getString("lastDirectory",
                Environment.getExternalStorageDirectory().getPath());

        importView.setStartDirectory(_lastDirectory);
        importView.setExtensionTypes(new String[] {
                "mpg", "mpeg", "ts"
        });
        AlertDialog.Builder b = new AlertDialog.Builder(_mapView.getContext());
        b.setView(importView);

        // There doesn't appear to be an easy way to directly modify the size
        // of the dialog title, so create a new text view and change the font
        // size and padding to make things look nicer.
        TextView titleView = new TextView(_mapView.getContext());
        titleView.setTextSize(20);
        titleView.setTextColor(_mapView.getResources().getColor(
                android.R.color.holo_blue_light));
        titleView.setPadding(7, 7, 7, 7);
        titleView.setText("Select Files to Import");
        b.setCustomTitle(titleView);

        b.setNegativeButton("Cancel", null);
        b.setPositiveButton("OK", new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                // User has selected items and touched OK. Import the data.
                List<File> selectedFiles = importView.getSelectedFiles();

                if (selectedFiles.size() == 0) {
                    Toast.makeText(_mapView.getContext(),
                            "No Files Were Selected to Import!",
                            Toast.LENGTH_SHORT).show();
                    ;
                } else {
                    // Store the currently displayed directory so we can open it
                    // again the next time this dialog is opened.
                    defaultPrefs
                            .edit()
                            .putString("lastDirectory",
                                    selectedFiles.get(0).getParent())
                            .commit();

                    final Importer importer = ImporterManager.findImporter(
                            VideoOverlayImporter.CONTENT_TYPE,
                            VideoOverlayImporter.MPEG2_TS_MIME);
                    if (importer != null) {
                        // Iterate over all of the selected files and begin an import task.
                        ImportResult result;
                        for (File file : selectedFiles) {
                            Log.d(TAG,
                                    "Adding Video Overlay: "
                                            + file.getAbsolutePath());
                            try {
                                result = importer.importData(
                                        Uri.fromFile(file),
                                        VideoOverlayImporter.MPEG2_TS_MIME,
                                        null);
                            } catch (IOException e) {
                                Log.e(TAG, "Failed to import video overlay: "
                                        + file.getAbsolutePath(), e);
                                result = ImportResult.FAILURE;
                            }

                            if (result != ImportResult.SUCCESS)
                                NotificationUtil
                                        .getInstance()
                                        .postNotification(
                                                com.atakmap.app.R.drawable.select_point_icon,
                                                "Failed to load Video", null,
                                                file.getAbsolutePath());
                        }
                    } else {
                        Log.w(TAG, "Failed to find Video Overlay importer");
                    }
                }
            }
        });
        final AlertDialog alert = b.create();

        // This also tells the importView to handle the back button presses
        // that the user provides to the alert dialog.
        importView.setAlertDialog(alert);

        // Find the current width of the window, we will use this in a minute to determine how large
        // to make the dialog.
        WindowManager wm = (WindowManager) _mapView.getContext()
                .getSystemService(Context.WINDOW_SERVICE);
        Display display = wm.getDefaultDisplay();
        Point p = new Point();
        display.getSize(p);

        // Show the dialog
        alert.show();

        // Copy over the attributes from the displayed window and then set the width
        // to be 70% of the total window width
        WindowManager.LayoutParams lp = new WindowManager.LayoutParams();
        lp.copyFrom(alert.getWindow().getAttributes());
        lp.width = (int) (p.x * .70);
        lp.height = WindowManager.LayoutParams.MATCH_PARENT;

        alert.getWindow().setAttributes(lp);
    }
}
