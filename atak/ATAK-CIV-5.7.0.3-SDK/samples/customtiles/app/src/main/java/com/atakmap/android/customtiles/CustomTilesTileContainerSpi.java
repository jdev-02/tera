package com.atakmap.android.customtiles;

import com.atakmap.database.DatabaseIface;
import com.atakmap.database.Databases;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;
import com.atakmap.map.layer.raster.tilematrix.TileContainerSpi;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;

import java.io.File;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

/**
 * Created by Developer on 7/23/2018.
 */

public class CustomTilesTileContainerSpi implements TileContainerSpi {
    public final static TileContainerSpi INSTANCE = new CustomTilesTileContainerSpi();

    private final static Map<String, Collection<String>> schema = new HashMap<String, Collection<String>>();
    static {
        schema.put("customtiles", Arrays.asList("z", "y", "x", "tile"));
        schema.put("info", Arrays.asList("srid", "origin_x", "origin_y", "min_x", "min_y", "max_x", "max_y", "tile_width", "tile_height", "pixel_size_x_z0", "pixel_size_y_z0"));
    }

    @Override
    public String getName() {
        return "Custom Tiles Example";
    }

    @Override
    public String getDefaultExtension() {
        // the default extension associated with the container. This is informative only.
        return ".customtiles";
    }

    @Override
    public TileContainer create(String s, String s1, TileMatrix tileMatrix) {
        // always return null -- this format is read-only
        return null;
    }

    @Override
    public TileContainer open(String s, TileMatrix tileMatrix, boolean b) {
        // we'll try to open the specified path as a SQLite database
        DatabaseIface db = null;
        try {
            db = Databases.openDatabase(s, true);

            // check the schema of the database, see if it matches the custom format
            if(!Databases.matchesSchema(db, schema, true))
                return null;

            final TileContainer retval = new CustomTilesTileContainer(new File(s), db);
            db = null; // ownership was transferred to the container
            return retval;
        } catch(Throwable t) {
            return null;
        } finally {
            if(db != null)
                db.close();
        }
    }

    @Override
    public boolean isCompatible(TileMatrix tileMatrix) {
        // the compatibility check is for container authoring, we should always return null
        return false;
    }
}
