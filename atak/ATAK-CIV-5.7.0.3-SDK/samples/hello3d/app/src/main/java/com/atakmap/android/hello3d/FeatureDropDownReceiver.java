package com.atakmap.android.hello3d;

import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.TextView;

import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.dropdown.DropDown.OnStateListener;

import com.atakmap.android.maps.MapGroup;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;

import com.atakmap.coremap.log.Log;

import com.atakmap.android.hello3d.plugin.R;

import com.atakmap.map.layer.feature.DataSourceFeatureDataStore;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.Utils;

public class FeatureDropDownReceiver extends DropDownReceiver implements
        OnStateListener {

    private final FeatureDataStore2 spatialDb;
    public static final String TAG = "FeatureDropDownReceiver";

    public View view;

    private double currWidth = HALF_WIDTH;
    private double currHeight = HALF_HEIGHT;

    public FeatureDropDownReceiver(
            MapView mapView, Context pluginContext,
            FeatureDataStore2 spatialDb) {
        super(mapView);
        this.spatialDb = spatialDb;

        LayoutInflater inflater = LayoutInflater.from(pluginContext);
 
        view = inflater.inflate(R.layout.simple_view, null);
        
    }

    @Override
    public void onReceive(final Context context, Intent intent) {
        String action = intent.getAction();
        final MapItem item = findTarget(intent.getStringExtra("targetUID"));
        if (action == null)
            return;

        long fid = item.getMetaLong("featureid", -1);
        if (fid < 0) {
            Log.d(TAG, "could not find featureid");
            return;
        }
        TextView tv = (TextView)view.findViewById(R.id.title);
        Feature f = null;
        try {
            f = Utils.getFeature(spatialDb, fid);
        } catch (Exception e) {
            Log.d(TAG, "could not find feature described by id " + fid);
            return;
        }
        if (f == null) {
            Log.d(TAG, "could not find feature described by id " + fid);
            return;
        }

        tv.setText(f.getName());



        // set up the view as appropriate 
        showDropDown(view,
                     HALF_WIDTH,
                     FULL_HEIGHT,
                     FULL_WIDTH,
                     HALF_HEIGHT, this);

    }


    @Override
    public void onDropDownSizeChanged(double width, double height) {
        Log.d(TAG, "resizing width=" + width + " height=" + height);
        currWidth = width;
        currHeight = height;
    }

    @Override
    public void onDropDownClose() {
    }

    @Override
    public void onDropDownSelectionRemoved() {
    }

    @Override
    public void onDropDownVisible(boolean v) {
    }

    @Override
    protected void onStateRequested(int state) {
        if (state == DROPDOWN_STATE_FULLSCREEN) {
            if (!isPortrait()) {
                if (Double.compare(currWidth, HALF_WIDTH) == 0) {
                    resize(FULL_WIDTH - HANDLE_THICKNESS_LANDSCAPE,
                            FULL_HEIGHT);
                }
            } else {
                if (Double.compare(currHeight, HALF_HEIGHT) == 0) {
                    resize(FULL_WIDTH, FULL_HEIGHT - HANDLE_THICKNESS_PORTRAIT);
                }
            }
        } else if (state == DROPDOWN_STATE_NORMAL) {
            if (!isPortrait()) {
                resize(HALF_WIDTH, FULL_HEIGHT);
            } else {
                resize(FULL_WIDTH, HALF_HEIGHT);
            }
        }
    }

    @Override
    public void disposeImpl() {
    }


    private MapItem findTarget(final String targetUID) {
        if (targetUID != null) {
            MapGroup rootGroup = getMapView().getRootGroup();
            return rootGroup.deepFindItem("uid", targetUID);
        } else {
            return null;
        }
    }
}
