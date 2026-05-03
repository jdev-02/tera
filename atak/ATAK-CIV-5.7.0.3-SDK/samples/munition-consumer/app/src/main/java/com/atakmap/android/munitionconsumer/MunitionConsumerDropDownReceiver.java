
package com.atakmap.android.munitionconsumer;

import android.content.Context;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.BaseAdapter;
import android.widget.ListView;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.databridge.Dataset;
import com.atakmap.android.databridge.DatasetProvider;
import com.atakmap.android.databridge.DatasetProviderCallback;
import com.atakmap.android.databridge.DatasetProviderManager;
import com.atakmap.android.databridge.DatasetQueryParam;
import com.atakmap.android.gui.PluginSpinner;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.munitionconsumer.plugin.R;
import com.atakmap.android.dropdown.DropDown.OnStateListener;
import com.atakmap.android.dropdown.DropDownReceiver;

import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

public class MunitionConsumerDropDownReceiver extends DropDownReceiver implements
        OnStateListener {

    public static final String TAG = MunitionConsumerDropDownReceiver.class
            .getSimpleName();

    public static final String SHOW_PLUGIN = "com.atakmap.android.windconsumer.SHOW_PLUGIN";
    private final View templateView;
    private final Context pluginContext;
    private final ListView listView;

    private GeoPoint active;

    private DatasetProvider munitionProvider = null;

    /**************************** CONSTRUCTOR *****************************/

    public MunitionConsumerDropDownReceiver(final MapView mapView,
                                            final Context context) {
        super(mapView);
        this.pluginContext = context;

        // Remember to use the PluginLayoutInflator if you are actually inflating a custom view
        // In this case, using it is not necessary - but I am putting it here to remind
        // developers to look at this Inflator
        templateView = PluginLayoutInflater.inflate(context,
                R.layout.main_layout, null);

        listView = templateView.findViewById(R.id.listview);

        Collection<DatasetProvider> providers = DatasetProviderManager.getInstance().getDatasetProviders();
        for (DatasetProvider provider: providers) {
            if (provider.getUID().equals("ada5be38-9d4c-4d67-a731-7741d2a9410d")) {
                munitionProvider = provider;
            }
        }

        PluginSpinner spinner = templateView.findViewById(R.id.groups);


        final String[] array = new String[] { "All", "Fixed", "Rotary", "Unguided_Mortar",
                                        "Unguided_Cannon", "Precision_Guided", "Naval Gunfire",
                                        "Tomahawk", "Nato", "Antiaircraft", "Surface_To_Air",
                                        "Minimum_Safe_Distances" };

        ArrayAdapter<String> adapter = new ArrayAdapter<>(context,
                android.R.layout.simple_spinner_item, array);
        spinner.setAdapter(adapter);
        spinner.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> adapterView, View view, int i, long l) {
                if (array[i].equals("All")) {
                    List<DatasetQueryParam> datasetQueryParams = new ArrayList<>();
                    munitionProvider.subscribe(MunitionConsumerDropDownReceiver.class.getSimpleName(),
                            datasetQueryParams, callback);
                } else {
                    munitionProvider.subscribe(MunitionConsumerDropDownReceiver.class.getSimpleName(),
                            Collections.singletonList(new DatasetQueryParam("group", DatasetQueryParam.Operation.EQUALS, array[i])), callback);

                }
            }

            @Override
            public void onNothingSelected(AdapterView<?> adapterView) {

            }
        });


        
        if (munitionProvider != null) {
            List<DatasetQueryParam> datasetQueryParams = new ArrayList<>();
            munitionProvider.subscribe(MunitionConsumerDropDownReceiver.class.getSimpleName(),
                    datasetQueryParams, callback);
        } else {
            TextView view = templateView.findViewById(R.id.supported);
            spinner.setVisibility(View.GONE);
            view.setVisibility(View.VISIBLE);
            view.setText(pluginContext.getString(R.string.warning));
        }
    }

    private final DatasetProviderCallback callback = new DatasetProviderCallback() {
        @Override
        public void onData(String s, DatasetProvider provider, List<DatasetQueryParam> list, List<Dataset> datasets,
                           Status status, String msg) {
            if (status == Status.COMPLETE)
                provider.unsubscribe(this);
            getMapView().post(new Runnable() {
                @Override
                public void run() {
                    listView.setAdapter(new DatasetAdapter(pluginContext, datasets));
                }
            });
        }
    };

    /**************************** PUBLIC METHODS *****************************/

    public void disposeImpl() {
    }

    /**************************** INHERITED METHODS *****************************/

    @Override
    public void onReceive(Context context, Intent intent) {

        final String action = intent.getAction();
        if (action == null)
            return;

        if (action.equals(SHOW_PLUGIN)) {

            Log.d(TAG, "showing plugin drop down");
            showDropDown(templateView, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH,
                    HALF_HEIGHT, false, this);
        }
    }

    @Override
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
    }



    public static class ProviderAdapter extends BaseAdapter {

        private final List<DatasetProvider> providers;
        private final Context context;

        public ProviderAdapter(Context context, List<DatasetProvider> providers) {
            this.providers = providers;
            this.context = context;
        }


        @Override
        public int getCount() {
            return providers.size();
        }

        @Override
        public Object getItem(int position) {
            return providers.get(position);
        }

        @Override
        public long getItemId(int position) {
            return position;
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            TextView tv = new TextView(context);
            DatasetProvider dp = providers.get(position);
            tv.setText(dp.getName());
            return tv;
        }
    }

    public static class DatasetAdapter extends BaseAdapter {

        private final List<Dataset> datasets;
        private final Context pluginContext;

        public DatasetAdapter(Context pluginContext, List<Dataset> datasets) {
            this.datasets = datasets;
            this.pluginContext = pluginContext;
        }


        @Override
        public int getCount() {
            return datasets.size();
        }

        @Override
        public Object getItem(int position) {
            return datasets.get(position);
        }

        @Override
        public long getItemId(int position) {
            return position;
        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            final View result;

            if (convertView == null) {
                result = LayoutInflater.from(pluginContext).inflate(R.layout.munition_info, parent, false);
            } else {
                result = convertView;
            }
            Holder h = (Holder)result.getTag();
            if (h == null) {
                h = new Holder();
                h.name = result.findViewById(R.id.name);
                h.description = result.findViewById(R.id.description);
                h.group = result.findViewById(R.id.group);
                h.category = result.findViewById(R.id.category);
                h.standing = result.findViewById(R.id.standing);
                h.prone = result.findViewById(R.id.prone);
                h.proneprotected = result.findViewById(R.id.proneprotected);
                h.ricochetfan = result.findViewById(R.id.ricochetfan);
                result.setTag(h);
            }
            Dataset dp = datasets.get(position);

            h.name.setText(dp.get("weapon_name", "unknown"));
            h.description.setText(dp.get("weapon_description", "unknown"));
            h.group.setText(dp.get("group", "unknown"));
            h.category.setText(dp.get("category", "unknown"));
            h.standing.setText(String.format(Locale.getDefault(), "%d", dp.get("weapon_standing", 0)));
            h.prone.setText(String.format(Locale.getDefault(), "%d", dp.get("weapon_prone", 0)));
            h.proneprotected.setText(String.format(Locale.getDefault(), "%d", dp.get("weapon_proneprotected", 0)));

            int deg = dp.get("weapon_ricochetfan_angle", 0);
            int meters = dp.get("weapon_ricochetfan_distance", 0);
            if (deg > 0 && meters > 0) {
                h.ricochetfan.setText(
                    String.format(Locale.getDefault(), "%d\u00B0 / %dm", deg, meters));
            } else {
                h.ricochetfan.setText("");
            }
            return result;
        }
    }

    private static class Holder {
        TextView name;
        TextView description;
        TextView group;
        TextView category;
        TextView standing;
        TextView prone;
        TextView proneprotected;
        TextView ricochetfan;
    }

}
