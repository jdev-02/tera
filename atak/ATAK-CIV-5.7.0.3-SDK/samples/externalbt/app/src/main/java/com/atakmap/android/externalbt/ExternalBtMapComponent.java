
package com.atakmap.android.externalbt;

import android.bluetooth.BluetoothDevice;
import android.content.Context;

import com.atakmap.android.location.MetaDataHolderLocationProvider;
import com.atakmap.android.location.framework.LocationManager;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.maps.conversion.EGM96;
import com.atakmap.coremap.maps.coords.GeoPoint;
import android.annotation.SuppressLint;

import com.atakmap.coremap.maps.coords.GeoPoint.AltitudeReference;
import com.atakmap.android.maps.Marker;
import com.atakmap.android.maps.MetaDataHolder2;
import com.atakmap.android.dropdown.DropDownMapComponent;
import com.atakmap.coremap.log.Log;
import android.content.Intent;

import java.util.Date;
import java.util.HashMap;
import java.util.Map;

import com.atakmap.coremap.conversions.ConversionFactors;

import com.atakmap.android.bluetooth.BluetoothConnection;
import com.atakmap.android.bluetooth.BluetoothManager;
import com.atakmap.android.bluetooth.BluetoothManager.BluetoothReaderFactory;
import com.atakmap.android.bluetooth.BluetoothReader;
import com.atakmap.android.bluetooth.BluetoothCotManager;
import com.atakmap.android.bluetooth.BluetoothASCIIClientConnection;

import com.atakmap.android.lrf.LocalRangeFinderInput;

import gnu.nmea.Packet;
import gnu.nmea.PacketGGA;
import gnu.nmea.PacketRMC;
import gnu.nmea.SentenceHandler;
import gnu.nmea.Geocoordinate;

import com.atakmap.android.externalbt.R;
import android.os.SystemClock;
import com.atakmap.coremap.maps.time.CoordinatedTime;
import com.atakmap.android.ipc.AtakBroadcast;
import android.os.Bundle;

public class ExternalBtMapComponent extends DropDownMapComponent {

    public static final String TAG = "ExternalBtMapComponent";

    public Context pluginContext;
    public MapView view;

    private PacketGGA _gga;
    private PacketRMC _rmc;

    private MetaDataHolderLocationProvider locationProvider =
            new MetaDataHolderLocationProvider("TP360 Reader",
                    "Demonstrates the ability to read from a classic Bluetooth TP360",
                    "external-bt-example-tp360");

    Map<String, Packet> state = new HashMap<>();

    public void onCreate(final Context context, Intent intent,
            final MapView view) {
        context.setTheme(R.style.ATAKPluginTheme);
        if (pluginContext == null) {
            Log.d(TAG, "externalbt loaded");
            super.onCreate(context, intent, view);
            pluginContext = context;
            this.view = view;
            BluetoothManager.getInstance().addExternalBluetoothReader(
                    new ExternalBtFactory());
        }
        LocationManager.getInstance().registerProvider(locationProvider, LocationManager.LOWEST_PRIORITY);

    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        super.onDestroyImpl(context, view);
        LocationManager.getInstance().unregisterProvider(locationProvider.getUniqueIdentifier());
    }

    /**
     * Factory implementation for creating readers for a specific device.
     */
    @SuppressLint({"MissingPermission"})
    private class ExternalBtFactory implements BluetoothReaderFactory {
        public boolean matches(BluetoothDevice device) {
            Log.d(TAG,
                    "searching for external bluetooth device for: " + device);
            if (device.getName().startsWith("TP360")) {
                return true;
            }
            return false;
        }

        public BluetoothReader create(BluetoothDevice device) {
            return new ExternalBluetoothReader(device);
        }
    }

    /**
     * Implementation of the reader.   Meat and Potatoes of the implementation.
     */
    private class ExternalBluetoothReader extends BluetoothReader {
        public ExternalBluetoothReader(BluetoothDevice device) {
            super(device);
        }

        @Override
        public void onRead(final byte[] data) {
            String ascii = new String(data);
            Log.d(TAG, "just print out the line: " + ascii);
            // parse packet
            Packet packet = null;
            try {
                packet = SentenceHandler.makePacket(ascii, false);
            } catch (Exception e) {
                // sentence handler throws an exception if it does not like the string
            }
            if (packet == null) {
                fireLRFUpdate(ascii);
            } else {
                MetaDataHolder2 mdh = MetaDataHolderLocationProvider.nmeaToMetadataHolder(
                        ascii, state, "TP360", -1, locationProvider.getUniqueIdentifier());

                // if needed I can clean up the mdh that was produced

                if (mdh != null) {
                    // call into the generic location provider that was instantiated for this device
                    locationProvider.update(mdh);
                }
            }

        }

        /**
         * Reuse existing classes.
         */
        @Override
        protected BluetoothConnection onInstantiateConnection(
                BluetoothDevice device) {
            return new BluetoothASCIIClientConnection(device,
                    BluetoothConnection.MY_UUID_INSECURE);
        }

        /**
         * Reuse existing classes.
         */
        @SuppressLint({"MissingPermission"})
        @Override
        public BluetoothCotManager getCotManager(MapView mapView) {
            BluetoothDevice device = connection.getDevice();
            return new BluetoothCotManager(this, mapView,
                    device.getName().replace(" ", "").trim() + "."
                            + device.getAddress(),
                    device.getName());
        }
    }

    private void fireLRFUpdate(String line) {
        Log.d(TAG, "processed line: " + line);

        if (!line.startsWith("$PLTIT,HV")) {
            return;
        }

        String[] data = line.split(",");
        String distanceString = data[2];
        String distanceUnits = data[3];
        String azimuthString = data[4];
        String inclinationString = data[6];

        double distance = getDistance(distanceString, distanceUnits);
        double azimuth = getAngle(azimuthString);
        double inclination = getAngle(inclinationString);

        try {
            Log.d(TAG, "received: " + line + "   values are  d: "
                    + distance + " " + "a: " + azimuth + "i: " + inclination);

            if (!Double.isNaN(distance) && !Double.isNaN(azimuth)
                    && !Double.isNaN(inclination)) {
                LocalRangeFinderInput.getInstance().onRangeFinderInfo(
                        "externalbt-lrf.55",
                        distance, azimuth, inclination);
            } else {
                Log.d(TAG, "error reading line: " + line
                        + "   values are  d: " + distance + " " + "a: "
                        + azimuth + "i: " + inclination);
            }
        } catch (Exception e) {
            Log.d(TAG, "error reading line: " + line, e);
        }
    }

    private double getDistance(String valString, String units) {
        try {
            double val = Double.parseDouble(valString);
            if (units.equals("F")) {
                val /= ConversionFactors.METERS_TO_FEET;
            } else if (units.equals("Y")) {
                val /= ConversionFactors.METERS_TO_YARDS;
            }
            return val;
        } catch (Exception e) {
            return Double.NaN;
        }

    }

    private double getAngle(String valString) {
        try {
            return Double.parseDouble(valString);
        } catch (Exception e) {
            return Double.NaN;
        }
    }

}
