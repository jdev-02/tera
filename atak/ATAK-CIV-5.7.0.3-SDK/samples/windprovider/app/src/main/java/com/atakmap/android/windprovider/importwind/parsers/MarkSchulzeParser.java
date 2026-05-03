/*
 *  Copyright 2023 PAR Government Systems
 *
 *  Unlimited Rights:
 *  PAR Government retains ownership rights to this software.  The Government has Unlimited Rights
 *  to use, modify, reproduce, release, perform, display, or disclose this
 *  software as identified in the purchase order contract. Any
 *  reproduction of computer software or portions thereof marked with this
 *  legend must also reproduce the markings. Any person who has been provided
 *  access to this software must be aware of the above restrictions.
 */

package com.atakmap.android.windprovider.importwind.parsers;

import android.content.Context;

import com.atakmap.android.windprovider.importwind.WindInfo;
import com.atakmap.android.windprovider.importwind.WindParseException;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;


/**
 * Parse Mark Schulze wind data CSV file over HTTP Tab delimited .txt via SD card (from
 * markschulze.net "Download File" button)
 */
public class MarkSchulzeParser extends WindParser {
    /* the following variables are what markschulze.net uses as
     * boundaries for CONUS */
    private static final double CONUS_LAT_UPPER_BOUND = 53.49178;
    private static final double CONUS_LAT_LOWER_BOUND = 2.227524;
    private static final double CONUS_LON_UPPER_BOUND = -140.4815;
    private static final double CONUS_LON_LOWER_BOUND = -67.51849;

    private static final String TAG = "MarkSchulzeParser";

    public MarkSchulzeParser(Context context) {
        super(context, "MarkSchulze.net");
    }

    MarkSchulzeParser(Context context, String name) {
        super(context,name);
    }


    @Override
    public String url(final GeoPoint location, final int hourOffset) {
        double lat = location.getLatitude();
        double lon = location.getLongitude();

        String base_url = prefs.getString("markschulze_base_url", null);
        if (FileSystemUtils.isEmpty(base_url))
            base_url = "markschulze.net";

        if (!base_url.contains("://"))
            base_url = "https://" + base_url;

        if ((lat > CONUS_LAT_LOWER_BOUND) && (lat < CONUS_LAT_UPPER_BOUND) &&
                (lon > CONUS_LON_UPPER_BOUND)
                && (lon < CONUS_LON_LOWER_BOUND)) {
            //CONUS winds
            return base_url +
                    "/winds/winds.php"
                    + "?lat="
                    + location.getLatitude() + "&lon="
                    + location.getLongitude()
                    + "&hourOffset="
                    + hourOffset
                    + "&referrer=TAK";
        } else {
            //OCONUS winds
            return base_url +
                    "/winds/winds.php"
                    + "?lat="
                    + location.getLatitude() + "&lon="
                    + location.getLongitude()
                    + "&hourOffset="
                    + hourOffset
                    + "&referrer=TAK";
        }

    }

    public double getQNH(String data) {
        if (data == null || FileSystemUtils.isEmpty(data)) {
            return 0d;
        }

        try {
            JSONObject weatherObj = new JSONObject(data);
            return weatherObj.getDouble("QNH");
        } catch (JSONException e) {
            Log.e(TAG, "error", e);
        }

        return 0d;
    }

    /**
     * Utilize the JSON classes to parse the wind data from the given json from markschulze
     *
     * @param data - the json response from the wind data query
     * @return - the table of wind data
     * @throws Exception - exceptions can be thrown if data is not valid json
     */
    public List<WindInfo> parseJsonWinds(String data)
            throws Exception {
        if (FileSystemUtils.isEmpty(data)) {
            throw new Exception("Unable to parse empty data");
        }

        try {
            JSONObject weatherObj = new JSONObject(data);

            JSONArray altArr = weatherObj.getJSONArray("altFt");
            JSONObject directionObj = weatherObj.getJSONObject("direction");
            JSONObject speedObj = weatherObj.getJSONObject("speed");

            List<WindInfo> windInfo = new ArrayList<>(altArr.length());

            for (int i = 0; i < altArr.length(); i++) {
                int altitude = (int) altArr.get(i);
                int direction = directionObj.getInt(String.valueOf(altitude));
                int speed = speedObj.getInt(String.valueOf(altitude));
                windInfo.add(new WindInfo(altitude, direction, speed));
            }
            return windInfo;
        } catch (JSONException e) {
            Log.e(TAG, "error", e);
        }

        return null;
    }

    @Override
    public List<WindInfo> parse(InputStream is) throws WindParseException {
        try {
            String data = FileSystemUtils.copyStreamToString(is, true, FileSystemUtils.UTF8_CHARSET);
            return parseJsonWinds(data);
        } catch (Exception e) {
            throw new WindParseException("error parsing mark schulze", e);
        }
    }

    @Override
    public boolean supportTimeOffset() {
        return true;
    }

}
