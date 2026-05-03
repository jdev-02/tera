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

import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.maps.coords.GeoPoint;

/**
 * Parse Mark Schulze wind data CSV file over HTTP Tab delimited .txt via SD card (from
 * markschulze.net "Download File" button)
 */
public class WindsAloftParser extends MarkSchulzeParser {
    /* the following variables are what markschulze.net uses as
     * boundaries for CONUS */
    private static final double CONUS_LAT_UPPER_BOUND = 53.49178;
    private static final double CONUS_LAT_LOWER_BOUND = 2.227524;
    private static final double CONUS_LON_UPPER_BOUND = -140.4815;
    private static final double CONUS_LON_LOWER_BOUND = -67.51849;

    private static final String TAG = "WindsAloftParser";

    public WindsAloftParser(Context context) {
        super(context, "WindsAloft.us");
    }

    @Override
    public String url(final GeoPoint location, final int hourOffset) {
        double lat = location.getLatitude();
        double lon = location.getLongitude();

        String base_url = prefs.getString("markschulze_base_url", null);
        if (FileSystemUtils.isEmpty(base_url))
            base_url = "windsaloft.us";

        if (!base_url.contains("://"))
            base_url = "https://" + base_url;

        if ((lat > CONUS_LAT_LOWER_BOUND) && (lat < CONUS_LAT_UPPER_BOUND) &&
                (lon > CONUS_LON_UPPER_BOUND)
                && (lon < CONUS_LON_LOWER_BOUND)) {
            //CONUS winds
            return base_url +
                    "/winds.php"
                    + "?lat="
                    + location.getLatitude() + "&lon="
                    + location.getLongitude()
                    + "&hourOffset="
                    + hourOffset
                    + "&referrer=TAK";
        } else {
            //OCONUS winds
            return base_url +
                    "/winds_gfs_1hr.php"
                    + "?lat="
                    + location.getLatitude() + "&lon="
                    + location.getLongitude()
                    + "&hourOffset="
                    + hourOffset
                    + "&referrer=TAK";
        }

    }
}
