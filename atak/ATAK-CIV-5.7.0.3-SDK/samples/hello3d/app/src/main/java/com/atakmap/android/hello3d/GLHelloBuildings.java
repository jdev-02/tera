
package com.atakmap.android.hello3d;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.Map;
import java.util.Set;

import android.graphics.Color;
import android.util.Pair;


import com.atakmap.coremap.maps.coords.GeoPoint.AltitudeReference;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.lang.Unsafe;
import com.atakmap.map.MapRenderer;
import com.atakmap.map.layer.Layer;
import com.atakmap.map.layer.feature.Adapters;
import com.atakmap.map.layer.feature.AttributeSet;
import com.atakmap.map.layer.feature.DataStoreException;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureCursor;
import com.atakmap.map.layer.feature.FeatureDataStore;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.FeatureDataStore2.FeatureQueryParameters;
import com.atakmap.map.layer.feature.FeatureDefinition2;
import com.atakmap.map.layer.feature.style.Style;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.GeometryCollection;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.map.layer.feature.style.BasicFillStyle;
import com.atakmap.map.layer.feature.style.CompositeStyle;
import com.atakmap.map.layer.opengl.GLAsynchronousLayer2;
import com.atakmap.map.layer.opengl.GLLayer2;
import com.atakmap.map.layer.opengl.GLLayerSpi2;
import com.atakmap.map.opengl.GLAsynchronousMapRenderable2;
import com.atakmap.map.opengl.GLMapBatchable2;
import com.atakmap.map.opengl.GLMapRenderable2;
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.opengl.GLES20FixedPipeline;
import com.atakmap.opengl.GLRenderBatch2;

public class GLHelloBuildings
        extends GLAsynchronousLayer2<Collection<Feature>> implements FeatureDataStore2.OnDataStoreContentChangedListener {

    public final static GLLayerSpi2 SPI = new GLLayerSpi2() {

        @Override
        public int getPriority() {
            // HelloBuildings : Layer2
            return 1;
        }

        @Override
        public GLLayer2 create(Pair<MapRenderer, Layer> object) {
            final MapRenderer renderCtx = object.first;
            final Layer layer = object.second;

            if (!(layer instanceof HelloBuildings))
                return null;

            return new GLHelloBuildings(renderCtx, (HelloBuildings) layer);
        }

    };

    private FeatureDataStore2 dataStore;
    private RendererImpl impl;

    public GLHelloBuildings(MapRenderer surface, HelloBuildings subject) {
        super(surface, subject);

        this.impl = new RendererImpl();
        this.dataStore = subject.getDataStore();

        dataStore.addOnDataStoreContentChangedListener(this);
    }

    @Override
    public void onDataStoreContentChanged(FeatureDataStore2 featureDataStore) {
        this.invalidateNoSync();
    }

    @Override
    public void onFeatureInserted(FeatureDataStore2 dataStore, long fid, FeatureDefinition2 def, long version) {

    }

    @Override
    public void onFeatureUpdated(FeatureDataStore2 dataStore, long fid, int modificationMask, String name, Geometry geom, Style style, AttributeSet attribs, int attribsUpdateType) {

    }

    @Override
    public void onFeatureDeleted(FeatureDataStore2 dataStore, long fid) {

    }

    @Override
    public void onFeatureVisibilityChanged(FeatureDataStore2 dataStore, long fid, boolean visible) {

    }

    @Override
    protected void releaseImpl() {
        dataStore.removeOnDataStoreContentChangedListener(this);
        this.impl.release();
        this.impl.renderables.clear();
    }

    @Override
    public int getRenderPass() {
        // rendered content will be full 3D objects as opposed to graphics that
        // should be composited onto the terrain 
        return GLMapView.RENDER_PASS_SPRITES;
    }

    @Override
    protected Collection<? extends GLMapRenderable2> getRenderList() {
        // this method returns the content that will be rendered during the draw
        // pump. the content of this object should be updated during the
        // invocation of 'updateRenderList'
        return Collections.singleton(this.impl);
    }

    @Override
    protected void resetPendingData(Collection<Feature> pendingData) {
        // the reset method prepares the Object that will hold the query results
        // for a new query. in this case, we will clear our the collection
        pendingData.clear();
    }

    @Override
    protected void releasePendingData(Collection<Feature> pendingData) {
        // the release method is invoked prior to the worker thread exiting. any
        // resource deallocation for the Object should occur here
        pendingData.clear();
    }

    @Override
    protected Collection<Feature> createPendingData() {
        // the pending data object will hold the results of the query performed
        // on the background worker thread
        return new LinkedList<Feature>();
    }

    @Override
    protected boolean updateRenderList(
            GLAsynchronousMapRenderable2.ViewState state,
            Collection<Feature> queryResults) {

        // this method, along with draw and release are guaranteed to be
        // externally synchronized, per GLAsynchronousMapRenderable2. we can
        // modify any of our renderable data structures here in a thread-safe
        // manner 

        // track which features have gone "stale" i.e. those that are no longer
        // in the AOI
        Set<Long> staleFIDs = new HashSet<Long>(this.impl.renderables.keySet());

        // iterate the results of the query and update the render list
        for (Feature f : queryResults) {
            final Long fid = Long.valueOf(f.getId());
            GLMultiPolygon r = this.impl.renderables.get(fid);
            if (r == null) {
                r = new GLMultiPolygon(this.renderContext);
                this.impl.renderables.put(fid, r);
            }
            // update the renderer
            r.update(f);
            staleFIDs.remove(fid);
        }

        // if there are stale renderables, clean up
        if (!staleFIDs.isEmpty()) {
            // while we can evict the stale renderers from the render list here
            // safely, the renderers' 'release' method MUST be invoked on the GL
            // thread per the contract of GLMapRenderable2

            final Collection<GLMapRenderable2> toRelease = new ArrayList<GLMapRenderable2>(
                    staleFIDs.size());
            for (Long fid : staleFIDs) {
                GLMultiPolygon r = this.impl.renderables.remove(fid);
                if (r == null)
                    throw new IllegalStateException();
                toRelease.add(r);
            }

            this.renderContext.queueEvent(new Runnable() {
                public void run() {
                    for (GLMapRenderable2 r : toRelease)
                        r.release();
                }
            });
        }

        return true;
    }

    @Override
    protected void query(GLAsynchronousMapRenderable2.ViewState state,
            Collection<Feature> retval) {

        FeatureCursor result = null;
        try {
            // create a filter to use when querying the data store
            FeatureDataStore.FeatureQueryParameters params = new FeatureDataStore.FeatureQueryParameters();
            // only accept visible features
            params.visibleOnly = true;
            // only accept features in the AOI
            params.spatialFilter = new FeatureDataStore.FeatureQueryParameters.RegionSpatialFilter(
                    new GeoPoint(state.northBound, state.westBound),
                    new GeoPoint(state.southBound, state.eastBound));
            // only accept features that meet the display threshold
            params.maxResolution = state.drawMapResolution;

            // before we issue the query, make sure that the query hasn't been
            // asynchronously aborted
            if (this.checkQueryThreadAbort())
                return;

            // query the data store based on the target view state parameters
            try {
                result = this.dataStore.queryFeatures(Adapters.adapt(params, null));
                while (result.moveToNext()) {
                    // check for abort
                    if (this.checkQueryThreadAbort())
                        break;

                    // add the feature to the list to be returned
                    retval.add(result.get());
                }
            } catch (DataStoreException dse) {
            }
        } finally {
            if (result != null)
                result.close();
        }
    }

    private static class RendererImpl implements GLMapRenderable2 {
        public Map<Long, GLMultiPolygon> renderables;
        private GLRenderBatch2 batch;

        RendererImpl() {
            this.renderables = new HashMap<Long, GLMultiPolygon>();
            this.batch = null;
        }

        @Override
        public void draw(GLMapView view, int renderPass) {
            // make sure the current render pass is supported 
            if ((renderPass & this.getRenderPass()) == 0)
                return;

            // verify we have content to render
            if (this.renderables.isEmpty())
                return;

            if (this.batch == null)
                this.batch = new GLRenderBatch2();

            // begin the batch operation. hints may be specified to allow for some
            // optimizations based on assumptions. if inputs are provided that do
            // not agree with the specified hints, the batch will fallback to a more
            // general purpose path
            this.batch.begin(GLRenderBatch2.HINT_UNTEXTURED);

            // capture the Projection and Model-View matrices and upload them to the
            // batch
            GLES20FixedPipeline.glGetFloatv(GLES20FixedPipeline.GL_PROJECTION,
                    view.scratch.matrixF, 0);
            this.batch.setMatrix(GLES20FixedPipeline.GL_PROJECTION,
                    view.scratch.matrixF, 0);
            GLES20FixedPipeline.glGetFloatv(GLES20FixedPipeline.GL_MODELVIEW,
                    view.scratch.matrixF, 0);
            this.batch.setMatrix(GLES20FixedPipeline.GL_MODELVIEW,
                    view.scratch.matrixF, 0);

            // iterate the renderables and add to the batch
            for (GLMultiPolygon r : this.renderables.values())
                r.batch(view, this.batch, renderPass);

            // all content has been added to the batch, flush to the display
            this.batch.end();
        }

        @Override
        public void release() {
            for (GLMultiPolygon r : this.renderables.values())
                r.release();

            if (this.batch != null) {
                this.batch.release();
                this.batch.dispose();
                this.batch = null;
            }
        }

        @Override
        public int getRenderPass() {
            return GLMapView.RENDER_PASS_SPRITES;
        }
    }

    // the renderer implementation for the geometries contained within the
    // HelloBuildings layer. since we have knowledge of exactly what will be
    // contained in the data store, we can tailor the implementation to the
    // expected content

    private static class GLMultiPolygon
            implements GLMapRenderable2, GLMapBatchable2 {

        private MapRenderer renderCtx;
        private Collection<LineString> rings;
        private FloatBuffer vertices;
        private long verticesPtr;
        private long version;
        private float colorR;
        private float colorG;
        private float colorB;
        private float colorA;

        GLMultiPolygon(MapRenderer renderCtx) {
            this.renderCtx = renderCtx;
            this.rings = new LinkedList<LineString>();
            this.vertices = null;
            this.verticesPtr = 0L;
            this.colorR = 0f;
            this.colorG = 0f;
            this.colorB = 0f;
            this.colorA = 0f;
            this.version = FeatureDataStore.FEATURE_ID_NONE;
        }

        public void update(final Feature feature) {
            // the batch/draw/release methods are guaranteed to only be invoked
            // on the GL thread. to avoid having to synchronize, we will only
            // modify the data accessed in those methods on that thread

            if (!this.renderCtx.isRenderThread()) {
                this.renderCtx.queueEvent(new Runnable() {
                    public void run() {
                        updateImpl(feature.getVersion(), feature.getGeometry(),
                                feature.getStyle());
                    }
                });
            } else {
                this.updateImpl(feature.getVersion(), feature.getGeometry(),
                        feature.getStyle());
            }
        }

        private void updateImpl(long version, Geometry geom, Style style) {
            // every feature contains a version number. features with the same
            // ID and same version will contain identical data. we will check
            // the version number for the content we've currently captured and
            // return immediately if it is the same. if the version is the
            // special constant, FEATURE_VERSION_NONE, an update is forced as it
            // indicates the versioning is not tracked
            if (version != FeatureDataStore.FEATURE_VERSION_NONE
                    && version == this.version)
                return;

            // record the version that we will be current with
            this.version = version;

            // clear out the previous content to prepare for the update
            this.rings.clear();

            // we are expecting a GeometryCollection that only has Polygons as
            // its children
            if (!(geom instanceof GeometryCollection))
                return;

            final GeometryCollection c = (GeometryCollection) geom;
            for (Geometry child : c.getGeometries()) {
                // verify that the child is a polygon
                if (!(child instanceof Polygon))
                    continue;

                final Polygon p = (Polygon) child;

                // for our example, we are going to ignore any inner rings
                // (holes). capture the exterior ring since we'll be using that
                // to create the vertex data
                final LineString l = p.getExteriorRing();

                // verify that the polygon is not empty
                if (l == null)
                    continue;

                this.rings.add(l);
            }

            // we are looking for a BasicFillStyle to get the color to render
            do {
                if (style instanceof BasicFillStyle) {
                    final BasicFillStyle fill = (BasicFillStyle) style;
                    this.colorR = (float) Color.red(fill.getColor()) / 255f;
                    this.colorG = (float) Color.green(fill.getColor()) / 255f;
                    this.colorB = (float) Color.blue(fill.getColor()) / 255f;
                    this.colorA = (float) Color.alpha(fill.getColor()) / 255f;
                } else if (style instanceof CompositeStyle) {
                    final CompositeStyle composite = (CompositeStyle) style;

                    // look up BasicFillStyle
                    style = CompositeStyle.find(composite,
                            BasicFillStyle.class);
                    // if found, re-run the loop
                    if (style != null)
                        continue;
                }

                // color has been derived from the style at this point, if
                // applicable
                break;
            } while (true);
        }

        @Override
        public void batch(GLMapView view, GLRenderBatch2 batch,
                int renderPass) {
            for (LineString ring : this.rings) {
                if (this.vertices == null || this.vertices
                        .capacity() < (3 * 2 * ring.getNumPoints())) {
                    ByteBuffer buf;

                    buf = ByteBuffer
                            .allocateDirect(2 * 3 * ring.getNumPoints() * 4);
                    buf.order(ByteOrder.nativeOrder());
                    this.vertices = buf.asFloatBuffer();
                    this.verticesPtr = Unsafe.getBufferPointer(this.vertices);
                }

                long pVerts;

                this.vertices.clear();
                pVerts = this.verticesPtr;

                // render the side faces of the polygon, the line string will always
                // have its first point as its last point to "close" the ring
                for (int i = 0; i < ring.getNumPoints(); i++) {
                    final double x = ring.getX(i);
                    final double y = ring.getY(i);

                    double baseElevation = view.getTerrainMeshElevation(y, x);
                    // if no terrain elevation is available, assume ellipsoid surface
                    if (Double.isNaN(baseElevation))
                        baseElevation = 0d;
                    // apply adjustments based on any configured offset and scale factor
                    baseElevation = (baseElevation + view.elevationOffset)
                            * view.elevationScaleFactor;

                    double z = ring.getZ(i) * view.elevationScaleFactor;

                    // compute and add the vertex
                    view.scratch.geo.set(y,
                            x,
                            z + baseElevation);
                    // convert the LLA coordinate to GL x,y,z
                    view.currentPass.scene.forward(view.scratch.geo, view.scratch.pointD);
                    // set the 3 float values at the pointer
                    Unsafe.setFloats(pVerts,
                            (float) view.scratch.pointD.x,
                            (float) view.scratch.pointD.y,
                            (float) view.scratch.pointD.z);
                    pVerts += 12;
                }
                // reset the limit on the buffer
                this.vertices.limit((int) ((pVerts - this.verticesPtr) / 4L));

                // XXX - at this time, the library does not have a 3D
                //       tessellation algorithm, as such, we are going to assume
                //       that all of the polygons are convex, in which case
                //       triangle fan rendering will be appropriate

                batch.batch(-1, // texture ID, not specified
                        GLES20FixedPipeline.GL_TRIANGLE_FAN, // mode
                        3, // number of elements per vertex coordinate
                        0, this.vertices, // vertex coordinates
                        0, null, // texture coordinates, not specified
                        this.colorR,
                        this.colorG,
                        this.colorB,
                        this.colorA);
            }
        }

        @Override
        public void draw(GLMapView view, int renderPass) {
            // we'll do some modifications to the GL state machine up front that
            // will be common to all drawing operations to follow

            // set the color for our polygons
            GLES20FixedPipeline.glColor4f(this.colorR,
                    this.colorG,
                    this.colorB,
                    this.colorA);

            // turn on alpha blending
            GLES20FixedPipeline.glEnable(GLES20FixedPipeline.GL_BLEND);
            GLES20FixedPipeline.glBlendFunc(GLES20FixedPipeline.GL_SRC_ALPHA,
                    GLES20FixedPipeline.GL_ONE_MINUS_SRC_ALPHA);

            // enable vertex arrays
            GLES20FixedPipeline
                    .glEnableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);

            // iterate and draw each polygon
            for (LineString ring : this.rings) {
                // ensure we have a vertex buffer with sufficient capacity
                if (this.vertices == null || this.vertices
                        .capacity() < (3 * 2 * ring.getNumPoints())) {
                    ByteBuffer buf;

                    buf = ByteBuffer
                            .allocateDirect(2 * 3 * ring.getNumPoints() * 4);
                    buf.order(ByteOrder.nativeOrder());
                    this.vertices = buf.asFloatBuffer();
                    this.verticesPtr = Unsafe.getBufferPointer(this.vertices);
                }

                long pVerts;

                this.vertices.clear();
                pVerts = this.verticesPtr;

                // render the faces of the volume. the line string will always
                // have its first point as its last point to "close" the ring,
                // so we will ignore it
                for (int i = 0; i < ring.getNumPoints() - 1; i++) {
                    final double x = ring.getX(i);
                    final double y = ring.getY(i);

                    double baseElevation = view.getTerrainMeshElevation(y, x);
                    // if no terrain elevation is available, assume ellipsoid surface
                    if (Double.isNaN(baseElevation))
                        baseElevation = 0d;
                    // apply adjustments based on any configured offset and scale factor
                    baseElevation = (baseElevation + view.elevationOffset)
                            * view.elevationScaleFactor;

                    double z = ring.getZ(i) * view.elevationScaleFactor;

                    // compute and add the vertex
                    view.scratch.geo.set(y,
                            x,
                            z + baseElevation);
                    // convert the LLA coordinate to GL x,y,z
                    view.currentPass.scene.forward(view.scratch.geo, view.scratch.pointD);
                    // set the 3 float values at the pointer
                    Unsafe.setFloats(pVerts,
                            (float) view.scratch.pointD.x,
                            (float) view.scratch.pointD.y,
                            (float) view.scratch.pointD.z);
                    pVerts += 12;
                }
                // reset the limit on the buffer
                this.vertices.limit((int) ((pVerts - this.verticesPtr) / 4L));

                // XXX - at this time, the library does not have a 3D
                //       tessellation algorithm, as such, we are going to assume
                //       that all of the polygons are convex, in which case
                //       triangle fan rendering will be appropriate

                GLES20FixedPipeline.glVertexPointer(3,
                        GLES20FixedPipeline.GL_FLOAT, 0, this.vertices);
                GLES20FixedPipeline.glDrawArrays(
                        GLES20FixedPipeline.GL_TRIANGLE_FAN, 0,
                        this.vertices.limit() / 3);

            }

            GLES20FixedPipeline
                    .glDisableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);
            GLES20FixedPipeline.glDisable(GLES20FixedPipeline.GL_BLEND);
        }

        @Override
        public void release() {
            if (this.vertices != null) {
                Unsafe.free(this.vertices);
                this.vertices = null;
                this.verticesPtr = 0L;
            }
        }

        @Override
        public int getRenderPass() {
            return GLMapView.RENDER_PASS_SPRITES;
        }
    }
}
