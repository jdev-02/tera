package com.atakmap.android.windprovider.importwind.parsers;

import android.content.Context;

import com.atakmap.android.windprovider.importwind.WindInfo;
import com.atakmap.android.windprovider.importwind.WindParseException;
import com.atakmap.coremap.conversions.ConversionFactors;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.conversion.EGM96;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.util.zip.IoUtils;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

/**
 * Parse CSV file wind from the Meteodrone
 * e.g. lin
 * Latitude [deg];
 * Longitude [deg];
 * Altitude AMSL [ft];
 * Temperature [dF];
 * Dew Point [dF];
 * Relative Humidity [perc];
 * Air Pressure [hPa];
 * Wind Speed [kts];
 * Wind direction [deg];
 * Wind gusts [kts];
 * ct2 [log_{10}K^2m^{-2/3}];
 * cn2 [log_{10}m^{-2/3}];
 * Speed of Sound [kts];
 * Sound Damping [dB/100m];
 * Refractivity [N];
 * Refractivity Gradient [dN/km];
 * Modified Refractivity [M];
 * Modified Refractivity Gradient [dM/km];
 * Latent Heat Flux [W/m^2];
 * Sensible Heat Flux [W/m^2]
 * 24.0604002;
 * -68.2211175;
 * 2913.8;74.99;
 * 62.40;65.03;
 * 921.6;
 * 19.3;
 * 243.9;
 * 20.2;
 * 0.0;
 * 0.0;
 * 673.2;
 * 7.3;
 * 83.9;
 * -10.8;
 * 223.1;
 * 146.0;
 * 2.8;
 * 7.2
 */
public class MeteodroneParser extends WindParser {

    private static final String TAG = "MeteodroneParser";

    public static final String MDCSV = ".mdcsv";
    public static final String CSV = ".csv";

    private static final String[] headerKeywords = new String[]{
            "Aircraft", "Latitude"
    };

    private final static String delimiter = ";";

    private double groundElevationMSL = 0;

    public MeteodroneParser(Context context) {
        super(context, "Meteodrone");
    }

    /**
     * Set the elevation of the ground in case the file provides altitude
     * in MSL it can be converted to AGL.
     *
     * @param groundElevation - the geoPoint of the DIP, with valid Altitude value
     */
    public void setGroundElevation(GeoPoint groundElevation) {
        groundElevationMSL = EGM96.getMSL(groundElevation);
    }

    @Override
    public String url(GeoPoint location, int hourOffset) {
        // Note location/time offset not used just return
        // URL stored in XML "data" attribute
        return "";
    }



    @Override
    public boolean supportTimeOffset() {
        return false;
    }


    public List<WindInfo> parse(InputStream input)  throws WindParseException {
        List<WindInfo> windInfo = new ArrayList<>();

        try {
            try (InputStreamReader isr = new InputStreamReader(input, FileSystemUtils.UTF8_CHARSET);
                 BufferedReader reader = new BufferedReader(isr)) {

                String line = reader.readLine();

                // for each row, pull out and check the values
                // if the values are valid, save them, otherwise skip that altitude entry
                int count = 0;
                while (line != null) {
                    if (line.trim().length() == 0) {
                        line = reader.readLine();
                        continue;
                    }

                    if (isTitleLine(line)) {
                        Log.d(TAG, "Skipping title line: " + line);
                        line = reader.readLine();
                        continue;
                    }

                    //Log.d(TAG, "parsing line " + (++count) + ": " + line);

                    // tokenize the line and return the altitude, direction and speed in an array
                    String[] toks = decodeLine(line);
                    if (toks == null || toks.length < 3) {
                        Log.d(TAG, "Skipping invalid line: " + line);
                        line = reader.readLine();
                        continue;
                    }

                    try {
                        int altitude = (int) Math.round(Double.parseDouble(toks[0]));
                        //subtract the MSL elevation of the DIP to get the AGL value
                        altitude -= (groundElevationMSL * ConversionFactors.METERS_TO_FEET);

                        // get the double values for direction and velocity and round them
                        double dubDir = Double.parseDouble(toks[1]);
                        int intDir = (int) Math.round(dubDir);

                        double dubVel = Double.parseDouble(toks[2]);
                        int intVel = (int) Math.round(dubVel);

                        count++;
                        Log.d(TAG, "Parsed line "
                                + count + ": alt=" + toks[0]
                                + ", adjust alt=" + altitude
                                + ", " + intDir
                                + ", " + intVel
                        );

                        windInfo.add(new WindInfo(altitude, intDir, intVel));
                    } catch (Exception e) {
                        Log.v(TAG, "invalid value in text file, skipping entry.");
                    }

                    // read the next line
                    line = reader.readLine();
                }
            }
        } catch (Exception e) {
            throw new WindParseException("error occurred during parsing", e);
        }


        return windInfo;
    }

    /**
     * pulls the altitude, direction and speed from the line at positions 2, 8, 7
     *
     * @param line - the comma separated line to read
     * @return - a string array [altitude, heading, speed]
     */
    private String[] decodeLine(String line) {
        String[] splitString = line.split(delimiter);
        if (splitString.length < 9) {
            Log.d(TAG, "decodeLine skipping invalid: " + line);
            return null;
        }

        return new String[]{
                splitString[2],
                splitString[8],
                splitString[7]
        };
    }

    /**
     * Check if the given line is a header row
     *
     * @param line - the line to check for variable indices
     * @return - true if the line does contain the titles
     */
    private static boolean isTitleLine(String line) {
        for (String spd : headerKeywords) {
            if (line.contains(spd)) {
                return true;
            }
        }
        return false;
    }

    public static boolean isSupported(File file, String fileExt) {
        //read first couple lines, see if we can find required Meteodrone title line(s)
        if (!FileSystemUtils.isFile(file))
            return false;

        if (!fileExt.equalsIgnoreCase(MeteodroneParser.CSV) && !fileExt.equalsIgnoreCase(MeteodroneParser.MDCSV)) {
            return false;
        }

        InputStreamReader isr = null;
        BufferedReader reader = null;
        try {
            FileInputStream fos = new FileInputStream(file);

            isr = new InputStreamReader(fos, FileSystemUtils.UTF8_CHARSET);
            reader = new BufferedReader(isr);

            String line = reader.readLine();

            // for each row, pull out and check the values
            // if the values are valid, save them, otherwise skip that altitude entry
            int count = 0;
            boolean found1 = false;
            boolean found2 = false;
            while (line != null && (++count < 4)) {
                if (line.trim().length() == 0) {
                    Log.d(TAG, "Found empty line");
                    line = reader.readLine();
                    continue;
                }

                if (line.contains(headerKeywords[0])) {
                    Log.d(TAG, "Found title1 line: " + line);
                    found1 = true;
                }

                if (line.contains(headerKeywords[1])) {
                    Log.d(TAG, "Found title2 line: " + line);
                    found2 = true;
                }

                if (found1 && found2) {
                    Log.d(TAG, "Found all required headers");
                    return true;
                }

                // read the next line
                Log.d(TAG, "Reading next line: " + line);
                line = reader.readLine();
            }

        } catch (Exception e) {
            Log.v(TAG, "Failed to parse " + file.getAbsolutePath(), e);
        } finally {
            IoUtils.close(reader);
            IoUtils.close(isr);
        }

        Log.d(TAG, "Did not find all required headers");
        return false;
    }
}
