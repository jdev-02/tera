package com.atakmap.android.customtiles;

import com.atakmap.coremap.log.Log;
import com.atakmap.database.CursorIface;
import com.atakmap.database.DatabaseIface;
import com.atakmap.database.Databases;
import com.atakmap.map.layer.feature.AttributeSet;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.FeatureSet;
import com.atakmap.map.layer.feature.Utils;
import com.atakmap.map.layer.feature.datastore.FeatureSetDatabase2;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Point;
import com.atakmap.map.layer.feature.style.BasicStrokeStyle;
import com.atakmap.map.layer.feature.style.IconPointStyle;
import com.atakmap.map.layer.feature.style.Style;
import com.atakmap.map.layer.raster.osm.OSMUtils;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

/**
 * Extracts the features contained within a Custom Tiles dataset
 *
 * Created by Developer on 8/22/2018.
 */

public final class CustomTilesFeatureExtractor {
    private static Set<String> POIS_COLUMNS = new HashSet<String>(Arrays.asList("name", "latitude", "longitude", "zoom_level"));
    private static Set<String> AOIS_COLUMNS = new HashSet<String>(Arrays.asList("name", "shape"));

    private CustomTilesFeatureExtractor() {} // not instantiable

    /**
     * Extracts all of the features (POIs and AOIs) contained within the specified Custom Tiles
     * dataset.
     *
     * @param path  The path to the Custom Tiles dataset file
     *
     * @return  A FeatureDataStore2 instance containing all of the extracted features within the
     *          dataset or <code>null</code> if the specified path does not point to a Custom Tiles
     *          dataset
     */
    public static FeatureDataStore2 extractFeatures(String path) {
        DatabaseIface database = null;
        try {
            // open the database
            database = Databases.openDatabase(path, true);
            // create new data store to hold features
            FeatureDataStore2 retval = new FeatureSetDatabase2(null);

            // if present, extract POIs and add to data store
            if(hasTable(database, "pois", POIS_COLUMNS)) {
                final long fsid = retval.insertFeatureSet(new FeatureSet("Custom Tiles", "Custom Tiles", "Points of Interest", Double.MAX_VALUE, 0d));
                FeatureSet pointsOfInterest = Utils.getFeatureSet(retval, fsid);
                CursorIface result = null;
                try {
                    result = database.query("SELECT name, latitude, longitude, zoom_level FROM pois", null);
                    while(result.moveToNext()) {
                        // pack the desired zoomto rolution in the feature attributes
                        AttributeSet attribs = new AttributeSet();
                        attribs.setAttribute("zoomToResolution", OSMUtils.mapnikTileResolution(result.getInt(3)));

                        // specify the style for the point. we will use an icon style. the 'color'
                        // specified is a 32-bit packed ARGB representation. pixel values in the
                        // icon image will be multiplied by the specified icon. A value of '-1' is
                        // equal to opaque white.
                        Style style = new IconPointStyle(0xFF0000FF,
                                                         "http://maps.google.com/mapfiles/kml/paddle/wht-blank.png",
                                                         0, 0,
                                                         0, 0,
                                                         0,
                                                         true);

                        // create and insert a feature for the POI in the datastore
                        retval.insertFeature(new Feature(
                                             pointsOfInterest.getId(),
                                             result.getString(0),
                                             new Point(result.getDouble(2), result.getDouble(1)),
                                             style,
                                             attribs));
                    }
                } finally {
                    if(result != null)
                        result.close();
                }
            }
            // if present, extract AOIs and add to data store
            if(hasTable(database, "aois", AOIS_COLUMNS)) {
                final long fsid = retval.insertFeatureSet(new FeatureSet("Custom Tiles", "Custom Tiles", "Areas of Interest", Double.MAX_VALUE, 0d));
                FeatureSet areasOfInterest = Utils.getFeatureSet(retval, fsid);
                CursorIface result = null;
                try {
                    result = database.query("SELECT name, shape FROM aois", null);
                    while(result.moveToNext()) {
                        // specify the style for the shape. we will use a basic stroke style. the
                        // 'color' specified is a 32-bit packed ARGB representation.
                        Style style = new BasicStrokeStyle(0xFF0000FF, 3f);

                        // create and insert a feature for the POI in the datastore
                        retval.insertFeature(new Feature(
                                             areasOfInterest.getId(),
                                             result.getString(0),
                                             parseShape(result.getString(1)),
                                             style,
                                             new AttributeSet()));
                    }
                } finally {
                    if(result != null)
                        result.close();
                }
            }

            // return data store
            return retval;
        } catch(Throwable t) {
            Log.e("CustomTilesFeatureExtractor", "Error occured extracting features from " + path, t);
            return null;
        } finally {
            if(database != null)
                database.close();
        }
    }

    private static boolean hasTable(DatabaseIface database, String tableName, Set<String> columns) {
        Set<String> tableCols = Databases.getColumnNames(database, tableName);
        return (tableCols != null) && tableCols.containsAll(columns);
    }

    private static Geometry parseShape(String shape) {
        LineString retval = new LineString(2);
        String[] coords = shape.split("\\,");
        for(int i = 0; i < coords.length; i++) {
            String[] lla = coords[i].trim().split("\\s+");
            if(lla.length < 2) {
                Log.w("CustomTilesFeatureExtractor", "Skipping invalid coord string: " + coords[i]);
                continue;
            }
            retval.addPoint(Double.parseDouble(lla[1]), Double.parseDouble(lla[0]));
        }
        return retval;
    }
}
