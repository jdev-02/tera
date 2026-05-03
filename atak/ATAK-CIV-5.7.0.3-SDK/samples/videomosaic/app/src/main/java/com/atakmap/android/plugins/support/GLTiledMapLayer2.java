package com.atakmap.android.plugins.support;

import com.atakmap.map.MapRenderer;
import com.atakmap.map.layer.raster.DatasetDescriptor;

public final class GLTiledMapLayer2 extends com.atakmap.map.layer.raster.tilereader.opengl.GLTiledMapLayer2 {
    public GLTiledMapLayer2(MapRenderer surface, DatasetDescriptor info) {
        super(surface, info);

        init();
    }

    @Override
    protected void init() {
        if(tileReader == null)
            super.init();
    }
}
