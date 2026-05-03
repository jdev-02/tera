
package com.atakmap.android.sensortest;

import android.content.Context;
import android.content.Intent;
import android.hardware.Sensor;
import android.hardware.SensorAdditionalInfo;
import android.hardware.SensorEvent;
import android.hardware.SensorEventCallback;
import android.hardware.SensorManager;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.sensortest.plugin.R;
import com.atakmap.android.dropdown.DropDown.OnStateListener;
import com.atakmap.android.dropdown.DropDownReceiver;

import com.atakmap.coremap.log.Log;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class SensorTestDropDownReceiver extends DropDownReceiver implements
        OnStateListener {

    public static final String TAG = SensorTestDropDownReceiver.class
            .getSimpleName();

    public static final String SHOW_PLUGIN = "com.atakmap.android.sensortest.SHOW_PLUGIN";
    private final View templateView;
    private final Context pluginContext;
    private final SensorManager sensorManager;
    private final ArrayList<SensorEventListener> sensorListeners = new ArrayList<>();


    /**************************** CONSTRUCTOR *****************************/

    public SensorTestDropDownReceiver(final MapView mapView,
                                      final Context context) {
        super(mapView);
        this.pluginContext = context;

        // Remember to use the PluginLayoutInflator if you are actually inflating a custom view
        // In this case, using it is not necessary - but I am putting it here to remind
        // developers to look at this Inflator
        templateView = PluginLayoutInflater.inflate(context, R.layout.main_layout, null);

        sensorManager = (SensorManager)context.getSystemService(Context.SENSOR_SERVICE);
        final List<Sensor> sensors = sensorManager.getSensorList(Sensor.TYPE_ALL);

        for (Sensor s: sensors) {
            Log.d(TAG, "register sensor: " + s.getName() + " " + s.getVendor());
            SensorEventListener sec = new SensorEventListener(s);
            sensorManager.registerListener(sec, s, SensorManager.SENSOR_DELAY_NORMAL);
            sensorListeners.add(sec);
        }
        SensorAdapter adapter = new SensorAdapter(mapView.getContext(), sensorListeners);
        ListView listView = (ListView) templateView.findViewById(R.id.sensors);
        listView.setAdapter(adapter);


    }

    /**************************** PUBLIC METHODS *****************************/

    public void disposeImpl() {
        for (SensorEventListener sec: sensorListeners) {
            sensorManager.unregisterListener(sec);
        }
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
                    HALF_HEIGHT, false);
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


    public class SensorAdapter extends ArrayAdapter<SensorEventListener> {
        public SensorAdapter(Context context, ArrayList<SensorEventListener> sensors) {
            super(context, 0, sensors);

        }

        @Override
        public View getView(int position, View convertView, ViewGroup parent) {
            SensorEventListener sensor = getItem(position);
            if (convertView == null) {
                convertView = LayoutInflater.from(pluginContext).inflate(R.layout.sensor_display, parent, false);
            }
            TextView sensorName = (TextView) convertView.findViewById(R.id.sensorName);
            TextView sensorAccuracy = (TextView) convertView.findViewById(R.id.sensorAccuracy);
            TextView sensorValue = (TextView) convertView.findViewById(R.id.sensorValue);
            TextView sensorAdditionalInfo = (TextView) convertView.findViewById(R.id.sensorAdditionalInfo);

            // Populate the data into the template view using the data object
            sensor.setView(sensorName, sensorAccuracy, sensorValue, sensorAdditionalInfo);
            return convertView;

        }

    }


    class SensorEventListener extends SensorEventCallback {
        private final Sensor s;
        private TextView sensorName;
        private TextView sensorAccuracy;
        private TextView sensorValue;
        private TextView sensorAdditionalInformation;

        public SensorEventListener(Sensor s) {
            this.s = s;
        }

        public void setView(final TextView sensorName,
                            final TextView sensorAccuracy,
                            final TextView sensorValue,
                            final TextView sensorAdditionalInformation) {
            this.sensorName = sensorName;
            this.sensorAccuracy =sensorAccuracy;
            this.sensorValue = sensorValue;
            this.sensorAdditionalInformation = sensorAdditionalInformation;
            sensorName.setText(s.getName());
        }

        @Override
        public void onSensorChanged(final SensorEvent event) {
            super.onSensorChanged(event);
            templateView.post(new Runnable() {
                @Override
                public void run() {
                    if (sensorValue != null)
                        sensorValue.setText(Arrays.toString(event.values));
                }
            });
        }

        @Override
        public void onAccuracyChanged(Sensor sensor, int accuracy) {
            super.onAccuracyChanged(sensor, accuracy);
            final String accString;

            if (accuracy == SensorManager.SENSOR_STATUS_ACCURACY_LOW)
                accString = "LOW";
            else if (accuracy == SensorManager.SENSOR_STATUS_ACCURACY_MEDIUM)
                accString = "MEDIUM";
            else if (accuracy == SensorManager.SENSOR_STATUS_ACCURACY_HIGH)
                accString = "HIGH";
            else {
                accString = "UNK: " + accuracy;
            }

            templateView.post(new Runnable() {
                    @Override
                    public void run() {
                        if (sensorAccuracy != null)
                            sensorAccuracy.setText("Accuracy: " + accString);
                    }
                });
        }

        @Override
        public void onFlushCompleted(Sensor sensor) {
            super.onFlushCompleted(sensor);
        }

        @Override
        public void onSensorAdditionalInfo(SensorAdditionalInfo info) {
            super.onSensorAdditionalInfo(info);
        }
    }
}
