
package com.atakmap.android.selfmarkerdata;

import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.TextView;

import com.atakmap.android.contact.ContactLocationView;
import com.atakmap.android.cot.CotMapComponent;
import com.atakmap.android.cot.detail.CotDetailHandler;
import com.atakmap.android.cot.detail.CotDetailManager;
import com.atakmap.android.cotdetails.ExtendedInfoView;
import com.atakmap.android.ipc.AtakBroadcast;

import com.atakmap.android.maps.AbstractMapComponent;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;

import com.atakmap.android.maps.PointMapItem;
import com.atakmap.android.user.PlacePointTool;
import com.atakmap.comms.CommsMapComponent;
import com.atakmap.comms.ReportingRate;
import com.atakmap.coremap.cot.event.CotDetail;
import com.atakmap.coremap.cot.event.CotEvent;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.android.selfmarkerdata.plugin.R;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.time.CoordinatedTime;

import java.util.Timer;
import java.util.TimerTask;

/**
 * Problem Statement #1
 *
 * ACME Sensors has decided to contract to you to build a plugin that reads data from their sensor and push the information over the network both locally and through a TAK server.    The data will be the heart rate of the TAK user.   The data they provide is the maximum and average heart rate over a period of time.    At the end of the technical exchange, everyone has decided that the information can be captured using this format
 *
 * <health maxHeartRate="80" averageHeartRate="65" start="2019-01-23T21:22:55.3074679Z" stop="2019-01-23T21:23:55.3074679Z"/>
 *
 * The plugin you build will be able to insert this data into the current SA message being sent by the TAK device and allow for a receiver to visualize when they have your plugin.
 */

/**
 * Since this map component has no associated drop down, I can extend the abstract map component.
 */
public class SelfMarkerDataMapComponent extends AbstractMapComponent {

    private static final String TAG = "SelfMarkerDataMapComponent";

    private Context pluginContext;
    private MapView view;

    /**
     * Use the timer to generate some simulated data.
     */
    private Timer timer = new Timer();

    private CotDetailHandler healthDetail;

    private ContactLocationView.ExtendedSelfInfoFactory extendedselfinfo;

    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        context.setTheme(R.style.ATAKPluginTheme);
        pluginContext = context;
        this.view = view;

        //View v = PluginLayoutInflater.inflate(pluginContext, R.layout.main_layout, null)
        View v = LayoutInflater.from(pluginContext)
                .inflate(R.layout.main_layout, null);

        /**
         * Part 1 of the task is to generate simulated data.
         * Use the timer task to generate data that can be sent out to remote participants.
         */
        timer.scheduleAtFixedRate(timerTask, 0, 5000);

        /**
         * Part 2 of the task is to write the deserialization mechanism for the data.
         */
        CotDetailManager.getInstance()
                .registerHandler(healthDetail = new CotDetailHandler("health") {
                    private final String TAG = "HealthDetail";

                    @Override
                    public CommsMapComponent.ImportResult toItemMetadata(
                            MapItem item, CotEvent event, CotDetail detail) {
                        //Log.d(TAG, "detail received from [ " + item.getMetaString("callsign", null) + " - " + detail + " in:  " + event);

                        try {

                            String maxHeartRateString = detail
                                    .getAttribute("maxHeartRate");
                            String averageHeartRateString = detail
                                    .getAttribute("averageHeartRate");
                            String startString = detail.getAttribute("start");
                            String stopString = detail.getAttribute("stop");

                            if (FileSystemUtils.isEmpty(maxHeartRateString) ||
                                    FileSystemUtils
                                            .isEmpty(averageHeartRateString)
                                    ||
                                    FileSystemUtils.isEmpty(startString) ||
                                    FileSystemUtils.isEmpty(stopString)) {
                                return CommsMapComponent.ImportResult.FAILURE;
                            }

                            int maxHeartRate = Integer
                                    .parseInt(maxHeartRateString);
                            int averageHeartRate = Integer
                                    .parseInt(averageHeartRateString);

                            /**
                             * In order to make sure that other plugins don't clobber my metadata, lets try
                             * to uniquely scope the keys that are put into this key/value map that is part
                             * of my marker.
                             */
                            item.setMetaInteger(
                                    "SelfMarkerDataPlugin.maxHeartRate",
                                    maxHeartRate);
                            item.setMetaInteger(
                                    "SelfMarkerDataPlugin.averageHeartRate",
                                    averageHeartRate);
                            item.setMetaLong("SelfMarkerDataPlugin.start",
                                    CoordinatedTime.fromCot(startString).getMilliseconds());
                            item.setMetaLong("SelfMarkerDataPlugin.stop",
                                    CoordinatedTime.fromCot(stopString).getMilliseconds());
                            Log.d(TAG,
                                    "received["
                                            + item.getMetaString("callsign",
                                                    null)
                                            + "]: " +
                                            maxHeartRate + " "
                                            + averageHeartRate);

                        } catch (Exception e) {
                            Log.e(TAG,
                                    "silly error[ "
                                            + item.getMetaString("callsign",
                                                    null)
                                            +
                                            "]: " + detail,
                                    e);
                        }
                        return CommsMapComponent.ImportResult.SUCCESS;
                    }

                    @Override
                    public boolean toCotDetail(MapItem item, CotEvent event,
                            CotDetail root) {
                        // We do not need to worry about serializing the data here.   This is done directly
                        // with the timer.
                        //Log.d(TAG, "converting to cot detail from: " + item.getUID());
                        return true;
                    }
                });

        /**
         * Part 3 of the task is to visualize the data.   ContactLocationView allows for 3rd party
         * components register a mechanism to fill in custom views witihin the detail page.
         */
        ContactLocationView.register(
                extendedselfinfo = new ContactLocationView.ExtendedSelfInfoFactory() {
                    @Override
                    public ExtendedInfoView createView() {
                        return new ExtendedInfoView(view.getContext()) {
                            @Override
                            public void setMarker(PointMapItem m) {
                                //Log.d(TAG, "setting the marker: " + m.getMetaString("callsign", ""));
                                TextView tv = new TextView(view.getContext());
                                tv.setLayoutParams(new LayoutParams(
                                        LayoutParams.WRAP_CONTENT,
                                        LayoutParams.WRAP_CONTENT));
                                this.addView(tv);
                                int maxHeartRate = m.getMetaInteger(
                                        "SelfMarkerDataPlugin.maxHeartRate",
                                        -1);
                                int averageHeartRate = m.getMetaInteger(
                                        "SelfMarkerDataPlugin.averageHeartRate",
                                        -1);

                                long s = m.getMetaLong("SelfMarkerDataPlugin.start", -1);
                                CoordinatedTime start = null;
                                if (s != -1)
                                    start = new CoordinatedTime(s);

                                s = m.getMetaLong("SelfMarkerDataPlugin.start", -1);
                                CoordinatedTime stop = null;
                                if (s != -1)
                                    stop = new CoordinatedTime(s);

                                if (maxHeartRate == -1 || averageHeartRate == -1
                                        || start == null || stop == null)
                                    tv.setVisibility(View.GONE);
                                else {
                                    final int timeInSeconds = (int) Math
                                            .round((stop.getMilliseconds() -
                                                    start.getMilliseconds())
                                                    / 1000f);
                                    tv.setText("HeartRate\n\tavg: "
                                            + averageHeartRate + " max: " +
                                            maxHeartRate + "\n" +
                                            "\tover a period of "
                                            + timeInSeconds + " seconds");
                                    if (maxHeartRate > 90)
                                        tv.setTextColor(Color.RED);
                                    else
                                        tv.setTextColor(Color.GREEN);
                                }
                            }
                        };
                    }
                });

    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        timer.cancel();
        CotDetailManager.getInstance().unregisterHandler(healthDetail);
        ContactLocationView.unregister(extendedselfinfo);
    }

    /**
     * This timer task will add in data to the PPLI/SA message sent out to all remote participants
     * on both the local network and the remote network.
     */
    final TimerTask timerTask = new TimerTask() {
        CoordinatedTime lastTime = new CoordinatedTime();

        public void run() {

            /**
             * Create a CoTDetail which is the serialized form of the data we wish to send out to
             * other users.  A CoTDetail can contain as many attributes as you would like.  It can '
             * also contain nested CoTDetails.
             */
            // <health maxHeartRate="80" averageHeartRate="65" start="2019-01-23T21:22:55.3074679Z" stop="2019-01-23T21:23:55.3074679Z"/>
            CotDetail cd = new CotDetail("health");
            int maxHeartRate = (int) Math.round(Math.random() * 15 + 60);
            cd.setAttribute("maxHeartRate", Integer.toString(maxHeartRate));
            int averageHeartRate = (int) Math.round(Math.random() * 10 + 60);
            cd.setAttribute("averageHeartRate",
                    Integer.toString(averageHeartRate));
            CoordinatedTime currentTime = new CoordinatedTime();
            cd.setAttribute("start", CoordinatedTime.toCot(lastTime));
            cd.setAttribute("stop", CoordinatedTime.toCot(currentTime));

            lastTime = currentTime;

            /**
             * Your personal self marker does not receive it's own SA messages, so lets use the
             * deserialization mechanism to stuff the serialized data into the self marker.    I
             * could have copied and pasted the code if I would have liked.
             */
            if (healthDetail != null) {
                healthDetail.toItemMetadata(view.getSelfMarker(), null, cd);
            }

            /**
             * Put the serialized information into the PPLI/SA message.
             */
            CotMapComponent.getInstance()
                    .addAdditionalDetail(cd.getElementName(), cd);

            /**
             * Tell the system to report the PPLI/SA message out of cycle.    The user has already
             * configured the sending rate of the PPLI/SA but this allows a programmer to send it
             * more frequently.
             */
            AtakBroadcast.getInstance().sendBroadcast(
                    new Intent(ReportingRate.REPORT_LOCATION)
                            .putExtra("reason",
                                    "detail update for heart rate"));

        }
    };

}
