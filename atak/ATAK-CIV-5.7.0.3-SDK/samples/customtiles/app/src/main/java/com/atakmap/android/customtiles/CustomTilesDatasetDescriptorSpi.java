package com.atakmap.android.customtiles;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.DatasetDescriptorSpi;
import com.atakmap.map.layer.raster.DatasetDescriptorSpiArgs;
import com.atakmap.map.layer.raster.ImageDatasetDescriptor;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.map.projection.Projection;
import com.atakmap.map.projection.ProjectionFactory;
import com.atakmap.math.PointD;

import java.io.File;
import java.util.Collections;
import java.util.Set;

/**
 * Created by Developer on 7/23/2018.
 */

public class CustomTilesDatasetDescriptorSpi implements DatasetDescriptorSpi {
    public final static DatasetDescriptorSpi INSTANCE = new CustomTilesDatasetDescriptorSpi();
    public final static String DATASET_TYPE = "customtiles";

    @Override
    public int parseVersion() {
        // the parse version defines the implementation version of this code that is used to derive
        // a dataset from a file. When the implementation changes such that it would produce a
        // different result from 'create' for a file that was successfully handled previously, the
        // version number should be bumped
        return 1;
    }

    @Override
    public Set<DatasetDescriptor> create(DatasetDescriptorSpiArgs args, Callback callback) {
        final File sourceFile = args.file;
        final File workingDir = args.workingDir;

        try {
            // invokers may optionally supply a callback interface. This callback interface may be
            // used to receive progress and parse errors. The callback also provides a mechanism to
            // "probe" a file to see if it supported. This operation should be as lightweight as
            // possible.
            if(callback != null && callback.isProbeOnly()) {
                // for our implementation, opening the TileContainer is a pretty cheap operation, so
                // we'll simply see if we can create a non-null TileContainer from the specified
                // file
                TileContainer tiles = null;
                try {
                    // try to create the container from the source file
                    tiles = CustomTilesTileContainerSpi.INSTANCE.open(sourceFile.getAbsolutePath(), null, true);
                    // report to the callback whether or not the probe was successful
                    callback.setProbeMatch(tiles != null);
                } finally {
                    // invoke dispose to explicitly release any allocated resources immediately
                    if(tiles != null)
                        tiles.dispose();
                }
                return null;
            }

            // we can use the TileContainer for our format to populate the DatasetDescriptor
            TileContainer tiles = null;
            try {
                // try to create the container from the source file
                tiles = CustomTilesTileContainerSpi.INSTANCE.open(sourceFile.getAbsolutePath(), null, true);
                // if we could not create a TileContainer from the file, we don't support the
                // dataset
                if(tiles == null)
                    return null;

                // compute the bounds of the dataset. We'll obtain the bounds from the TileContainer
                // specified in the native spatial reference, then convert to WGS84
                Envelope bounds = tiles.getBounds();
                // obtain the Projection object that will allow us to perform the coordinate
                // conversions
                Projection proj = ProjectionFactory.getProjection(tiles.getSRID());
                // if 'proj' is 'null', the projection is not supported
                if(proj == null)
                    return null;
                // compute the corresponding corner coordinates. The Projection interface defines
                // two functions for transforming coordinates:
                //  forward -- transforms latitude,longitude,altitude into projected coordinates
                //  inverse -- transforms projected coordinates in latitude,longitude,altitude
                GeoPoint upperLeft = proj.inverse(new PointD(bounds.minX, bounds.maxY), null);
                GeoPoint upperRight = proj.inverse(new PointD(bounds.maxX, bounds.maxY), null);
                GeoPoint lowerRight = proj.inverse(new PointD(bounds.maxX, bounds.minY), null);
                GeoPoint lowerLeft = proj.inverse(new PointD(bounds.minX, bounds.minY), null);

                // we'll compute the "width" and "height" of the tile pyramid, at its maximum
                // resolution, for the data containing region. The respective dimensions will be
                // equal to the extent of the bounds divided by the pixel size; remember:
                // pixelSize[XY] is in native spatial reference units.
                final TileMatrix.ZoomLevel maxZoomLevel = tiles.getZoomLevel()[tiles.getZoomLevel().length-1];

                final int width = (int)Math.ceil((bounds.maxX-bounds.minX)/maxZoomLevel.pixelSizeX);
                final int height = (int)Math.ceil((bounds.maxY-bounds.minY)/maxZoomLevel.pixelSizeY);

                final DatasetDescriptor retval = new ImageDatasetDescriptor(
                        // the name we are assigning to the dataset -- we'll give it the filename
                        sourceFile.getName(),
                        // the URI from which the dataset was derived -- the file we are parsing
                        sourceFile.getAbsolutePath(),
                        // the provider name
                        getType(),
                        DATASET_TYPE,
                        sourceFile.getName(),
                        width, height,
                        // the number of resolution levels present in the dataset
                        tiles.getZoomLevel().length,
                        upperLeft, upperRight, lowerRight, lowerLeft,
                        tiles.getSRID(),
                        false,
                        // pass through the provider working directory
                        workingDir,
                        Collections.<String, String>emptyMap());

                return Collections.singleton(retval);
            } finally {
                // invoke dispose to explicitly release any allocated resources immediately
                if(tiles != null)
                    tiles.dispose();
            }
        } catch(Throwable t) {
            // deliver the error to the callback if one was provided
            if(callback != null)
                callback.errorOccurred("Failed to parse " + sourceFile.getName(), t);

            // no exceptions should be raised -- in the event that this DatasetDescriptorSpi cannot
            // handle the input file, 'null' should be returned
            return null;
        } finally {

        }
    }

    @Override
    public int getPriority() {
        // returns the priority assigned to this DatasetDescriptorSpi. The priority controls the
        // iteration order used over the registered DatasetDescriptorSpis when 1) determining if a
        // file is supported and 2) invoking 'create' to obtain a dataset for a given file. Sorting
        // is based on descending priority value; instances with larger int values are evaluated
        // before instances with smaller int values. In the event that two instances share the same
        // priority value, registration order is considered next.

        // While not required or documented, the convention generally used for priority is reflected
        // by the logic below
        // p0 : file is octet stream
        // p1 : file is SQLite
        // p2 : file is SQLite with CustomTiles schema
        // This kind of approach can disambiguate selecting priorities for specializations within a
        // given format to ensure that specialized handlers are evaluated before more generic ones.
        return 2;
    }

    @Override
    public String getType() {
        // The "provider" name we will to associate with the DatasetDescriptor instances produced by
        // this DatasetDescriptorSpi instance
        return "customtiles";
    }

    @Override
    public Set<DatasetDescriptor> create(DatasetDescriptorSpiArgs args) {
        return create(args, null);
    }
}
