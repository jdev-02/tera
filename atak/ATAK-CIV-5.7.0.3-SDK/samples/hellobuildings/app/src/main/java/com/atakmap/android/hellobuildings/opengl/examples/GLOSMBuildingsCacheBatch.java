
package com.atakmap.android.hellobuildings.opengl.examples;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.Map;

import android.graphics.Color;
import android.util.Pair;

import com.atakmap.android.hellobuildings.BuildingsExample;
import com.atakmap.map.MapRenderer;
import com.atakmap.map.layer.Layer;
import com.atakmap.map.layer.feature.AttributeSet;
import com.atakmap.map.layer.feature.DataStoreException;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureCursor;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.FeatureDefinition2;
import com.atakmap.map.layer.feature.style.Style;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.GeometryFactory;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.map.layer.feature.style.BasicFillStyle;
import com.atakmap.map.layer.feature.style.CompositeStyle;
import com.atakmap.map.layer.opengl.GLAsynchronousLayer2;
import com.atakmap.map.layer.opengl.GLLayer2;
import com.atakmap.map.layer.opengl.GLLayerSpi2;
import com.atakmap.map.opengl.GLMapRenderable2;
import com.atakmap.map.opengl.GLMapView;

public class GLOSMBuildingsCacheBatch
        extends GLAsynchronousLayer2<Collection<Feature>>
        implements FeatureDataStore2.OnDataStoreContentChangedListener,
        Layer.OnLayerVisibleChangedListener {

    public final static GLLayerSpi2 SPI = new GLLayerSpi2() {
        @Override
        public int getPriority() {
            // BuildingsExample : Layer2
            return 1;
        }

        @Override
        public GLLayer2 create(Pair<MapRenderer, Layer> object) {
            final MapRenderer renderCtx = object.first;
            final Layer layer = object.second;

            if (!(layer instanceof BuildingsExample))
                return null;

            return new GLOSMBuildingsCacheBatch(renderCtx,
                    (BuildingsExample) layer);
        }
    };

    /**************************************************************************/

    private FeatureDataStore2 dataStore;
    private Map<Long, GLExtrudingPolygon> renderables;
    private Collection<? extends GLMapRenderable2> renderList;
    private GLBuildingCacheBatch cacheBatchRenderer;
    private boolean visible;

    public GLOSMBuildingsCacheBatch(MapRenderer surface,
            BuildingsExample subject) {
        super(surface, subject);

        this.dataStore = subject.getDataStore();
        this.renderables = new HashMap<Long, GLExtrudingPolygon>();

        this.cacheBatchRenderer = new GLBuildingCacheBatch();
        this.cacheBatchRenderer.polys = this.renderables.values();

        this.renderList = Collections.singleton(cacheBatchRenderer);
    }

    @Override
    public void start() {
        // start is invoked to signal to the renderer that it may interact with
        // its underlying subject to obtain content for rendering. when the
        // renderable is not in the started state, it should not access its
        // subject, but may continue to render any content that it has
        // previously computed

        // register the renderable on the subject to receive events, and record
        // the initial visibility state
        this.dataStore.addOnDataStoreContentChangedListener(this);
        this.subject.addOnLayerVisibleChangedListener(this);
        this.visible = this.subject.isVisible();

        super.start();
    }

    @Override
    public void stop() {
        // stop is invoked to signal to the renderer that it must cease any
        // interaction with its underlying subject. while in the stopped state,
        // this renderbale may continue to render any content that it has
        // previously computed

        // unregister the renderable on the subject from receiving events from
        // the subject
        this.dataStore.removeOnDataStoreContentChangedListener(this);
        this.subject.removeOnLayerVisibleChangedListener(this);
        super.stop();
    }

    @Override
    public void draw(GLMapView view, int renderPass) {
        // XXX - workaround for a bug in the base class -- GLAsynchronousLayer2
        //       should be managing subject visibility and return without
        //       drawing if layer is not visible
        if (!this.visible)
            return;

        super.draw(view, renderPass);
    }

    @Override
    public int getRenderPass() {
        // content for this renderable should only be drawn during a "sprites"
        // pass
        return GLMapView.RENDER_PASS_SPRITES;
    }

    @Override
    protected Collection<? extends GLMapRenderable2> getRenderList() {
        // return the content that we want drawn during the draw pump.
        // Implementations generally specify the render list as aither a
        // collection of renderables, or a single renderable that collects other
        // renderables (e.g. a batch renderer). The content for the render list
        // should be updated in the method, 'updateRenderList(...)'
        return this.renderList;
    }

    @Override
    protected void resetPendingData(Collection<Feature> pendingData) {
        // resets the context used to store the query results
        pendingData.clear();
    }

    @Override
    protected void releasePendingData(Collection<Feature> pendingData) {
        // releases the context used to store the query results
        pendingData.clear();
    }

    @Override
    protected Collection<Feature> createPendingData() {
        // creates a context to be used to store the query results
        return new LinkedList<Feature>();
    }

    @Override
    protected boolean updateRenderList(
            ViewState state,
            Collection<Feature> pendingData) {

        // we will update the render list based on the results of the previous
        // query
        final Map<Long, GLExtrudingPolygon> toRelease = new HashMap<Long, GLExtrudingPolygon>(
                this.renderables);
        renderables.clear();
        for (Feature f : pendingData) {
            GLExtrudingPolygon renderer = toRelease.remove(f.getId());
            if (renderer == null) {
                int color = Color.WHITE;
                Style s = f.getStyle();
                if (s instanceof CompositeStyle)
                    s = CompositeStyle.find((CompositeStyle) s,
                            BasicFillStyle.class);
                if (s instanceof BasicFillStyle)
                    color = ((BasicFillStyle) s).getColor();
                renderer = new GLExtrudingPolygon((Polygon) f.getGeometry(),
                        color);
            } else {
                // XXX - check version and update renderable if necessary
            }
            renderables.put(f.getId(), renderer);
        }

        if (!toRelease.isEmpty()) {
            this.renderContext.queueEvent(new Runnable() {
                public void run() {
                    for (GLMapRenderable2 r : toRelease.values())
                        r.release();
                }
            });
        }

        // for 'cache batch' rendering, we need to let the renderer know that
        // its cache is dirty. all other rendering strategies process the
        // content on every render pump, so there is no need for such mechanism
        this.cacheBatchRenderer.dirty = true;

        // return 'true' to indicate that the update operation was successful.
        // In the event that it was determined that the results should not be
        // considered valid, 'false', may be returned which will force another
        // query to occur immediately.
        return true;
    }

    @Override
    protected void query(ViewState state,
            Collection<Feature> result) {

        // perform the query on the background worker thread -- if the view
        // spans the Anti-Meridian, split it into two separate queries
        if (state.crossesIDL) {
            // west of IDL
            this.queryImpl(state.northBound,
                    state.westBound,
                    state.southBound,
                    180d,
                    state.drawMapResolution,
                    result);

            // east of IDL
            this.queryImpl(state.northBound,
                    -180d,
                    state.southBound,
                    state.eastBound,
                    state.drawMapResolution,
                    result);
        } else {
            this.queryImpl(state.northBound,
                    state.westBound,
                    state.southBound,
                    state.eastBound,
                    state.drawMapResolution,
                    result);
        }
    }

    private void queryImpl(double northBound,
            double westBound,
            double southBound,
            double eastBound,
            double drawMapResolution,
            Collection<Feature> retval) {

        // query the data store for the current AOI and map resolution
        FeatureCursor result = null;
        try {
            FeatureDataStore2.FeatureQueryParameters params = new FeatureDataStore2.FeatureQueryParameters();
            params.spatialFilter = GeometryFactory.fromEnvelope(new Envelope(
                    westBound, southBound, 0d, eastBound, northBound, 0d));
            params.featureSetFilter = new FeatureDataStore2.FeatureSetQueryParameters();
            params.featureSetFilter.maxResolution = drawMapResolution;
            params.visibleOnly = true;
            params.ignoredFeatureProperties = FeatureDataStore2.PROPERTY_FEATURE_ATTRIBUTES;

            // check if the query thread has been aborted and do an early return
            if (this.checkQueryThreadAbort())
                return;

            result = this.dataStore.queryFeatures(params);
            while (result.moveToNext()) {
                // check if the query thread has been aborted and do an early
                // return
                if (this.checkQueryThreadAbort())
                    break;
                // obtain the feature
                Feature f = result.get();
                // ensure the feature is a polygon, and add it to the query
                // results context
                if (f.getGeometry() instanceof Polygon)
                    retval.add(f);
            }
        } catch (DataStoreException e) {
        } finally {
            if (result != null)
                result.close();
        }
    }

    @Override
    public void onDataStoreContentChanged(FeatureDataStore2 dataStore) {
        // we've received notification that the data store content is changed.
        // dispatch invalidation which will initiate a new content query
        this.invalidateNoSync();
    }

    @Override
    public void onFeatureInserted(FeatureDataStore2 dataStore, long fid,
            FeatureDefinition2 def,
            long version) {
        // we've received notification that the data store content is changed.
        // dispatch invalidation which will initiate a new content query
        this.invalidateNoSync();
    }

    @Override
    public void onFeatureUpdated(FeatureDataStore2 dataStore, long fid,
            int modificationMask,
            String name, Geometry geom, Style style, AttributeSet attribs,
            int attribsUpdateType) {

        // we've received notification that the data store content is changed.
        // dispatch invalidation which will initiate a new content query
        this.invalidateNoSync();
    }

    @Override
    public void onFeatureDeleted(FeatureDataStore2 dataStore, long fid) {
        // we've received notification that the data store content is changed.
        // dispatch invalidation which will initiate a new content query
        this.invalidateNoSync();
    }

    @Override
    public void onFeatureVisibilityChanged(FeatureDataStore2 dataStore,
            long fid, boolean visible) {
        // we've received notification that the data store content is changed.
        // dispatch invalidation which will initiate a new content query
        this.invalidateNoSync();
    }

    @Override
    public void onLayerVisibleChanged(Layer layer) {
        // update the visibility state
        this.visible = layer.isVisible();
    }
}
