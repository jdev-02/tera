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

package com.atakmap.android.windprovider.importwind;

import android.content.Context;

import com.atakmap.android.windprovider.importwind.parsers.CNSParser;
import com.atakmap.android.windprovider.importwind.parsers.MeteodroneParser;
import com.atakmap.android.windprovider.importwind.parsers.WindFileParser;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.io.File;
import java.io.FileInputStream;
import java.util.List;

/**
 * Class to import wind data from a file, parse it, and send
 * the data back to the WindData class
 */
class ImportWindFile {

    public static final String TAG = "ImportWindFile";

    private final Context con;





    ImportWindFile(Context ctx) {
        con = ctx;
    }

    /**
     * call a method to get the data from the file and then send the gathered info back to the
     * proper WindData instance.
     *
     * @param fileName the name of the file to get wind data from
     * @param groundPoint the ground point for use when determining AGL offset
     */
    public boolean parseFile(String fileName, GeoPoint groundPoint) {
        Log.i(TAG, "parsing wind, " + fileName);
        File windFile = new File(fileName);

        try {
            int lastPeriod = fileName.lastIndexOf('.');

            String fileExt = fileName.substring(lastPeriod);
            // <altitude, Pair<velocity, direction>
            List<WindInfo> windInfo;
            if (fileExt.equalsIgnoreCase(".cns")) {
                windInfo = new CNSParser(con).parse(new FileInputStream(windFile));
            } else if (MeteodroneParser.isSupported(windFile, fileExt)) {
                MeteodroneParser wfParser = new MeteodroneParser(con);
                wfParser.setGroundElevation(groundPoint);
                windInfo = wfParser.parse(new FileInputStream(windFile));
            } else {
                WindFileParser wfParser = new WindFileParser(con, "Generic Format");
                wfParser.setLocationElevation(groundPoint);
                windInfo = wfParser.parse(new FileInputStream(windFile));
            }

            return !windInfo.isEmpty();
        } catch (Exception e) {
            Log.e(TAG,
                    "Failed to import winds from file: "
                            + windFile.getAbsolutePath(),
                    e);
        }
        return false;
    }


}
