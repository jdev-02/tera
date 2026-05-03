
package com.atakmap.android.windprovider.importwind.parsers;

import android.content.Context;
import android.content.SharedPreferences;
import android.preference.PreferenceManager;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.windprovider.importwind.WindInfo;
import com.atakmap.android.windprovider.importwind.WindParseException;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.io.InputStream;
import java.util.List;

/**
 * Interface for wind parsers.
 */
public abstract class WindParser {

    private static final String TAG = "WindParser";

    private final String name;
    protected final Context context;
    protected final SharedPreferences prefs;

    /**
     * @param context the plugin context to use during the import process
     * @param name the well known name for the parser
     */
    public WindParser(Context context, String name) {
        this.context = context;
        this.name = name;
        prefs = PreferenceManager.getDefaultSharedPreferences(MapView.getMapView().getContext());
    }


    /**
     * Returns a well known name for the parser
     * @return the well known name.
     */
    public String getName() {
        return name;
    }

    /**
     * Get the URL for the wind server HTTP request, given the location/hour offset
     *
     * @param location   The geographic location of the request.
     * @param hourOffset Time offset in hours relative to current.
     * @return URL of HTTP request.
     */
    public abstract String url(GeoPoint location, int hourOffset);

    /**
     * Check if this implementation supports time offsets. e.g. many wind servers will only support
     * serving up current winds (not projected winds).
     *
     * @return True if offset wind data can be returned.
     */
    public abstract boolean supportTimeOffset();

    /**
     * <p>
     * Parse the specified data and populate the table.
     * <br>
     * Altitudes should be normalized to readings every 1000 feet or omitted if data is not
     * available for a given 1000ft altitude.
     * </p>
     * <br>
     * <p>
     * Map altitude (ft AGL) to :
     *     <ul>
     *     <li>wind speed (knots)</li>
     *     <li>direction (true)</li>
     *     </ul>
     * </p>
     * <p><i>
     *     e.g. [alt=1000, [speed=52, direction=180]]
     * </i></p>
     *
     * @param inputStream the input stream to parse
     * @return the list of wind information corresponding to the data
     */
    public abstract List<WindInfo> parse(InputStream inputStream) throws WindParseException;


}
