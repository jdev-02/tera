package com.atakmap.android.importexportexample;

import android.net.Uri;

import com.atakmap.android.importexport.AbstractMarshal;
import com.atakmap.android.importexport.Marshal;
import com.atakmap.android.maps.Marker;
import com.atakmap.android.user.PlacePointTool;
import com.atakmap.coremap.locale.LocaleUtil;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.io.SubInputStream;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;

public class ExFmtMarshal extends AbstractMarshal {
    public final static Marshal INSTANCE = new ExFmtMarshal();

    private ExFmtMarshal() {
        super(ExFmtImporter.CONTENT_TYPE);
    }

    @Override
    public String marshal(InputStream inputStream, int limit) throws IOException {
        // this example only supports reading from a file, not a stream. For
        // real-world use-cases involving streaming data, this method can be
        // implemented in addition to, or to the exclusion of, `marshal(Uri)`
        return null;
    }

    @Override
    public String marshal(Uri uri) throws IOException {
        File f = new File(uri.getPath());
        if(!f.exists())
            return null;
        if(!f.getName().toLowerCase(LocaleUtil.US).endsWith(".exfmt"))
            return null;
        try(FileInputStream fis = new FileInputStream(f);
            InputStreamReader isr = new InputStreamReader(fis);
            BufferedReader reader = new BufferedReader(isr)) {

            return isExFmt(reader.readLine()) ? ExFmtImporter.TEXT_CSV : null;
        }
    }

    @Override
    public int getPriorityLevel() {
        // priority determines when this `Marshal` will be evaluated in
        // comparison to other registered `Marshal` instances. Numerically
        // greater priorities are invoked before numerically lower priorities.
        // LIFO is used to settle collisions.
        return 1;
    }

    static boolean isExFmt(String line) {
        if(line == null)
            return false;
        String[] parts = line.split(",");
        if(parts == null)
            return false;
        if(parts.length < 5)
            return false;
        // first five columns may not be empty
        for(int i = 0; i < 5; i++) {
            if(parts[i].trim().length() < 1)
                return false;
        }

        // latitude
        try {
            Double.parseDouble(parts[3]);
        } catch(NumberFormatException e) {
            return false;
        }
        // longitude
        try {
            Double.parseDouble(parts[4]);
        } catch(NumberFormatException e) {
            return false;
        }

        // assumed matches format specification
        return true;
    }
}
