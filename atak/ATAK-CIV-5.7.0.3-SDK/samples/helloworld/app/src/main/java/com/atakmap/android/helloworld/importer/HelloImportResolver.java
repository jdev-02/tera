package com.atakmap.android.helloworld.importer;

import android.content.Context;
import android.widget.Toast;

import com.atakmap.android.helloworld.plugin.R;
import com.atakmap.android.importfiles.sort.ImportResolver;
import com.atakmap.android.maps.MapView;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;

import java.io.File;
import java.io.IOException;
import java.util.Set;


/**
 * Will match/import a file with extension .hwi e.g. "sample.hwi"
 * With a body containing 'helloWorldSample' e.g. {"helloWorldSample" : "Sample File"}
 */
public class HelloImportResolver extends ImportResolver {

    private static final String TAG = "HelloImportResolver";

    public static final String TOOL_NAME = FileSystemUtils.TOOL_DATA_DIRECTORY + File.separator +
            "helloworld";

    public static final String MATCHER = "helloWorldSample";
    public static final String FILE_EXT = ".hwi";
    private final MapView mapView;

    public HelloImportResolver(MapView mapView, Context pContext) {
        super(FILE_EXT, TOOL_NAME, "Hello Importer", pContext.getDrawable(R.drawable.ic_launcher));
        this.mapView = mapView;
    }

    public boolean match(File file) {
        return super.match(file) && isHelloWorld(file);
    }

    private boolean isHelloWorld(File file) {
        if (!FileSystemUtils.isFile(file))
            return false;

        try {
            String contents = FileSystemUtils.copyStreamToString(file);
            return !FileSystemUtils.isEmpty(contents) && contents.contains(MATCHER);
        } catch (IOException e) {
            Log.w(TAG, "Unable to read file", e);
            return false;
        }
    }

    protected void onFileSorted(File src, File dst, Set<SortFlags> flags) {
        super.onFileSorted(src, dst, flags);
        Log.d(TAG, "Sorted, now initiating import");
        importHelloworld(dst);
    }

    private void importHelloworld(File file) {
        Log.d(TAG, "importHelloworld: " + file.getAbsolutePath());

        try {
            String contents = FileSystemUtils.copyStreamToString(file);
            if (FileSystemUtils.isEmpty(contents) || !contents.contains(MATCHER)) {
                Log.w(TAG, "importHelloworld file invalid");
                toast("Invalid or corrupt Hello World sample file");
                return;
            }

            Log.d(TAG, "importHelloworld: " + contents);
            toast("Hello World import: " + contents);

        } catch (IOException e) {
            Log.w(TAG, "importHelloworld Unable to read file", e);
        }
    }

    private void toast(String str) {
        mapView.post(new Runnable() {
            @Override
            public void run() {
                Toast.makeText(mapView.getContext(), str, Toast.LENGTH_LONG).show();
            }
        });
    }
}
