
package com.atakmap.android.windconsumer;

import android.content.Context;
import android.content.Intent;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.BaseAdapter;
import android.widget.Button;
import android.widget.ListView;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.databridge.Dataset;
import com.atakmap.android.databridge.DatasetDefinition;
import com.atakmap.android.databridge.DatasetProvider;
import com.atakmap.android.databridge.DatasetProviderCallback;
import com.atakmap.android.databridge.DatasetProviderManager;
import com.atakmap.android.databridge.DatasetQueryParam;
import com.atakmap.android.gui.PluginSpinner;
import com.atakmap.android.gui.coordinateentry.CoordinateEntryCapability;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.windconsumer.plugin.R;
import com.atakmap.android.dropdown.DropDown.OnStateListener;
import com.atakmap.android.dropdown.DropDownReceiver;

import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPointMetaData;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

public class WindConsumerDropDownReceiver extends DropDownReceiver implements
        OnStateListener {

    public static final String TAG = WindConsumerDropDownReceiver.class
            .getSimpleName();

    public static final String SHOW_PLUGIN = "com.atakmap.android.windconsumer.SHOW_PLUGIN";
    private final View templateView;
    private final Context pluginContext;
    private final ListView listView;
    private final Button pull;
    private final Button refresh;
    private final PluginSpinner spinner;
    private final TextView information;

    private GeoPoint active;

    private List<DatasetProvider> windproviders = new ArrayList<>();

    /**************************** CONSTRUCTOR *****************************/

    public WindConsumerDropDownReceiver(final MapView mapView,
                                        final Context context) {
        super(mapView);
        this.pluginContext = context;

        // Remember to use the PluginLayoutInflator if you are actually inflating a custom view
        // In this case, using it is not necessary - but I am putting it here to remind
        // developers to look at this Inflator
        templateView = PluginLayoutInflater.inflate(context,
                R.layout.main_layout, null);

        refresh = templateView.findViewById(R.id.refresh);
        pull = templateView.findViewById(R.id.pull);
        information = templateView.findViewById(R.id.information);
        spinner = templateView.findViewById(R.id.spinner);
        listView = templateView.findViewById(R.id.listview);


        refresh.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                windproviders.clear();
                Collection<DatasetProvider> providers = DatasetProviderManager.getInstance().getDatasetProviders();
                for (DatasetProvider provider: providers) {
                    if (provider.getPackageName().equals("com.atakmap.android.windprovider.plugin")) {
                        windproviders.add(provider);
                    }

                }
                ProviderAdapter spinnerAdapter = new ProviderAdapter(getMapView().getContext(), windproviders);
                getMapView().post(new Runnable() {
                    @Override
                    public void run() {
                        spinner.setAdapter(spinnerAdapter);
                    }
                });
            }
        });

        pull.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                information.setText("");
                DatasetProvider provider = (DatasetProvider) spinner.getSelectedItem();
                if (provider == null)
                    return;

                List<DatasetDefinition> definitions = provider.getDefinitions();
                for (DatasetDefinition definition : definitions) {
                    Log.d(TAG, definition.toString());
                }
                List<DatasetQueryParam> datasetQueryParams = new ArrayList<>();
                datasetQueryParams.add(new DatasetQueryParam("requested_location",
                        DatasetQueryParam.Operation.EQUALS, active = getMapView().getCenterPoint().get()));
                provider.subscribe(WindConsumerDropDownReceiver.class.getSimpleName(),
                        datasetQueryParams, callback);
            }
        });



    }

    private final DatasetProviderCallback callback = new DatasetProviderCallback() {
        @Override
        public void onData(String s, DatasetProvider provider, List<DatasetQueryParam> list, List<Dataset> datasets,
                           Status status, String msg) {
            if (status == Status.COMPLETE)
                provider.unsubscribe(this);
            for (Dataset dataset : datasets) {
                Log.d(TAG, dataset.get("altitude", -1) + " " +
                        dataset.get("direction", -1) + " " +
                        dataset.get("speed", -1));
            }
            getMapView().post(new Runnable() {
                @Override
                public void run() {
                    CoordinateEntryCapability cec = CoordinateEntryCapability.getInstance(getMapView().getContext());
                    if (FileSystemUtils.isEmpty(msg)) {
                        information.setText(status.name() + ":" +
                                cec.format(cec.findId("MGRS"), GeoPointMetaData.wrap(active)));
                    } else {
                        information.setText(status.name() + ":" + msg);
                    }
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
                result = LayoutInflater.from(pluginContext).inflate(R.layout.altitude_direction_speed, parent, false);
            } else {
                result = convertView;
            }
            TextView alt = result.findViewById(R.id.altitude);
            TextView dir = result.findViewById(R.id.direction);
            TextView spd = result.findViewById(R.id.speed);
            Dataset dp = datasets.get(position);

            if (dp.contains("direction"))
                dir.setText(""+dp.get("direction", -1));
            else
                dir.setText("");

            if (dp.contains("speed"))
                spd.setText(""+dp.get("speed", -1));
            else
                spd.setText("");

            if (dp.contains("altitude"))
                alt.setText(""+dp.get("altitude", -1));
            else
                alt.setText("");
            return result;
        }
    }

}
