
package com.atakmap.android.hello3d;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.ShortBuffer;
import java.util.Collection;
import java.util.LinkedList;

import android.graphics.Color;
import android.util.Pair;

import com.atakmap.coremap.log.Log;

import com.atakmap.coremap.maps.coords.GeoPoint.AltitudeReference;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.lang.Unsafe;
import com.atakmap.map.MapRenderer;
import com.atakmap.map.layer.Layer;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.map.layer.opengl.GLAbstractLayer2;
import com.atakmap.map.layer.opengl.GLLayer2;
import com.atakmap.map.layer.opengl.GLLayerSpi2;
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.opengl.GLES20FixedPipeline;
import com.atakmap.opengl.GLTriangulate;

public class GLExtrudedPolygonsExample extends GLAbstractLayer2 {

    public final static GLLayerSpi2 SPI = new GLLayerSpi2() {

        @Override
        public int getPriority() {
            // ExtrudedPolygonsExample : Layer2
            return 1;
        }

        @Override
        public GLLayer2 create(Pair<MapRenderer, Layer> object) {
            final MapRenderer renderCtx = object.first;
            final Layer layer = object.second;

            if (!(layer instanceof ExtrudedPolygonsExample))
                return null;

            return new GLExtrudedPolygonsExample(renderCtx,
                    (ExtrudedPolygonsExample) layer);
        }

    };

    private final ExtrudedPolygonsExample subject;
    private Collection<Polygon> shapes;
    private float colorR;
    private float colorG;
    private float colorB;
    private float colorA;
    private FloatBuffer vertices;
    private long verticesPtr;
    private ShortBuffer indices;
    private long indicesPtr;

    public GLExtrudedPolygonsExample(MapRenderer surface,
            ExtrudedPolygonsExample subject) {
        super(surface, subject, GLMapView.RENDER_PASS_SPRITES);

        this.subject = subject;
        this.shapes = new LinkedList<Polygon>();
        this.colorR = 1f;
        this.colorG = 1f;
        this.colorB = 1f;
        this.colorA = 1f;
    }

    @Override
    public void start() {
        super.start();

        // capture the state of the subject
        final Collection<Polygon> polys = new LinkedList<Polygon>();
        polys.addAll(this.subject.getPolygons());
        final int color = this.subject.getColor();

        // update our copy of the state on the GL thread
        this.renderContext.queueEvent(new Runnable() {
            public void run() {
                shapes.clear();
                shapes.addAll(polys);

                colorR = (float) Color.red(color) / 255f;
                colorG = (float) Color.green(color) / 255f;
                colorB = (float) Color.blue(color) / 255f;
                colorA = (float) Color.alpha(color) / 255f;
            }
        });
    }

    @Override
    public void stop() {
        // reset our state on the GL thread
        this.renderContext.queueEvent(new Runnable() {
            public void run() {
                shapes.clear();
            }
        });

        super.stop();
    }

    @Override
    protected void drawImpl(GLMapView view, int renderPass) {
        GLES20FixedPipeline.glColor4f(this.colorR,
                this.colorG,
                this.colorB,
                this.colorA);
        GLES20FixedPipeline.glEnable(GLES20FixedPipeline.GL_BLEND);
        GLES20FixedPipeline.glBlendFunc(GLES20FixedPipeline.GL_SRC_ALPHA,
                GLES20FixedPipeline.GL_ONE_MINUS_SRC_ALPHA);
        for (Polygon p : shapes) {
            // get the exterior ring of the polygon
            LineString exterior = p.getExteriorRing();
            // obtain the render elevation at the center of the polygon 
            Envelope mbb = exterior.getEnvelope();
            double baseElevation = view.getTerrainMeshElevation(
                    (mbb.maxY + mbb.minY) / 2d, (mbb.maxX + mbb.minX) / 2d);
            // if no terrain elevation is available, assume ellipsoid surface
            if (Double.isNaN(baseElevation))
                baseElevation = 0d;
            // apply adjustments based on any configured offset and scale factor
            baseElevation = (baseElevation + view.elevationOffset)
                    * view.elevationScaleFactor;

            if (this.vertices == null || this.vertices
                    .capacity() < (3 * 2 * exterior.getNumPoints())) {
                ByteBuffer buf;

                buf = ByteBuffer
                        .allocateDirect(2 * 3 * exterior.getNumPoints() * 4);
                buf.order(ByteOrder.nativeOrder());
                this.vertices = buf.asFloatBuffer();
                this.verticesPtr = Unsafe.getBufferPointer(this.vertices);

                buf = ByteBuffer.allocateDirect(
                        ((exterior.getNumPoints() - 1) - 2) * 3 * 2);
                buf.order(ByteOrder.nativeOrder());
                this.indices = buf.asShortBuffer();
                this.indicesPtr = Unsafe.getBufferPointer(this.indices);
            }

            long pVerts;

            this.vertices.clear();
            pVerts = this.verticesPtr;

            // render the side faces of the polygon, the line string will always
            // have its first point as its last point to "close" the ring
            for (int i = 0; i < exterior.getNumPoints(); i++) {
                double z = exterior.getZ(i) * view.elevationScaleFactor;

                // vertex at the top of the extrusion
                view.scratch.geo.set(exterior.getY(i),
                        exterior.getX(i),
                        z + baseElevation);
                // convert the LLA coordinate to GL x,y,z
                view.currentPass.scene.forward(view.scratch.geo, view.scratch.pointD);
                // set the 3 float values at the pointer
                Unsafe.setFloats(pVerts,
                        (float) view.scratch.pointD.x,
                        (float) view.scratch.pointD.y,
                        (float) view.scratch.pointD.z);
                pVerts += 12;
                // vertex at the base of the extrusion
                view.scratch.geo.set(exterior.getY(i),
                        exterior.getX(i),
                        baseElevation);
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

            // add the side faces as a single triangle strip that winds around
            // the exterior of the polygon
            GLES20FixedPipeline
                    .glEnableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);
            GLES20FixedPipeline.glVertexPointer(3, GLES20FixedPipeline.GL_FLOAT,
                    0, this.vertices);
            GLES20FixedPipeline.glDrawArrays(
                    GLES20FixedPipeline.GL_TRIANGLE_STRIP, 0,
                    this.vertices.limit() / 3);
            GLES20FixedPipeline
                    .glDisableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);

            // render the top of the polygon
            this.vertices.clear();
            pVerts = this.verticesPtr;

            for (int i = 0; i < exterior.getNumPoints(); i++) {
                double z = exterior.getZ(i) * view.elevationScaleFactor;

                // vertex at the top of the extrusion
                view.scratch.geo.set(exterior.getY(i),
                        exterior.getX(i),
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

            this.indices.clear();
            switch (GLTriangulate.triangulate(this.vertices,
                    exterior.getNumPoints() - 1, this.indices)) {
                case GLTriangulate.INDEXED:
                    this.indices.flip();
                    GLES20FixedPipeline.glEnableClientState(
                            GLES20FixedPipeline.GL_VERTEX_ARRAY);
                    GLES20FixedPipeline.glVertexPointer(3,
                            GLES20FixedPipeline.GL_FLOAT, 0, this.vertices);
                    GLES20FixedPipeline.glDrawElements(
                            GLES20FixedPipeline.GL_TRIANGLES,
                            this.indices.limit(),
                            GLES20FixedPipeline.GL_UNSIGNED_SHORT,
                            this.indices);
                    GLES20FixedPipeline.glDisableClientState(
                            GLES20FixedPipeline.GL_VERTEX_ARRAY);
                    break;
                case GLTriangulate.TRIANGLE_FAN:
                    GLES20FixedPipeline.glEnableClientState(
                            GLES20FixedPipeline.GL_VERTEX_ARRAY);
                    GLES20FixedPipeline.glVertexPointer(3,
                            GLES20FixedPipeline.GL_FLOAT, 0, this.vertices);
                    GLES20FixedPipeline.glDrawArrays(
                            GLES20FixedPipeline.GL_TRIANGLE_FAN, 0,
                            this.vertices.limit() / 3);
                    GLES20FixedPipeline.glDisableClientState(
                            GLES20FixedPipeline.GL_VERTEX_ARRAY);
                    break;
                case GLTriangulate.STENCIL:
                    Log.w("GLExtrudedPolygonsExample",
                            "Stenciled non-surface polygon");
                    break;
                default:
                    throw new IllegalStateException();
            }
        }

        GLES20FixedPipeline.glDisable(GLES20FixedPipeline.GL_BLEND);
    }

    @Override
    public void release() {
        super.release();

        this.vertices = null;
        this.verticesPtr = 0L;

        this.indices = null;
        this.indicesPtr = 0L;
    }
}
