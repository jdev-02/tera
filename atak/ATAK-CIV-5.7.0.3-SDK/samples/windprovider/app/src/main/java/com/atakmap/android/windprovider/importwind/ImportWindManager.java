
package com.atakmap.android.windprovider.importwind;

import android.content.Context;

public class ImportWindManager {

    private static final String TAG = "ImportWindManager";
    private final Context con;

    private static ImportWindManager _instance;

    private final OnlineWindImport importWindHTTP;
    private final ImportWindFile importWindFile;

    /**
     * Constructor sets up the context, gives the WindData class to return values to, and tells if
     * there was user input that might be overwritten.
     */
    private ImportWindManager(Context c) {
        con = c;
        _instance = this;
        importWindHTTP = new OnlineWindImport(c);
        importWindFile = new ImportWindFile(c);
    }

    public static synchronized ImportWindManager getInstance(Context context) {
        if (_instance == null)
            _instance = new ImportWindManager(context);
        return _instance;
    }


    public OnlineWindImport getOnlineImport() {
        return importWindHTTP;
    }


}
