
package com.atakmap.android.hellobuildings.opengl;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.ShortBuffer;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

import com.atakmap.android.image.nitf.overlays.FreeformOverlay;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.lang.Unsafe;
import com.atakmap.map.MapSceneModel;
import com.atakmap.map.opengl.GLMapRenderable2;
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.math.MathUtils;
import com.atakmap.math.PointD;
import com.atakmap.math.Statistics;
import com.atakmap.opengl.GLES20FixedPipeline;

public class GLBuildingCacheBatch implements GLMapRenderable2, Runnable {
    Collection<GLExtrudingPolygon> polys;
    List<CachePage> cache = new ArrayList<CachePage>();
    Collection<GLExtrudingPolygon> uncacheable;
    boolean dirty = true;

    short[] idxTransfer;

    Statistics stats = new Statistics();

    AtomicBoolean servicingRequest = new AtomicBoolean(false);
    CacheRequest cacheRequest;

    boolean wireFrame = true;
    boolean textured = false;

    Thread worker;

    Collection<int[]> freeVbos = new LinkedList<int[]>();

    public synchronized void release() {
        for (CachePage page : cache)
            page.dispose();
        cache.clear();

        if (!freeVbos.isEmpty()) {
            int[] freeList = new int[freeVbos.size()];
            int i = 0;
            for (int[] vbo : freeVbos)
                freeList[i++] = vbo[0];
            GLES20FixedPipeline.glDeleteBuffers(i, freeList, 0);
            freeVbos.clear();
        }

        this.uncacheable = null;
        this.idxTransfer = null;

        wireFrame = true;
        textured = true;

        this.worker = null;
        this.notify();
    }

    public void draw(GLMapView view, int renderPass) {
        PointD lcsOrigin = new PointD(0d, 0d, 0d);
        view.scratch.geo.set(view.drawLat, view.drawLng);
        view.scratch.geo.set(GeoPoint.UNKNOWN);
        view.scene.mapProjection.forward(view.scratch.geo, lcsOrigin);

        final int terrainVersion = view.terrain.getTerrainVersion();

        synchronized (this) {
            for (CachePage page : cache) {
                if (page.srid != view.drawSrid ||
                        page.terrainVersion != terrainVersion) {
                    this.dirty = true;
                    break;
                }
            }

            if (this.dirty) {
                // XXX - experiment with some mechanism that "triggers" a
                //       request to be issued, but waits for a couple of frames
                //       to attempt to better sync what's being constructed
                //       against the current viewport. what currently happens is
                //       that a request is issued as soon as the map begins to
                //       move, then another one as soon as it completes (and so
                //       on) until the last one reflects the current view.

                // while rendering the pre-constructed pages is very fast,
                // constructing them cannot be done in frame rate time. instead,
                // we'll issue requests for the pages we want built to a
                // background thread which will do the work for us.
                if (this.cacheRequest == null)
                    this.cacheRequest = new CacheRequest();

                if (this.worker == null) {
                    this.worker = new Thread(this);
                    this.worker.setName("GLBuildingCacheBatch-worker@"
                            + Integer.toString(this.hashCode(), 16));
                    this.worker.setPriority(Thread.NORM_PRIORITY);
                    this.worker.start();
                }

                this.cacheRequest.polys = new ArrayList<GLExtrudingPolygon>(
                        this.polys);
                this.cacheRequest.terrainVersion = terrainVersion;
                this.cacheRequest.scene = view.scene;
                this.cacheRequest.view = view;
                this.cacheRequest.lcs = new LocalCoordinateSystem();
                LocalCoordinateSystem.deriveFrom(view.scene, lcsOrigin,
                        this.cacheRequest.lcs);
                this.notify();

                this.dirty = false;
            }

            if (!freeVbos.isEmpty()) {
                int[] freeList = new int[freeVbos.size()];
                int i = 0;
                for (int[] vbo : freeVbos)
                    freeList[i++] = vbo[0];
                GLES20FixedPipeline.glDeleteBuffers(i, freeList, 0);
                freeVbos.clear();
            }

            if (this.cache.isEmpty())
                return;

            GLES20FixedPipeline.glEnable(GLES20FixedPipeline.GL_BLEND);
            GLES20FixedPipeline.glBlendFunc(GLES20FixedPipeline.GL_SRC_ALPHA,
                    GLES20FixedPipeline.GL_ONE_MINUS_SRC_ALPHA);

            GLES20FixedPipeline.glPushMatrix();

            GLES20FixedPipeline.glLineWidth(2f);

            // upload the volume vertices and render via drawElements
            GLES20FixedPipeline
                    .glEnableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);
            for (CachePage page : cache) {
                // the page is invalid, skip it
                if (page.srid != view.drawSrid)
                    continue;

                // NOTE: since we're loading the matrix, no need to push
                if (page.lcs == null) {
                    GLES20FixedPipeline
                            .glLoadMatrixf(view.sceneModelForwardMatrix, 0);
                } else {
                    LocalCoordinateSystem.deriveFrom(view.scene,
                            page.lcs.origin, page.lcs);
                    GLES20FixedPipeline.glLoadMatrixf(page.lcs.forwardF, 0);
                }

                // translation and scale for altitude values
                GLES20FixedPipeline.glScalef(1f, 1f,
                        (float) view.elevationScaleFactor);
                GLES20FixedPipeline.glTranslatef(0f, 0f,
                        (float) view.elevationOffset);

                if (page.vbo == null) {
                    // generate the VBO
                    page.vbo = new int[1];
                    GLES20FixedPipeline.glGenBuffers(1, page.vbo, 0);

                    // bind the VBO
                    GLES20FixedPipeline.glBindBuffer(
                            GLES20FixedPipeline.GL_ARRAY_BUFFER, page.vbo[0]);

                    // upload the buffer data as static
                    GLES20FixedPipeline.glBufferData(
                            GLES20FixedPipeline.GL_ARRAY_BUFFER,
                            page.vertices.capacity() * 4,
                            page.vertices,
                            GLES20FixedPipeline.GL_STATIC_DRAW);

                    // free the vertex array
                    Unsafe.free(page.vertices);
                    page.vertices = null;
                } else {
                    // bind the VBO
                    GLES20FixedPipeline.glBindBuffer(
                            GLES20FixedPipeline.GL_ARRAY_BUFFER, page.vbo[0]);
                }

                GLES20FixedPipeline.glVertexPointer(3,
                        GLES20FixedPipeline.GL_FLOAT, 0, 0);

                if (wireFrame && MathUtils.hasBits(renderPass,
                        GLMapView.RENDER_PASS_SPRITES)) {
                    GLES20FixedPipeline.glColor4f(page.r, page.g, page.b, 1f);
                    GLES20FixedPipeline.glDrawElements(
                            GLES20FixedPipeline.GL_LINES,
                            page.frameIndices.limit(),
                            GLES20FixedPipeline.GL_UNSIGNED_SHORT,
                            page.frameIndices);
                }
                if (textured && renderPass == GLMapView.RENDER_PASS_SPRITES) {
                    GLES20FixedPipeline.glColor4f(page.r, page.g, page.b,
                            page.a);
                    GLES20FixedPipeline.glDrawElements(
                            GLES20FixedPipeline.GL_TRIANGLES,
                            page.volumeIndices.limit(),
                            GLES20FixedPipeline.GL_UNSIGNED_SHORT,
                            page.volumeIndices);
                }

                GLES20FixedPipeline
                        .glBindBuffer(GLES20FixedPipeline.GL_ARRAY_BUFFER, 0);
            }
            GLES20FixedPipeline
                    .glDisableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);

            GLES20FixedPipeline.glPopMatrix();

            GLES20FixedPipeline.glDisable(GLES20FixedPipeline.GL_BLEND);
        }
    }

    @Override
    public int getRenderPass() {
        // content for this renderable should only be drawn during a "sprites"
        // pass
        return GLMapView.RENDER_PASS_SPRITES | GLMapView.RENDER_PASS_SURFACE;
    }

    @Override
    public void run() {
        CacheRequest filling = null;
        while (true) {
            synchronized (this) {
                if (this.worker == null) {
                    if (filling != null) {
                        for (CachePage page : filling.result)
                            page.dispose();
                        filling.result.clear();
                        filling = null;
                    }
                    break;
                }

                if (filling != null) {
                    // flip the pages buffers
                    for (CachePage page : cache)
                        page.dispose();
                    cache.clear();

                    this.cache.addAll(filling.result);
                    filling = null;
                }

                if (this.cacheRequest == null) {
                    try {
                        this.wait();
                    } catch (InterruptedException ignored) {
                    }
                    continue;
                }
                filling = this.cacheRequest;
                this.cacheRequest = null;
                this.servicingRequest.set(true);
            }

            long s = System.currentTimeMillis();

            // create cache pages
            if (!filling.polys.isEmpty()) {
                CachePage page = new CachePage();
                page.terrainVersion = filling.terrainVersion;
                page.srid = filling.scene.mapProjection.getSpatialReferenceID();
                page.lcs = filling.lcs;
                for (GLExtrudingPolygon p : filling.polys) {
                    // XXX - we have some additional synchronization occurring
                    //       here that is a side effect of having the upstream
                    //       layer be an example, showing several different ways
                    //       the content could be rendered. Were this production
                    //       code, the renderer would be structured such that
                    //       the GLExtrudingPolygon instances were managed by
                    //       this object, and would be done so in a manner that

                    // validate the polygon vertices
                    synchronized (p) {
                        if (filling.lcs == null) {
                            if (!p.validateAsync(filling.view, filling.scene,
                                    filling.terrainVersion))
                                continue;
                        } else {
                            if (!p.validateAsync(filling.view, filling.lcs,
                                    filling.terrainVersion))
                                continue;
                        }

                        do {
                            // XXX - should be handling color more robustly -- split
                            //       similarly colored polys into color specific
                            //       pages
                            page.r = p.r;
                            page.g = p.g;
                            page.b = p.b;
                            page.a = p.a;

                            // XXX - handle case where vertex count makes polygon
                            //       unpageable
                            if (!page.add(p)) {
                                page.cache(filling.result);

                                page = new CachePage();
                                page.terrainVersion = filling.terrainVersion;
                                page.srid = filling.scene.mapProjection
                                        .getSpatialReferenceID();
                                page.lcs = filling.lcs;
                                continue;
                            }
                            break;
                        } while (true);
                    }
                }

                if (page.volumeIdxPos > 0)
                    page.cache(filling.result);

                long e = System.currentTimeMillis();
                if (!polys.isEmpty()) {
                    stats.observe(e - s);
                    System.out.println("Constructed " + filling.result.size()
                            + " pages for " + filling.polys.size()
                            + " polys in " + (e - s) + "ms (avg "
                            + (long) (stats.mean) + "ms)");
                }
            }
        }
    }

    private static class CacheRequest {
        LocalCoordinateSystem lcs;
        GLMapView view;
        MapSceneModel scene;
        int terrainVersion;
        Collection<GLExtrudingPolygon> polys;

        List<CachePage> result = new ArrayList<CachePage>(3);
    }

    private class CachePage {
        FloatBuffer vertices;
        private long verticesPtr;
        ShortBuffer volumeIndices;
        private long volumeIndicesPtr;
        ShortBuffer frameIndices;
        private long frameIndicesPtr;

        private int vertexCount;
        LocalCoordinateSystem lcs;
        int terrainVersion;
        int srid;
        float r;
        float g;
        float b;
        float a;

        int[] vbo;

        private int volumeIdxPos;
        private int frameIdxPos;

        CachePage() {
            ByteBuffer buf;

            buf = Unsafe.allocateDirect(0xFFFF * 12);
            buf.order(ByteOrder.nativeOrder());
            this.vertices = buf.asFloatBuffer();
            this.verticesPtr = Unsafe.getBufferPointer(this.vertices);

            buf = Unsafe.allocateDirect(0xFFFF / 4 * 48 * 2);
            buf.order(ByteOrder.nativeOrder());
            this.volumeIndices = buf.asShortBuffer();
            this.volumeIndicesPtr = Unsafe.getBufferPointer(this.volumeIndices);
            this.volumeIdxPos = 0;

            buf = Unsafe.allocateDirect(0xFFFF / 4 * 48 * 2);
            buf.order(ByteOrder.nativeOrder());
            this.frameIndices = buf.asShortBuffer();
            this.frameIndicesPtr = Unsafe.getBufferPointer(this.frameIndices);
            this.frameIdxPos = 0;

            this.vertexCount = 0;

            terrainVersion = -1;
            srid = -1;
            r = 1f;
            g = 1f;
            b = 1f;
            a = 1f;

            if (idxTransfer == null
                    || idxTransfer.length < this.volumeIndices.capacity())
                idxTransfer = new short[this.volumeIndices.capacity()];

        }

        boolean add(GLExtrudingPolygon poly) {
            final int numVertices = poly.vertices.limit() / 3;
            if (vertexCount + numVertices > 0xFFFF)
                return false;
            final int numVolumeIndices = poly.indices.limit();
            if (numVolumeIndices > (idxTransfer.length - volumeIdxPos))
                return false;
            final int numPoints = poly.subject.getNumPoints();
            final int numFrameIndices = numPoints * 6;
            if (numFrameIndices > (frameIndices.capacity() - frameIdxPos))
                return false;

            final long src = poly.verticesPtr;
            final long dst = this.verticesPtr + (12 * vertexCount);

            Unsafe.memcpy(dst, src, numVertices * 12);

            // XXX - the transfer for the indices is really slow. the fastest
            //       method readily available through experimentation is to
            //       populate a short array and transfer it in one put operation
            //       to the direct buffer. look to implementing JNI code to
            //       handle as it should be significantly faster

            // retrieve the indices from the polygon
            poly.indices.get(idxTransfer, volumeIdxPos, numVolumeIndices);
            poly.indices.position(0);
            // copy those indices to our index buffer, adjusting for vertex
            // count 
            for (int i = 0; i < numVolumeIndices; i++)
                idxTransfer[i + volumeIdxPos] += (short) vertexCount;
            volumeIdxPos += numVolumeIndices;

            // the polygon should be defined by a closed line loop

            // top
            for (int i = 0; i < numPoints - 1; i++) {
                Unsafe.setShorts(frameIndicesPtr + (frameIdxPos * 2),
                        (short) (vertexCount + (i % (numPoints - 1))),
                        (short) (vertexCount + ((i + 1) % (numPoints - 1))));
                frameIdxPos += 2;
            }
            // bottom
            for (int i = 0; i < numPoints - 1; i++) {
                Unsafe.setShorts(frameIndicesPtr + (frameIdxPos * 2),
                        (short) (vertexCount + (numVertices / 2)
                                + (i % (numPoints - 1))),
                        (short) (vertexCount + (numVertices / 2)
                                + ((i + 1) % (numPoints - 1))));
                frameIdxPos += 2;
            }
            // sides
            for (int i = 0; i < numPoints - 1; i++) {
                Unsafe.setShorts(frameIndicesPtr + (frameIdxPos * 2),
                        (short) (vertexCount + i),
                        (short) (vertexCount + (numVertices / 2) + i));
                frameIdxPos += 2;
            }

            this.vertexCount += numVertices;

            return true;
        }

        /**
         * Closes the page from further additions and adds to the cache.
         */
        void cache(List<CachePage> cache) {
            // transfer the index array to the direct buffer
            Unsafe.put(this.volumeIndices, idxTransfer, 0, volumeIdxPos);
            // flip the buffer
            this.volumeIndices.flip();

            this.frameIndices.clear();
            this.frameIndices.limit(this.frameIdxPos);

            // add this page to the cache
            cache.add(this);
        }

        void dispose() {
            if (this.vertices != null)
                Unsafe.free(this.vertices);
            this.verticesPtr = 0L;
            Unsafe.free(this.volumeIndices);
            this.volumeIndicesPtr = 0L;

            if (vbo != null) {
                freeVbos.add(vbo);
                vbo = null;
            }
        }
    }
}
