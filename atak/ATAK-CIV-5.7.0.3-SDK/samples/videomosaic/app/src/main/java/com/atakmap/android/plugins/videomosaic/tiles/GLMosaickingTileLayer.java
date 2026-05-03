package com.atakmap.android.plugins.videomosaic.tiles;

import android.util.Pair;

import com.atakmap.android.plugins.support.TileMatrixReader;
import com.atakmap.android.plugins.support.GLTiledMapLayer2;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.MapControl;
import com.atakmap.map.MapRenderer;
import com.atakmap.map.layer.Layer;
import com.atakmap.map.layer.control.ColorControl;
import com.atakmap.map.layer.opengl.GLAbstractLayer2;
import com.atakmap.map.layer.opengl.GLLayer2;
import com.atakmap.map.layer.opengl.GLLayerSpi2;
import com.atakmap.map.layer.raster.DatasetDescriptor;
import com.atakmap.map.layer.raster.ImageDatasetDescriptor;
import com.atakmap.map.layer.raster.controls.TileCacheControl;
import com.atakmap.map.layer.raster.controls.TileClientControl;
import com.atakmap.map.layer.raster.opengl.GLMapLayer3;
import com.atakmap.map.layer.raster.osm.OSMWebMercator;
import com.atakmap.map.layer.raster.tilematrix.TileMatrix;
import com.atakmap.map.layer.raster.tilematrix.opengl.GLTileMatrixLayer;
import com.atakmap.map.layer.raster.tilereader.TileReader;
import com.atakmap.map.layer.raster.tilereader.TileReaderFactory;
import com.atakmap.map.layer.raster.tilereader.TileReaderSpi2;
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.util.Collections2;
import com.atakmap.util.ConfigOptions;

import java.lang.ref.WeakReference;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

public final class GLMosaickingTileLayer extends GLAbstractLayer2 {
    final static String DATASET_TYPE = "tilemosaic";

    //

    static Map<String, WeakReference<TileMatrix>> _mosaics = new HashMap<>();

    final static TileReaderSpi2 MOSAIC_READER_SPI = new TileReaderSpi2() {
        @Override
        public int getPriority() {
            return 1;
        }

        @Override
        public String getName() {
            return DATASET_TYPE;
        }

        @Override
        public TileReader create(String uri, TileReaderFactory.Options options) {
            if(uri == null)
                return null;
            if(!uri.startsWith(DATASET_TYPE + "://"))
                return null;

            final String key = uri.substring(DATASET_TYPE.length()+3);

            final TileMatrix matrix;
            synchronized (_mosaics) {
                final WeakReference<TileMatrix> matrixRef = _mosaics.get(key);
                if(matrixRef == null)
                    return null;
                matrix = matrixRef.get();
                if(matrix == null) {
                    _mosaics.remove(key);
                    return null;
                }
            }

            TileReader.AsynchronousIO asyncio = (options != null) ? options.asyncIO : null;
            if(asyncio == null)
                asyncio = TileReader.getMasterIOThread();
            return new TileMatrixReader(matrix, uri, asyncio, false);
        }

        @Override
        public boolean isSupported(String uri) {
            return uri != null && uri.startsWith(DATASET_TYPE + "://");
        }
    };

    public final static GLLayerSpi2 SPI = new GLLayerSpi2() {
        @Override
        public int getPriority() {
            return 1;
        }

        @Override
        public GLLayer2 create(Pair<MapRenderer, Layer> object) {
            if(!(object.second instanceof MosaickingTileLayer))
                return null;
            final MosaickingTileLayer layer = (MosaickingTileLayer) object.second;
            synchronized(_mosaics) {
                if(_mosaics.isEmpty()) {
                    TileReaderFactory.registerSpi(MOSAIC_READER_SPI);
                }

                _mosaics.put(Integer.toHexString(layer.getTiles().hashCode()), new WeakReference<>(layer.getTiles()));
            }

            return new GLMosaickingTileLayer(object.first, (MosaickingTileLayer)object.second);
        }
    };

    GLMapLayer3 impl;
    final MosaickingTileLayer subject;
    final Set<MapControl> registeredControls;

    GLMosaickingTileLayer(MapRenderer surface, MosaickingTileLayer subject) {
        super(surface, subject, GLMapView.RENDER_PASS_SURFACE);

        this.subject = subject;
        registeredControls = Collections2.newIdentityHashSet();

    }

    @Override
    protected void init() {
        super.init();
        if(impl == null) {
            final TileMatrix.ZoomLevel[] levels = subject.getTiles().getZoomLevel();
            final DatasetDescriptor desc =new ImageDatasetDescriptor(
                    null,
                    "tilemosaic://" + Integer.toHexString(subject.getTiles().hashCode()),
                    "realtimemosaic",
                    DATASET_TYPE,
                    "osmdroid",
                    256 << levels[levels.length - 1].level, 256 << levels[levels.length - 1].level,
                    levels[levels.length - 1].resolution,
                    levels[levels.length - 1].level - levels[0].level + 1,
                    new GeoPoint(OSMWebMercator.INSTANCE.getMaxLatitude(), OSMWebMercator.INSTANCE.getMinLongitude()),
                    new GeoPoint(OSMWebMercator.INSTANCE.getMaxLatitude(), OSMWebMercator.INSTANCE.getMaxLongitude()),
                    new GeoPoint(OSMWebMercator.INSTANCE.getMinLatitude(), OSMWebMercator.INSTANCE.getMaxLongitude()),
                    new GeoPoint(OSMWebMercator.INSTANCE.getMinLatitude(), OSMWebMercator.INSTANCE.getMinLongitude()),
                    3857,
                    true,
                    false,
                    null,
                    Collections.emptyMap()
            );

            if(false) {
                // off-the-shelf `GLTileMatrixLayer` doesn't reliably support tile refresh
                impl = new GLTileMatrixLayer(
                        renderContext,
                        desc,
                        subject.getTiles()
                );
            } else {
                impl = new GLTiledMapLayer2(
                        renderContext,
                        desc
                );
            }

            // associate renderable controls with the layer
            Class<? extends MapControl>[] ctrlTypes = new Class[] {
                    TileClientControl.class,
                    TileCacheControl.class,
                    ColorControl.class,
            };
            for(Class<? extends MapControl> ctrlType : ctrlTypes) {
                MapControl ctrl = impl.getControl(ctrlType);
                if(ctrl != null) {
                    renderContext.registerControl(subject, ctrl);
                    registeredControls.add(ctrl);
                }
            }
        }
    }

    @Override
    public void release() {
        if(impl != null) {
            for(MapControl ctrl : registeredControls)
                renderContext.unregisterControl(subject, ctrl);
            registeredControls.clear();

            impl.release();
            impl = null;
        }
        super.release();
    }

    @Override
    protected void drawImpl(GLMapView view, int renderPass) {
        if(impl != null)
            impl.draw(view);
    }
}
