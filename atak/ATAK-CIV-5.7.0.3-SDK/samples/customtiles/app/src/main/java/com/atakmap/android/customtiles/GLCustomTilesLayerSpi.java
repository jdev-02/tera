package com.atakmap.android.customtiles;

import android.util.Pair;

import com.atakmap.map.MapRenderer;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.opengl.GLMapLayer3;
import com.atakmap.map.layer.raster.opengl.GLMapLayerSpi3;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;
import com.atakmap.map.layer.raster.tilematrix.opengl.GLTileMatrixLayer;

/**
 * Created by Developer on 7/23/2018.
 */

public class GLCustomTilesLayerSpi implements GLMapLayerSpi3 {
    public final static GLMapLayerSpi3 INSTANCE = new GLCustomTilesLayerSpi();

    @Override
    public int getPriority() {
        // returns the priority assigned to this GLMapLayerSpi3. The priority controls the
        // iteration order used over the registered GLMapLayerSpi3 when ATAK requests a renderer for
        // a DatasetDescriptor instance. Sorting is based on descending priority value; instances
        // with larger int values are evaluated before instances with smaller int values. In the
        // event that two instances share the same priority value, registration order is considered
        // next.
        return 1;
    }

    @Override
    public GLMapLayer3 create(Pair<MapRenderer, DatasetDescriptor> arg) {
        final MapRenderer ctx = arg.first;
        final DatasetDescriptor dataset = arg.second;

        // check to see if the dataset is the customtiles dataset type
        if(!dataset.getDatasetType().equals(CustomTilesDatasetDescriptorSpi.DATASET_TYPE))
            return null;

        // try to create the TileContainer
        final TileContainer tiles = CustomTilesTileContainerSpi.INSTANCE.open(dataset.getUri(), null, true);
        if(tiles == null)
            return null;

        // return the library provided renderer implementation
        return new GLTileMatrixLayer(ctx, dataset, tiles);
    }
}
