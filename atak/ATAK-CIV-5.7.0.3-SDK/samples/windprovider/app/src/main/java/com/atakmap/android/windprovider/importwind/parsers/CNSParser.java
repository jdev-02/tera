
package com.atakmap.android.windprovider.importwind.parsers;

import android.content.Context;

import com.atakmap.android.windprovider.importwind.WindInfo;
import com.atakmap.android.windprovider.importwind.WindParseException;
import com.atakmap.coremap.conversions.ConversionFactors;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * Parse CNS wind file (e.g. LAP8000 Wind Profiler)
 */
public class CNSParser extends WindParser {

    public CNSParser(Context context) {
        super(context, "CNSParser");
    }

    @Override
    public String url(GeoPoint location, int hourOffset) {
        // Note location/time offset not used, just return
        // URL stored in XML "data" attribute
        return "";
    }

    /**
     * pull just the last wind data lines from the given string representation of a CNS file
     */
    @Override
    public List<WindInfo> parse(InputStream is) throws WindParseException {

        try {
            String data = FileSystemUtils.copyStreamToString(is, true, FileSystemUtils.UTF8_CHARSET);
            if (FileSystemUtils.isEmpty(data)) {
                throw new Exception("Unable to parse empty data");
            }

            List<String> windLines = new ArrayList<>();
            String line;

            ArrayList<String> reverseLines = new ArrayList<>();
            StringBuilder lineBuilder = new StringBuilder();
            int length = data.length();
            length--;
            for (int seek = length; seek >= 0; --seek) {
                char c = data.charAt(seek);
                lineBuilder.append(c);
                if (c == '\n') {
                    lineBuilder = lineBuilder.reverse();
                    line = lineBuilder.toString();
                    reverseLines.add(line);
                    lineBuilder = new StringBuilder();
                    if (line.contains("HT")) {
                        if (reverseLines.size() > 2) {
                            for (int i = reverseLines.size() - 2; i >= 2; i--)
                                windLines.add(reverseLines.get(i));
                            return getWindTable(windLines);
                        }
                    }
                }

            }
            return getWindTable(windLines);
        } catch (Exception e) {
            throw new WindParseException("error pasing cns data", e);
        }
    }

    @Override
    public boolean supportTimeOffset() {
        return false;
    }


    private List<WindInfo> getWindTable(List<String> winds) throws Exception {

        // pull from string
        if (winds == null || winds.size() < 1) {
            throw new Exception("Unable to parse empty winds");
        }

        List<WindInfo> windInfo = new ArrayList<>();

        // XXX- find a better way to tokenize the strings
        for (String line : winds) {
            double alt = Double.NaN;
            double speed = Double.NaN;
            double dir = Double.NaN;
            String[] splitString = line.split(" ");
            for (String tok : splitString) {
                try {
                    double val = Double.parseDouble(tok);
                    if (Double.isNaN(alt)) {
                        alt = val;
                    } else if (Double.isNaN(speed)) {
                        speed = val;
                    } else if (Double.isNaN(dir)) {
                        dir = val;
                    } else
                        break;
                } catch (NumberFormatException ignored) {
                }
            }

            // convert and round the alt
            double altFeet = 1000 * ConversionFactors.METERS_TO_FEET * alt;

            // convert and round the speed
            int speedInKnots = (int) Math.round(speed * 1.94384);

            // round the dir
            int dirRounded = (int) Math.round(dir);

            if (speed < 300 && dir < 720)
                windInfo.add(new WindInfo((int) altFeet, speedInKnots, dirRounded));
        }

        return windInfo;
    }
}
