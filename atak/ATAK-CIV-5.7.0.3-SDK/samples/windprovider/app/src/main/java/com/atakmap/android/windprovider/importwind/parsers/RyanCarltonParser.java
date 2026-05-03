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

/**
 * Parse Mark Schulze wind data CSV file over HTTP Tab delimited .txt via SD card (from
 * markschulze.net "Download File" button)
 */
public class RyanCarltonParser extends WindParser {

    private static final String TAG = "RyanCarltonParser";

    public RyanCarltonParser(Context context) {
        super(context, "RyanCarlton.com");
    }

    @Override
    public String url(final GeoPoint location, final int hourOffset) {
        String base_url = "https://ryancarlton.com/api/forecast";

        if (!base_url.contains("://"))
            base_url = "https://" + base_url;
        //format the rest of the url with the query
        return base_url
                + "?gps=true&search={\"latitude\":\""
                + location.getLatitude() + "\",\"longitude\":\""
                + location.getLongitude()
                + "\"}&CAPE=false&altitude=AGL&distance=ft&inversions=false&maxAltitude=null&model=RAP&speed=KTs&temp=F&dewpoint=true&tempDewSpread=false&timezone=America/New_York&boop=false";
    }

    /**
     * @param data - the json response from the wind data query
     * @return Array of wind information with altitude, direction, speed.
     * @throws Exception - exceptions can be thrown if data is not valid json
     */
    public ArrayList<WindInfo> parseJsonWinds(String data)
            throws Exception {
        if (FileSystemUtils.isEmpty(data)) {
            throw new Exception("Unable to parse empty data");
        }

        try {
            JSONObject dataObj = new JSONObject(data);

            JSONArray forecastArr = dataObj.getJSONArray("forecast");
            JSONObject forecastObj = forecastArr.getJSONObject(0);

            JSONArray altArr = forecastObj.getJSONArray("height");
            JSONArray dirArr = forecastObj.getJSONArray("windDirection");
            JSONArray spdArr = forecastObj.getJSONArray("windSpeed");

            ArrayList<WindInfo> windInfo = new ArrayList<>();

            for (int i = 0; i < altArr.length(); i++) {
                int spd = Integer.parseInt(spdArr.get(i).toString());
                int dir = Integer.parseInt(dirArr.get(i).toString());
                int alt = Integer.parseInt(altArr.get(i).toString());
                windInfo.add(new WindInfo(alt, dir, spd));
            }

            return windInfo;
        } catch (JSONException e) {
            Log.e(TAG, "error", e);
        }

        return null;
    }


    @Override
    public ArrayList<WindInfo> parse(InputStream is)
            throws WindParseException {
        try {
            String data = FileSystemUtils.copyStreamToString(is, true, FileSystemUtils.UTF8_CHARSET);
            return parseJsonWinds(data);
        } catch (Exception e) {
            throw new WindParseException("error pasing ryan carlton", e);
        }
    }

    @Override
    public boolean supportTimeOffset() {
        return false;
    }

}
