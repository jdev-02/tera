
package com.atakmap.android.elevation.dsm;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.ImageView;
import android.widget.ListAdapter;
import android.widget.ListView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import com.atakmap.android.dropdown.DropDown.OnStateListener;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.elevation.dsm.plugin.R;
import com.atakmap.android.gui.PluginSpinner;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.layers.LayerSelection;
import com.atakmap.android.layers.LayerSelectionAdapter;
import com.atakmap.android.maps.MapCoreIntentsComponent;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.maps.MapView.RenderStack;
import com.atakmap.android.preference.AtakPreferences;
import com.atakmap.coremap.conversions.Span;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.elevation.ElevationData;
import com.atakmap.map.layer.Layer;
import com.atakmap.map.layer.feature.DataStoreException;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.FeatureLayer3;
import com.atakmap.map.layer.raster.OutlinesFeatureDataStore2;
import com.atakmap.map.layer.raster.RasterLayer2;

import java.io.File;
import java.lang.ref.WeakReference;
import java.util.Comparator;

import gov.tak.platform.util.LimitingThread;

public class DSMManagerDropDownReceiver extends DropDownReceiver
        implements OnStateListener {
    public static String TAG = "DSMManagerDropDownReceiver";

    public static final String SHOW_DSM_TOOL = "com.atakmap.android.elevation.dsm.SHOW_DSM_MANAGER";
    private final View dsmView;
    private final MapView mapView;
    private final Context pluginContext;
    private ListView dsmOverlaysList;
    private final RasterLayer2 dsmRasterLayer;
    private Layer outlinesLayer;
    private AtakPreferences prefs;

    private final DSMDatabase.OnContentChangedListener _contentChangedHandler  = new DSMDatabase.OnContentChangedListener() {
        @Override
        public void onContentChanged() {
            refreshDsm();
        }
    };

    public DSMManagerDropDownReceiver(final MapView mapView,
            final Context context, final RasterLayer2 rasterlayer) {
        super(mapView);
        this.pluginContext = context;
        this.mapView = mapView;
        prefs = AtakPreferences.getInstance(mapView.getContext());
        this.dsmRasterLayer = rasterlayer;


        this.outlinesLayer = new FeatureLayer3("DSM Outlines",
                new OutlinesFeatureDataStore2(rasterlayer, -1, false));
        this.outlinesLayer.setVisible(true);
        try {
            ((FeatureLayer3) this.outlinesLayer).getDataStore()
                    .setFeaturesVisible(new FeatureDataStore2.FeatureQueryParameters(), true);
        } catch(DataStoreException ignored) {}

        // Use the inflater service to get the UI ready to show
        LayoutInflater inflater = (LayoutInflater) context
                .getSystemService(context.LAYOUT_INFLATER_SERVICE);

        // Inflate or load the UI
        dsmView = inflater.inflate(R.layout.dsm_manager_layout, null);

        dsmView.findViewById(R.id.dsmrefresh).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                lt.exec();
            }
        });

        dsmOverlaysList = dsmView
                .findViewById(R.id.listView);
        dsmOverlaysList.setEmptyView(dsmView.findViewById(R.id.empty));

        final Switch dsmEnabled = dsmView.findViewById(R.id.dsmEnabled);
        dsmEnabled.setSelected(prefs.get("dsm.enabled", true));

        dsmView.findViewById(R.id.dsmEnabled).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                prefs.set("dsm.enabled",dsmEnabled.isChecked());
            }
        });

        dsmOverlaysList.setOnTouchListener(new View.OnTouchListener() {
            // Setting on Touch Listener for handling the touch inside ScrollView
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                // Disallow the touch request for parent scroll on touch of child view
                v.getParent().requestDisallowInterceptTouchEvent(true);
                return false;
            }
        });

        DSMManager.getDb().addOnContentChangedListener(_contentChangedHandler);
    }

    @Override
    public void disposeImpl() {
        DSMManager.getDb().removeOnContentChangedListener(_contentChangedHandler);
    }

    private void refreshDsm() {
        if(isClosed())
            return;

        if (outlinesLayer != null)
            mapView.removeLayer(RenderStack.MAP_SURFACE_OVERLAYS, outlinesLayer);

        outlinesLayer = new FeatureLayer3("DSM Outlines",
                new OutlinesFeatureDataStore2(dsmRasterLayer, -1, false));
        outlinesLayer.setVisible(true);
        try {
            ((FeatureLayer3) outlinesLayer).getDataStore()
                    .setFeaturesVisible(new FeatureDataStore2.FeatureQueryParameters(), true);
        } catch(DataStoreException ignored) {}

        mapView.addLayer(RenderStack.MAP_SURFACE_OVERLAYS, outlinesLayer);

        LayerSelectionAdapter adapter = createAdapter(dsmRasterLayer, null, mapView, mapView.getContext());
        mapView.post(new Runnable() {
            @Override
            public void run() {
                dsmOverlaysList.setAdapter(adapter);
            }
        });
    }

    LimitingThread lt = new LimitingThread("dsm-monitor", new Runnable() {
        @Override
        public void run() {
            // invoked to catch a case where a datapackage containing a DSM file is sent to a user
            DSMManager.refresh();
            refreshDsm();
            try {
                Thread.sleep(5000);
            } catch (Exception ignored) {}
        }
    });

    @Override
    public void onReceive(final Context context, Intent intent) {

        final String action = intent.getAction();
        if (action == null)
            return;

        if (action.equals(SHOW_DSM_TOOL)) {
            // Begin building the view starting with the tabhost
            //lt.exec();
            
            // Show the weather GUI with initial size options and which callbacks to use
            // The 'this' pointer will call onDropDownClose if GUI is closed afterwards
            showDropDown(dsmView, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH,
                    HALF_HEIGHT, this);
            setAssociationKey("dsm_manager_preferences");

            // XXX - should just be visible by default...

            try {
                ((FeatureLayer3) this.outlinesLayer).getDataStore()
                        .setFeaturesVisible(new FeatureDataStore2.FeatureQueryParameters(), true);
            } catch(DataStoreException ignored) {}

            mapView.addLayer(RenderStack.MAP_SURFACE_OVERLAYS, outlinesLayer);



            LayerSelectionAdapter adapter = createAdapter(dsmRasterLayer, null, mapView, mapView.getContext());
            dsmOverlaysList.setAdapter(adapter);
        }
    }

    private LayerSelectionAdapter createAdapter(RasterLayer2 wxRasterLayer, Object o, MapView mapView, Context context) {
        LayerSelectionAdapter adapter = new LayerSelectionAdapter(
                wxRasterLayer, null,
                mapView, mapView.getContext()) {

            @Override
            protected View getViewImpl(final LayerSelection sel,
                                       final int position, View convertView,
                                       ViewGroup parent) {

                final ElevationInfo info = DSMManager.getDb()
                        .getElevationInfo(sel.getName());

                // First, inflate the overlay list item layout to get the main view
                LayoutInflater inflater = LayoutInflater
                        .from(pluginContext);
                View view = inflater.inflate(
                        R.layout.dsm_manager_list_item, null);

                // Set the name of each wx report overlay
                TextView title = view
                        .findViewById(R.id.dsm_item_title);
                title.setText(new File(sel.getName()).getName());

                TextView desc = view
                        .findViewById(R.id.dsm_item_desc);
                StringBuilder descStr = new StringBuilder();
                if (info != null) {
                    switch (info.model) {
                        case ElevationData.MODEL_SURFACE:
                            descStr.append("Surface ");
                            break;
                        case ElevationData.MODEL_TERRAIN:
                            descStr.append("Terrain ");
                            break;
                        case (ElevationData.MODEL_SURFACE
                                | ElevationData.MODEL_TERRAIN):
                            descStr.append("Terrain+Surface ");
                            break;
                        default:
                            throw new IllegalArgumentException();
                    }

                    descStr.append(info.units.getAbbrev());
                    descStr.append(" ");
                    descStr.append(info.reference);
                }
                desc.setText(descStr);

                // Get the visibility toggle and attach a listener
                ImageView panToButton = view
                        .findViewById(R.id.dsm_pan_to);
                panToButton.setOnClickListener(new View.OnClickListener() {
                    // When toggle is selected, set visibility to opposite of current
                    public void onClick(View v) {
                        Intent panto = new Intent(
                                MapCoreIntentsComponent.ACTION_PAN_ZOOM);
                        panto.putExtra("shape",
                                new String[] {
                                        (new GeoPoint(sel.getNorth(),
                                                sel.getWest())).toString(),
                                        (new GeoPoint(sel.getSouth(),
                                                sel.getEast())).toString(),
                                });
                        AtakBroadcast.getInstance().sendBroadcast(panto);
                    }
                });

                // Get the visibility toggle and attach a listener
                ImageView editButton = view
                        .findViewById(R.id.dsm_edit);
                editButton.setOnClickListener(new View.OnClickListener() {
                    // When toggle is selected, set visibility to opposite of current
                    public void onClick(View v) {
                        if (info == null) {
                            Toast.makeText(mapView.getContext(),
                                    "Item cannot be edited.",
                                    Toast.LENGTH_SHORT).show();
                            return;
                        }

                        AlertDialog.Builder builderVal = new AlertDialog.Builder(
                                mapView.getContext());
                        builderVal.setTitle("Edit "
                                + (new File(sel.getName())).getName());
                        View holder = View.inflate(pluginContext,
                                R.layout.dsm_item_editor, null);
                        builderVal.setView(holder);

                        final PluginSpinner modelSpinner = holder
                                .findViewById(R.id.dsm_edit_model_spinner);
                        setSpinnerOptions(mapView.getContext(),
                                modelSpinner, new String[] {
                                        "Surface", "Terrain",
                                        "Terrain+Surface"
                                });
                        switch (info.model) {
                            case ElevationData.MODEL_SURFACE:
                                modelSpinner.setSelection(0);
                                break;
                            case ElevationData.MODEL_TERRAIN:
                                modelSpinner.setSelection(1);
                                break;
                            case (ElevationData.MODEL_SURFACE
                                    | ElevationData.MODEL_TERRAIN):
                                modelSpinner.setSelection(2);
                                break;
                            default:
                                throw new IllegalArgumentException();
                        }

                        final PluginSpinner unitSpinner = holder
                                .findViewById(R.id.dsm_edit_units_spinner);
                        setSpinnerOptions(mapView.getContext(), unitSpinner,
                                new String[] {
                                        Span.METER.getPlural(),
                                        Span.FOOT.getPlural()
                                });
                        switch (info.units) {
                            case METER:
                                unitSpinner.setSelection(0);
                                break;
                            case FOOT:
                                unitSpinner.setSelection(1);
                                break;
                            default:
                                throw new IllegalArgumentException();
                        }

                        final PluginSpinner referenceSpinner = holder
                                .findViewById(
                                        R.id.dsm_edit_reference_spinner);
                        setSpinnerOptions(mapView.getContext(),
                                referenceSpinner, new String[] {
                                        "HAE",
                                        "MSL"
                                });
                        switch (info.reference) {
                            case "HAE":
                                referenceSpinner.setSelection(0);
                                break;
                            case "MSL":
                                referenceSpinner.setSelection(1);
                                break;
                            default:
                                throw new IllegalArgumentException();
                        }

                        builderVal.setPositiveButton("OK",
                                new DialogInterface.OnClickListener() {
                                    @Override
                                    public void onClick(
                                            DialogInterface dialog,
                                            int which) {
                                        // XXX -
                                        int editModel = info.model;
                                        if (modelSpinner.getSelectedItem()
                                                .equals("Surface"))
                                            editModel = ElevationData.MODEL_SURFACE;
                                        else if (modelSpinner
                                                .getSelectedItem()
                                                .equals("Terrain"))
                                            editModel = ElevationData.MODEL_TERRAIN;
                                        else if (modelSpinner
                                                .getSelectedItem()
                                                .equals("Terrain+Surface"))
                                            editModel = ElevationData.MODEL_TERRAIN
                                                    | ElevationData.MODEL_SURFACE;

                                        Span editUnits = Span
                                                .findFromPluralName(
                                                        (String) unitSpinner
                                                                .getSelectedItem());
                                        String editReference =
                                                (String) referenceSpinner
                                                        .getSelectedItem();

                                        DSMManager.getDb().update(
                                                sel.getName(),
                                                editModel,
                                                editReference,
                                                editUnits);

                                        notifyDataSetChanged();
                                    }
                                });
                        builderVal.show();

                    }
                });

                // Finally, the view is done, ready to show
                return view;
            }

            @Override
            protected Comparator getSortComparator() {
                return new Comparator<LayerSelection>() {
                    @Override
                    public int compare(LayerSelection ls1,
                                       LayerSelection ls2) {
                        return ls1.getName().compareToIgnoreCase(
                                ls2.getName());
                    }
                };
            }
        };

        return adapter;

    }

    private static void setSpinnerOptions(Context context,
            PluginSpinner spinner, String[] opts) {
        ArrayAdapter<String> adapter = new ArrayAdapter<>(context,
                android.R.layout.simple_spinner_item, opts);
        spinner.setAdapter(adapter);
    }

    public void onDropDownSelectionRemoved() {
    }

    @Override
    public void onDropDownVisible(boolean v) {
    }

    @Override
    public void onDropDownSizeChanged(double width, double height) {
    }

    @Override
    public void onDropDownClose() {
        mapView.removeLayer(RenderStack.MAP_SURFACE_OVERLAYS, outlinesLayer);
    }
}
