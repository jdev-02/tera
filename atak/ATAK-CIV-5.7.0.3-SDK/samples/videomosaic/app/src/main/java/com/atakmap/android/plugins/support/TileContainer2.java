package com.atakmap.android.plugins.support;

import com.atakmap.map.layer.control.Controls;
import com.atakmap.map.layer.raster.tilematrix.TileContainer;

public interface TileContainer2 extends TileContainer, Controls {
    /**
     * Deletes the specified tiles from the container, if present
     *
     * @param zoomLevel The zoom level
     * @param stx       The starting tile column, inclusive
     * @param sty       The starting tile row, inclusive
     * @param ftx       The ending tile column, inclusive
     * @param fty       The ending tile row, inclusive
     */
    void deleteTiles(int zoomLevel, int stx, int sty, int ftx, int fty);
}
