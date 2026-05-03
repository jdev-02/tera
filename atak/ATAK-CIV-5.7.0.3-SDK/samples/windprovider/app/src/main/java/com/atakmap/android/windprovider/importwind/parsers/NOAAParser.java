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
import com.atakmap.coremap.conversions.ConversionFactors;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.Locale;
import java.util.Scanner;
import java.util.TimeZone;

/**
 * Parse Mark Schulze wind data CSV file over HTTP Tab delimited .txt via SD card (from
 * markschulze.net "Download File" button)
 */
public class NOAAParser extends WindParser {
    /* the following variables are what markschulze.net uses as
     * boundaries for CONUS */
    private static final double CONUS_LAT_UPPER_BOUND = 53.49178;
    private static final double CONUS_LAT_LOWER_BOUND = 2.227524;
    private static final double CONUS_LON_UPPER_BOUND = -140.4815;
    private static final double CONUS_LON_LOWER_BOUND = -67.51849;

    private static final int INVALID_VALUE = 99999;

    private static final String MANDATORY_LEVEL_LINE_NUM = "4";
    private static final String SIGNIFICANT_LEVEL_LINE_NUM = "5";
    private static final String WIND_LEVEL_LINE_NUM = "6";
    private static final String MAX_WIND_LEVEL_LINE_NUM = "8";
    private static final String SURFACE_LEVEL_LINE_NUM = "9";

    //columns are 0 indexed
    private static final int HEIGHT_COLUMN = 2;
    private static final int WIND_DIR_COLUMN = 5;
    private static final int WIND_SPD_COLUMN = 6;

    private static final String TAG = "NOAAParser";


    public NOAAParser(Context context) {
        super(context, "NOAA");
    }

    @Override
    public String url(final GeoPoint location, final int hourOffset) {
        double lat = location.getLatitude();
        double lon = location.getLongitude();

        String base_url = "https://rucsoundings.noaa.gov/get_soundings.cgi";

        if (!base_url.contains("://"))
            base_url = "https://" + base_url;
        //format the rest of the url with the query params


        String hourOffsetParams = "&latest=latest&start=latest";
        String startEndSecs = "";
        if (hourOffset > 0) {
            TimeZone timeZone = TimeZone.getTimeZone("UTC");
            Calendar calendar = Calendar.getInstance(timeZone);
            calendar.setTimeInMillis(System.currentTimeMillis() + ((long) hourOffset * 60 * 60 * 1000));

            SimpleDateFormat sdf =
                    new SimpleDateFormat("MMM", Locale.US);
            sdf.setTimeZone(timeZone);
            String month = sdf.format(calendar.getTime());
            long secs = calendar.getTimeInMillis() / 1000;
            hourOffsetParams = "&start_year=" + calendar.get(Calendar.YEAR) +
                    "&start_month_name=" + month +
                    "&start_mday=" + calendar.get(Calendar.DAY_OF_MONTH) +
                    "&start_hour=" + calendar.get(Calendar.HOUR_OF_DAY) +
                    "&start_min=" + calendar.get(Calendar.MINUTE);

            startEndSecs = "&startSecs=" + secs +
                    "&endSecs=" + (secs + 3600);

        }

        if ((lat > CONUS_LAT_LOWER_BOUND) && (lat < CONUS_LAT_UPPER_BOUND) &&
                (lon > CONUS_LON_UPPER_BOUND)
                && (lon < CONUS_LON_LOWER_BOUND)) {
            //CONUS winds

            return base_url
                    + "?data_source=Op40" + hourOffsetParams + "&n_hrs=1.0&fcst_len=shortest&"
                    + "airport=" + location.getLatitude() + ",%20" + location.getLongitude()
                    + "&text=Ascii+text+(GSL+format)&hydrometeors=false" + startEndSecs;

        } else {
            //OCONUS winds

            return base_url
                    + "?data_source=GFS" + hourOffsetParams + "&n_hrs=1.0&fcst_len=shortest&"
                    + "airport=" + location.getLatitude() + ",%20" + location.getLongitude()
                    + "&text=Ascii+text+(GSL+format)&hydrometeors=false" + startEndSecs;
        }

    }

    /**
     * @param data - the GSD Sounding Format response from the wind data query
     * @return - the table of wind data
     */
    public List<WindInfo> parseResponseWinds(String data) throws Exception {
        if (FileSystemUtils.isEmpty(data)) {
            throw new Exception("Unable to parse empty data");
        }

        ArrayList<WindInfo> windInfo = new ArrayList<>();

        String delims = "[ ]+";
        Scanner scanner = new Scanner(data);

        int groundElevMeters = 0;
        //1 indexed, to match notepad++
        int lineNum = 0;
        while (scanner.hasNextLine()) {

            try {
                String line = scanner.nextLine().trim();
                lineNum++;
                // process the line

                //first 3 lines are just headers, ignore for now
                if (lineNum <= 3) {
                    continue;
                }

                String[] tokens = line.split(delims);
                if (tokens.length < 7) {
                    continue;
                }

                if (tokens[0].equals(SURFACE_LEVEL_LINE_NUM)) {
                    //set the surface level
                    groundElevMeters = Integer.parseInt(tokens[HEIGHT_COLUMN]);
                    int surfWindDir = Integer.parseInt(tokens[WIND_DIR_COLUMN]);
                    int surfWindSpd = Integer.parseInt(tokens[WIND_SPD_COLUMN]);
                    if (surfWindDir != INVALID_VALUE && surfWindSpd != INVALID_VALUE) {
                        windInfo.add(new WindInfo(groundElevMeters, surfWindDir, surfWindSpd));
                    }
                }

                if (tokens[0].equals(MANDATORY_LEVEL_LINE_NUM) ||
                        tokens[0].equals(SIGNIFICANT_LEVEL_LINE_NUM) ||
                        tokens[0].equals(WIND_LEVEL_LINE_NUM) ||
                        tokens[0].equals(MAX_WIND_LEVEL_LINE_NUM)) {
                    int windAltMeters = Integer.parseInt(tokens[HEIGHT_COLUMN]);
                    if (windAltMeters == INVALID_VALUE) {
                        continue;
                    }
                    int altAGLInMeters = windAltMeters - groundElevMeters;
                    int altAGLinFeet = (int) Math.round(altAGLInMeters * ConversionFactors.METERS_TO_FEET);

                    int windDir = Integer.parseInt(tokens[WIND_DIR_COLUMN]);
                    int windSpd = Integer.parseInt(tokens[WIND_SPD_COLUMN]);

                    if (windDir != INVALID_VALUE && windSpd != INVALID_VALUE) {
                        windInfo.add(new WindInfo(altAGLinFeet, windDir, windSpd));
                    }
                }

            } catch (Exception e) {
                Log.e(TAG, "error", e);
            }
        }
        scanner.close();

        return windInfo;
    }

    @Override
    public List<WindInfo> parse(InputStream is) throws WindParseException {
        try {
            String data = FileSystemUtils.copyStreamToString(is, true, FileSystemUtils.UTF8_CHARSET);
            return parseResponseWinds(data);
        } catch (Exception e) {
            throw new WindParseException("error parsing NOAA", e);
        }
    }

    @Override
    public boolean supportTimeOffset() {
        return true;
    }

}
