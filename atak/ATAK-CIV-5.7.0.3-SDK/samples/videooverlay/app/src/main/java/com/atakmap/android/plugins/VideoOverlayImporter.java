
package com.atakmap.android.plugins;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.Collections;
import java.util.Set;

import org.simpleframework.xml.convert.ConvertException;

import android.net.Uri;
import android.os.Bundle;

import com.atakmap.android.importexport.Importer;
import com.atakmap.comms.CommsMapComponent.ImportResult;

public class VideoOverlayImporter implements Importer {

    public final static String CONTENT_TYPE = "video overlay";

    public final static String MPEG2_TS_MIME = "video/mp2t";
    private final static Set<String> SUPPORTED_MIME_TYPES = Collections
            .singleton(MPEG2_TS_MIME);

    private final VideoOverlayManager mgr;

    VideoOverlayImporter(VideoOverlayManager mgr) {
        this.mgr = mgr;
    }

    @Override
    public String getContentType() {
        return CONTENT_TYPE;
    }

    @Override
    public Set<String> getSupportedMIMETypes() {
        return SUPPORTED_MIME_TYPES;
    }

    @Override
    public ImportResult importData(InputStream source, String mime, Bundle b)
            throws IOException {
        // XXX - ??? don't support import from stream currently
        return ImportResult.IGNORE;
    }

    @Override
    public ImportResult importData(Uri uri, String mime, Bundle b)
            throws IOException {
        if (!SUPPORTED_MIME_TYPES.contains(mime))
            return ImportResult.IGNORE;

        try {
            if (this.mgr.add(new File(uri.getPath())))
                return ImportResult.SUCCESS;
            else
                return ImportResult.FAILURE;
        } catch (Exception e) {
            throw new IOException(e);
        }
    }

    @Override
    public boolean deleteData(Uri uri, String mime) throws IOException {
        return false;
    }
}
