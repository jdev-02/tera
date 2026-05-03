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
import com.atakmap.coremap.locale.LocaleUtil;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.conversion.EGM96;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;

/**
 * Parse CSV file wind TODO document what sensor(s) produces these files
 */
public class WindFileParser extends WindParser {
    /* Variables */
    private static final String TAG = "WindFileParser";
    private static final String[] altitudeTitleArr = new String[]{"alt", "height"};
    private static final String[] headingTitleArr = new String[]{"heading", "hdg", "dir"};
    private static final String[] speedTitleArr = new String[]{"speed", "spd", "vel"};

    private boolean unitsInHeader = false;
    private AltitudeUnit altitudeUnit = AltitudeUnit.FEET;
    private double locationElevationMetersMSL = 0;
    // default indices for wind altitude, heading and speed
    private int altitudeIndex = 2;
    private int headingIndex = 3;
    private int speedIndex = 4;
    private String altitudeReference = "AGL";
    private String delimiter = ",";
    private WindSpeedUnit windSpeedUnit = WindSpeedUnit.KNOTS;

    /* Enums */
    private enum AltitudeUnit {
        FEET,
        METERS
    }

    private enum WindSpeedUnit {
        KNOTS,
        METERS_PER_SECOND

    }

    /**
     * Generic file parser
     * @param context the context to use
     * @param name the name of the parser
     */
    public WindFileParser(Context context, String name) {
        super(context, name);
    }


    @Override
    public boolean supportTimeOffset() {
        return false;
    }

    @Override
    public String url(GeoPoint location, int hourOffset) {
        // NOTE: location/time offset not used just return
        // URL stored in XML "data" attribute
        return "";
    }

    @Override
    public List<WindInfo> parse(InputStream input) throws WindParseException {
        List<WindInfo> windInfo = new ArrayList<>();
        try {
            try (InputStreamReader isr = new InputStreamReader(input, FileSystemUtils.UTF8_CHARSET);
                 BufferedReader reader = new BufferedReader(isr)) {
                //check the indices of the titles, if not found return an empty table
                if (!setArrayIndices(reader)) {
                    return windInfo;
                }

                String line = reader.readLine();
                //get units that are in the line after the header
                if (!unitsInHeader) {
                    if (line == null || line.trim().length() == 0) line = reader.readLine();
                    if (line != null && line.contains("(")) {
                        String[] unitList = decodeLine(line);
                        setAltitudeUnit(unitList[0]);
                        setSpeedUnit(unitList[2]);
                    }
                }

                // for each row, pull out and check the values
                // if the values are valid, save them, otherwise skip that altitude entry
                while (line != null) {
                    if (line.trim().length() == 0) {
                        line = reader.readLine();
                        continue;
                    }
                    // tokenize the line and return the altitude, direction and speed in an array
                    final String[] tokens = decodeLine(line);

                    try {
                        if (tokens[0].compareToIgnoreCase("sfc") == 0 ||
                                tokens[0].compareToIgnoreCase("surface") == 0) {
                            tokens[0] = "0";
                        }
                        int altitude = (int) Math.round(Double.parseDouble(tokens[0]));
                        if (altitudeUnit == AltitudeUnit.METERS) {
                            altitude *= ConversionFactors.METERS_TO_FEET;
                        }

                        //if the altitude in the file is in MSL, subtract the MSL elevation of
                        //the DIP to get the AGL value
                        if (altitudeReference.equals("MSL")) {
                            altitude -= (locationElevationMetersMSL * ConversionFactors.METERS_TO_FEET);
                        }

                        // get the double values for direction and velocity and round them
                        double dubDir = Double.parseDouble(tokens[1]);
                        int intDir = (int) Math.round(dubDir);

                        double dubVel = Double.parseDouble(tokens[2]);
                        if (windSpeedUnit == WindSpeedUnit.METERS_PER_SECOND) {
                            dubVel *= ConversionFactors.METERS_PER_S_TO_KNOTS;
                        }

                        int intVel = (int) Math.round(dubVel);

                        windInfo.add(new WindInfo(altitude, intDir, intVel));

                    } catch (Exception e) {
                        Log.v(TAG, "invalid value in text file, skipping entry.");
                    }

                    // read the next line
                    line = reader.readLine();
                }
            }
        } catch (Exception e) {
            throw new WindParseException("error parsing the file", e);
        }
        // close the reader and input stream

        return windInfo;
    }

    /**
     * Set the elevation of the DIP in case the file provides altitude
     * in MSL it can be converted to AGL.
     *
     * @param location - the geoPoint of the DIP, with valid Altitude value
     */
    public void setLocationElevation(GeoPoint location) {
        locationElevationMetersMSL = EGM96.getMSL(location);
    }

    /* Private Methods */

    /**
     * pulls the altitude, direction and speed from the line assuming that the altitude is the 3rd
     * value, direction is the 4th and speed is the 5th
     *
     * @param line - the comma separated line to read
     * @return - a string array [altitude, heading, speed]
     */
    private String[] decodeLine(String line) {
        String[] result = new String[]{"", "", ""};
        String[] splitString = line.split(delimiter);
        if (splitString.length > altitudeIndex) result[0] = splitString[altitudeIndex];
        if (splitString.length > headingIndex) result[1] = splitString[headingIndex];
        if (splitString.length > speedIndex) result[2] = splitString[speedIndex];
        return result;
    }

    /**
     * Given the title line that defines the indices, determine how
     * the values are delineated. This only works if the titles are
     * delineated the same way the values are.
     *
     * @param titleLine - the title line that defines the indices
     *                  of the altitude, wind speed and wind direction
     */
    private void findDelineation(String titleLine) {
        if (titleLine.contains(",")) {
            delimiter = ",";
        } else if (titleLine.contains("\t")) {
            delimiter = "\t";
        } else {
            delimiter = "\\s{2,}";
        }
    }

    /**
     * Check if the given line is the line that defines the indices of each variable.
     *
     * @param line - the line to check for variable indices
     * @return - true if the line does contain the titles
     */
    private boolean isTitleLine(String line) {
        boolean altHeader = false;
        for (String alt : altitudeTitleArr) {
            if (line.contains(alt)) {
                altHeader = true;
                break;
            }
        }
        if (!altHeader) {
            return false;
        }

        boolean hdgHeader = false;
        for (String hdg : headingTitleArr) {
            if (line.contains(hdg)) {
                hdgHeader = true;
                break;
            }
        }
        if (!hdgHeader) return false;

        boolean spdHeader = false;
        for (String spd : speedTitleArr) {
            if (line.contains(spd)) {
                spdHeader = true;
                break;
            }
        }
        return spdHeader;
    }

    /**
     * TODO
     *
     * @param entry TODO
     */
    private void setAltitudeUnit(String entry) {
        String unit = entry.substring(entry.indexOf('(') + 1, entry.indexOf(')'));
        unit = unit.toLowerCase(LocaleUtil.getCurrent());
        if (unit.contains("ft") || unit.contains("feet")) {
            altitudeUnit = AltitudeUnit.FEET;
        } else if (unit.compareTo("m") == 0 || unit.contains("m ")) {
            altitudeUnit = AltitudeUnit.METERS;
        }

        if (unit.contains("msl")) {
            altitudeReference = "MSL";
        }
    }

    /**
     * Sets the order and index for the altitude, heading, and wind speed in the given file.
     *
     * @param reader TODO
     */
    private boolean setArrayIndices(BufferedReader reader) {

        boolean altHeader = false;
        boolean hdgHeader = false;
        boolean spdHeader = false;

        try {
            String line = reader.readLine();

            while (line != null) {
                line = line.toLowerCase(LocaleUtil.getCurrent());
                if (!isTitleLine(line)) {
                    line = reader.readLine();
                    continue;
                }
                //after the title line is found, use the title line to determine the delimiter
                findDelineation(line);

                final String[] splitString = line.split(delimiter);
                for (int i = 0; i < splitString.length; i++) {
                    final String entry = splitString[i];

                    if (!altHeader) {
                        for (String alt : altitudeTitleArr) {
                            if (entry.contains(alt)) {
                                altHeader = true;
                                altitudeIndex = i;

                                if (entry.contains("(")) {
                                    unitsInHeader = true;
                                    setAltitudeUnit(entry);
                                }
                                break;
                            }
                        }
                    }
                    if (!hdgHeader) {
                        for (String hdg : headingTitleArr) {
                            if (entry.contains(hdg)) {
                                hdgHeader = true;
                                headingIndex = i;
                                break;
                            }
                        }
                    }

                    if (!spdHeader) {
                        for (String spd : speedTitleArr) {
                            if (entry.contains(spd)) {
                                spdHeader = true;
                                speedIndex = i;

                                if (entry.contains("(")) {
                                    unitsInHeader = true;
                                    setSpeedUnit(entry);
                                }

                                break;
                            }
                        }
                    }

                    if (altHeader && hdgHeader && spdHeader) {
                        return true;
                    }
                }
            }

        } catch (IOException e) {
            Log.e(TAG, "error", e);
        }

        return false;
    }

    /**
     * Set the wind speed unit type (knots, meters/second).
     *
     * @param entry The line to read.
     */
    private void setSpeedUnit(String entry) {
        String unit = entry.substring(entry.indexOf('(') + 1, entry.indexOf(')'));
        unit = unit.toLowerCase(LocaleUtil.getCurrent());
        if (unit.contains("kt") || unit.contains("knots")) {
            windSpeedUnit = WindSpeedUnit.KNOTS;
        } else if (unit.contains("m/s") || unit.contains("mps")) {
            windSpeedUnit = WindSpeedUnit.METERS_PER_SECOND;
        }
    }
}
