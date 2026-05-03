
package com.atakmap.android.plugins;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

import com.atakmap.android.maps.MapCoreIntentsComponent;
import com.atakmap.android.maps.Shape;
import com.atakmap.android.plugins.VideoOverlay.R;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import com.atakmap.map.AtakMapView;

import android.app.Activity;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.View;
import android.view.View.OnClickListener;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.ImageButton;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Manages list of RemoteResources from the UI perspective
 * 
 * @author byoung
 */
public class VideoOverlayAdapter extends BaseAdapter implements
        VideoOverlayManager.OnVideoOverlayListener {
    private final static Comparator<VideoOverlayLayer> NameSort = new Comparator<VideoOverlayLayer>() {

        @Override
        public int compare(VideoOverlayLayer lhs, VideoOverlayLayer rhs) {

            if (lhs == null && rhs == null)
                return 0;
            else if (lhs == null && rhs != null)
                return -1;
            else if (lhs != null && rhs == null)
                return 1;

            final String lhsName = lhs.getName();
            final String rhsName = rhs.getName();

            if (lhsName == null && rhsName == null)
                return 0;
            else if (lhsName == null && rhsName != null)
                return -1;
            else if (lhsName != null && rhsName == null)
                return 1;

            return lhsName.compareToIgnoreCase(rhsName);
        }
    };

    private static final String TAG = "ImportManagerResourceAdapter";

    private final List<VideoOverlayLayer> _overlays;
    private final AtakMapView _mapView;
    private final VideoOverlayView _view;
    private final VideoOverlayManager mgr;

    private boolean invalid;

    public VideoOverlayAdapter(AtakMapView mapView, VideoOverlayView view,
            VideoOverlayManager mgr) {
        _mapView = mapView;
        _view = view;
        _overlays = new ArrayList<VideoOverlayLayer>();
        this.mgr = mgr;

        this.invalid = true;

        this.mgr.addOnVideoOverlayListener(this);
    }

    private void validateNoSync() {
        this._overlays.clear();

        VideoOverlayLayer[] overlays = this.mgr.getOverlays();
        for (VideoOverlayLayer layer : overlays)
            this._overlays.add(layer);

        Collections.sort(this._overlays, NameSort);
        this.invalid = false;

        System.out.println("videooverlay VALIDATE " + _overlays.size()
                + " overlays");
    }

    @Override
    public synchronized int getCount() {
        if (this.invalid)
            this.validateNoSync();

        return _overlays.size();
    }

    @Override
    public synchronized Object getItem(int position) {
        if (this.invalid)
            this.validateNoSync();

        return _overlays.get(position);
    }

    @Override
    public synchronized long getItemId(int position) {
        if (this.invalid)
            this.validateNoSync();

        return this.getItem(position).hashCode();
    }

    @Override
    public synchronized View getView(int position, View convertView,
            final ViewGroup parent) {
        if (this.invalid)
            this.validateNoSync();

        LayoutInflater inf = LayoutInflater.from(parent.getContext());
        convertView = inf.inflate(R.layout.video_overlay_item, null);

        if (_overlays.size() <= position) {
            Log.w(TAG, "Unable to instantiate row view for position: "
                    + position);
            return null;
        }

        final VideoOverlayLayer overlay = _overlays.get(position);

        Log.i(TAG, " building view for index " + position + "; Video: "
                + overlay.getName());

        TextView txtName = (TextView) convertView
                .findViewById(R.id.video_file_text);
        txtName.setText(overlay.getName());

        ImageButton btnGoTo = (ImageButton) convertView
                .findViewById(R.id.video_goto_btn);
        btnGoTo.setOnClickListener(new OnClickListener() {

            @Override
            public void onClick(View v) {
                GeoPoint[] pts = new GeoPoint[4];
                for (int i = 0; i < pts.length; i++)
                    pts[i] = GeoPoint.createMutable();

                if (overlay.getFrameBounds( pts[0],
                         pts[1],
                         pts[2],
                         pts[3])) {

                    String[] spts = new String[pts.length];
                    for (int i = 0; i < pts.length; i++)
                        spts[i] = pts[i].toStringRepresentation();

                    // broadcast intent to zoom to video bounds
                    Intent intent = new Intent(
                            MapCoreIntentsComponent.ACTION_PAN_ZOOM);
                    intent.putExtra("shape", spts);

                    com.atakmap.android.ipc.AtakBroadcast.getInstance()
                            .sendBroadcast(intent);
                } else {
                    Toast.makeText(_mapView.getContext(),
                            "Metadata not available", Toast.LENGTH_SHORT);
                }
            }
        });

        ImageButton btnLock = (ImageButton) convertView
                .findViewById(R.id.video_lock_btn);

        // XXX - 
        btnLock.setEnabled(false);
        btnLock.setOnClickListener(new OnClickListener() {

            @Override
            public void onClick(View v) {
                // XXX - subscribe listener to receive updates and stay centered
                //       on frame at CURRENT zoom (allow user to adjust zoom and
                //       retain)
            }
        });

        ImageButton btnDelete = (ImageButton) convertView
                .findViewById(R.id.video_remove_btn);
        btnDelete.setOnClickListener(new OnClickListener() {

            @Override
            public void onClick(View v) {
                mgr.remove(overlay);
            }
        });

        return convertView;

    }

    @Override
    public boolean hasStableIds() {
        return true;
    }

    private void invalidateNoSync() {
        this.invalid = true;
        System.out.println("videooverlay INVALIDATE ADAPTER");
        _mapView.post(new Runnable() {
            @Override
            public void run() {
                notifyDataSetChanged();
            }
        });
    }

    /**************************************************************************/

    @Override
    public synchronized void onVideoOverlayAdded(VideoOverlayLayer overlay) {
        this.invalidateNoSync();
    }

    @Override
    public synchronized void onVideoOverlayRemoved(VideoOverlayLayer overlay) {
        this.invalidateNoSync();
    }
}
