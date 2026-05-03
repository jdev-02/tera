package com.atakmap.android.importexportexample;

import android.net.Uri;
import android.os.Bundle;

import com.atakmap.android.importexport.AbstractImporter;
import com.atakmap.android.importexport.Importer;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.maps.Marker;
import com.atakmap.android.maps.PointMapItem;
import com.atakmap.android.user.PlacePointTool;
import com.atakmap.comms.CommsMapComponent;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.Collections;
import java.util.Set;


public class ExFmtImporter extends AbstractImporter {
    public final static String TEXT_CSV = "text/csv";
    public final static String CONTENT_TYPE = "Import/Export Example File";

    public final static Importer INSTANCE = new ExFmtImporter();

    private ExFmtImporter() {
        super(CONTENT_TYPE);
    }

    @Override
    public Set<String> getSupportedMIMETypes() {
        return Collections.<String>singleton(TEXT_CSV);
    }

    @Override
    public CommsMapComponent.ImportResult importData(InputStream inputStream, String s, Bundle bundle) throws IOException {
        int parsed = 0;
        BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream));
        do {
            // iterate each row
            final String line = reader.readLine();
            if(line == null)
                break;

            // parse each line
            if(parse(line) != null)
                parsed++;
        } while(true);

        // return success/failure. If at least one marker was parsed, we'll
        // consider it successful
        return (parsed > 0) ? CommsMapComponent.ImportResult.SUCCESS :
                CommsMapComponent.ImportResult.FAILURE;
    }

    @Override
    public CommsMapComponent.ImportResult importData(Uri uri, String s, Bundle bundle) throws IOException {
        return AbstractImporter.importUriAsStream(this, uri, s, bundle);
    }

    static Marker parse(String line) {
        String[] parts = line.split(",");
        if(parts == null)
            return null;
        if(parts.length < 5)
            return null;
        // first four columns may not be empty
        for(int i = 0; i < 5; i++) {
            if(parts[i].trim().length() < 1)
                return null;
        }
        final String uid = parts[0];
        final String callsign = parts[1];
        final String type = parts[2];
        final double latitude;
        try {
            latitude = Double.parseDouble(parts[3]);
        } catch(NumberFormatException e) {
            return null;
        }
        final double longitude;
        try {
            longitude = Double.parseDouble(parts[4]);
        } catch(NumberFormatException e) {
            return null;
        }
        double altitude = Double.NaN;
        if(parts.length >= 6) {
            try {
                altitude = Double.parseDouble(parts[5]);
            } catch(NumberFormatException ignored) {}
        }
        String remarks = null;
        if(parts.length >= 7) {
            remarks = parts[6];
        }

        // use the `MarkerCreator` utility to create the `Marker` and place it
        // on the map
        Marker marker = new PlacePointTool.MarkerCreator(new GeoPoint(latitude, longitude, altitude))
                .setCallsign(callsign)
                .setUid(uid)
                .setType(type)
                .placePoint();
        marker.setRemarks(remarks);
        return marker;
    }
}
