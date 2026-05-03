
package com.atakmap.android.hellobuildings.opengl.examples;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.DoubleBuffer;
import java.nio.FloatBuffer;
import java.nio.ShortBuffer;

import android.graphics.Color;


import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPoint.AltitudeReference;


import com.atakmap.lang.Unsafe;
import com.atakmap.map.MapSceneModel;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.map.layer.feature.geometry.opengl.GLGeometry;
import com.atakmap.map.opengl.GLMapRenderable2;
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.math.MathUtils;
import com.atakmap.math.PointD;
import com.atakmap.opengl.GLES20FixedPipeline;

public class GLExtrudingPolygon implements GLMapRenderable2 {

    /** the exterior ring of the polygon */
    private LineString subject;
    /** the minimum bounding box of the polygon */
    private Envelope subjectMbb;
    /**
     * direct buffer of the building volume vertices
     */
    private DoubleBuffer points;
    /** the pointer to the memory address of the points buffer */
    private long pointsPtr;
    FloatBuffer vertices;
    /** the pointer to the memory address of the vertices buffer */
    long verticesPtr;
    /**
     * The version of the vertex buffer content. When <code>vertexType</code>
     * is {@link GLGeometry#VERTICES_PIXEL}, this value should be compared with
     * {@link GLMapView#drawVersion}; when <code>vertexType</code> is
     * {@link GLGeometry#VERTICES_PROJECTED}, this value should be compared with
     * {@link GLMapView#drawSrid}.
     */
    private int verticesVersion;
    /**
     * The current coordinate space of the vertices. One of:
     * <UL>
     *  <LI>{@link GLGeometry#VERTICES_PIXEL</LI>
     *  <LI>{@link GLGeometry#VERTICES_PROJECTED</LI>
     * </UL>
     */
    private int vertexType;
    private boolean vertexHasBaseEl;
    /** the render indices for the polygon */
    ShortBuffer indices;
    /** the pointer to the memory address of the indices buffer */
    long indicesPtr;
    /** the base elevation for the polygon, derived from the terrain */
    private double baseElevation;
    /** the terrain version associated with the base elevation */
    private int baseElevationVersion;
    /** the feature version that the renderable's state reflects */
    long version;
    /** render red color component */
    float r;
    /** render green color component */
    float g;
    /** render blue color component */
    float b;
    /** render alpha color component */
    float a;

    public GLExtrudingPolygon(Polygon subject, int color) {
        this.subject = subject.getExteriorRing();
        this.subjectMbb = this.subject.getEnvelope();

        this.points = null;
        this.pointsPtr = 0L;
        this.vertices = null;
        this.verticesPtr = 0L;
        this.indices = null;
        this.indicesPtr = 0L;
        this.baseElevationVersion = -1;

        this.r = Color.red(color) / 255f;
        this.g = Color.green(color) / 255f;
        this.b = Color.blue(color) / 255f;
        this.a = Color.alpha(color) / 255f;
    }

    private boolean drawCommon() {
        final int numPoints = this.subject.getNumPoints();
        final int vertexCount = numPoints - 1;
        if (vertexCount < 4)
            return false;

        if (this.points == null
                || (this.points.capacity() < (3 * 2 * vertexCount))) {
            ByteBuffer buf;

            buf = Unsafe.allocateDirect(3 * 2 * vertexCount * 8);
            buf.order(ByteOrder.nativeOrder());
            this.points = buf.asDoubleBuffer();
            this.pointsPtr = Unsafe.getBufferPointer(this.points);

            buf = Unsafe.allocateDirect(
                    ((vertexCount * 6) + ((vertexCount - 2) * 3)) * 2);
            buf.order(ByteOrder.nativeOrder());
            this.indices = buf.asShortBuffer();
            this.indicesPtr = Unsafe.getBufferPointer(this.indices);

            long topPtr = pointsPtr;
            long bottomPtr = topPtr + (vertexCount * 3 * 8);
            long indexPtr = this.indicesPtr;
            for (int i = 0; i < vertexCount; i++) {
                final double x = this.subject.getX(i);
                final double y = this.subject.getY(i);
                final double z = this.subject.getZ(i);

                // add the vertex to the top of the extrusion
                Unsafe.setDoubles(topPtr, x, y, z);
                topPtr += 3 * 8;
                // add the vertex to tbe base of the extrusion
                Unsafe.setDoubles(bottomPtr, x, y, 0d);
                bottomPtr += 3 * 8;

                // emit a face
                if (i > 0) {
                    Unsafe.setShorts(indexPtr,
                            (short) (i - 1),
                            (short) (vertexCount + i - 1),
                            (short) i);
                    indexPtr += 6;
                    Unsafe.setShorts(indexPtr,
                            (short) (vertexCount + i - 1),
                            (short) i,
                            (short) (vertexCount + i));
                    indexPtr += 6;
                }
            }

            // join last edge to first edge
            Unsafe.setShorts(indexPtr,
                    (short) (vertexCount - 1),
                    (short) (vertexCount + vertexCount - 1),
                    (short) 0);
            indexPtr += 6;
            Unsafe.setShorts(indexPtr,
                    (short) (vertexCount + vertexCount - 1),
                    (short) 0,
                    (short) vertexCount);
            indexPtr += 6;

            // create the top
            // XXX - using triangle fan, look into tessellation
            for (int i = 2; i < vertexCount; i++) {
                Unsafe.setShorts(indexPtr,
                        (short) 0,
                        (short) (i - 1),
                        (short) i);
                indexPtr += 6;
            }
        }

        if (this.vertices == null
                || this.vertices.capacity() < (3 * 2 * vertexCount)) {
            ByteBuffer buf;

            buf = Unsafe.allocateDirect(2 * 3 * vertexCount * 4);
            buf.order(ByteOrder.nativeOrder());
            this.vertices = buf.asFloatBuffer();
            this.verticesPtr = Unsafe.getBufferPointer(this.vertices);
        }

        return true;
    }

    @Override
    public void draw(GLMapView view, int renderPass) {
        if (!MathUtils.hasBits(renderPass, this.getRenderPass()))
            return;

        if (!this.drawCommon())
            return;

        // turn on blending
        GLES20FixedPipeline.glEnable(GLES20FixedPipeline.GL_BLEND);
        GLES20FixedPipeline.glBlendFunc(GLES20FixedPipeline.GL_SRC_ALPHA,
                GLES20FixedPipeline.GL_ONE_MINUS_SRC_ALPHA);

        // set the color
        GLES20FixedPipeline.glColor4f(this.r, this.g, this.b, this.a);

        // draw the vertex data
        if (view.hardwareTransformResolutionThreshold > view.drawMapResolution)
            drawGeneric(view);
        else
            drawProjected(view);

        GLES20FixedPipeline.glDisable(GLES20FixedPipeline.GL_BLEND);
    }

    private void drawGeneric(GLMapView view) {
        final int numPoints = this.subject.getNumPoints();
        final int vertexCount = numPoints - 1;
        if (vertexCount < 4)
            return;

        // validate the vertices and base elevation for the render pump
        if (!this.validate(view,
                GLGeometry.VERTICES_PIXEL,
                view.terrain.getTerrainVersion(),
                true)) {

            return;
        }

        // render the exterior faces of the extruded polygon
        GLES20FixedPipeline
                .glEnableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);
        GLES20FixedPipeline.glVertexPointer(3, GLES20FixedPipeline.GL_FLOAT, 0,
                this.vertices);
        GLES20FixedPipeline.glDrawElements(GLES20FixedPipeline.GL_TRIANGLES,
                this.indices.limit(), GLES20FixedPipeline.GL_UNSIGNED_SHORT,
                this.indices);
        GLES20FixedPipeline
                .glDisableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);
    }

    private void drawProjected(GLMapView view) {
        final int numPoints = this.subject.getNumPoints();
        final int vertexCount = numPoints - 1;
        if (vertexCount < 4)
            return;

        // validate the vertices and base elevation for the render pump
        if (!this.validate(view,
                GLGeometry.VERTICES_PROJECTED,
                view.terrain.getTerrainVersion(),
                false)) {

            return;
        }

        GLES20FixedPipeline.glPushMatrix();
        GLES20FixedPipeline.glLoadMatrixf(view.sceneModelForwardMatrix, 0);

        // translation and scale for altitude values
        GLES20FixedPipeline.glScalef(1f, 1f, (float) view.elevationScaleFactor);
        GLES20FixedPipeline.glTranslatef(0f, 0f,
                (float) (baseElevation + view.elevationOffset));

        // upload the volume vertices and render via drawElements
        GLES20FixedPipeline
                .glEnableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);
        GLES20FixedPipeline.glVertexPointer(3, GLES20FixedPipeline.GL_FLOAT, 0,
                this.vertices);
        GLES20FixedPipeline.glDrawElements(GLES20FixedPipeline.GL_TRIANGLES,
                this.indices.limit(), GLES20FixedPipeline.GL_UNSIGNED_SHORT,
                this.indices);
        GLES20FixedPipeline
                .glDisableClientState(GLES20FixedPipeline.GL_VERTEX_ARRAY);

        GLES20FixedPipeline.glPopMatrix();
    }

    @Override
    public synchronized void release() {
        if (this.points != null) {
            Unsafe.free(this.points);
            this.points = null;
            this.pointsPtr = 0L;
        }
        if (this.vertices != null) {
            Unsafe.free(this.vertices);
            this.vertices = null;
            this.verticesPtr = 0L;
        }
        if (this.indices != null) {
            Unsafe.free(this.indices);
            this.indices = null;
            this.indicesPtr = 0L;
        }
    }

    @Override
    public int getRenderPass() {
        return GLMapView.RENDER_PASS_SPRITES;
    }

    boolean validate(GLMapView view, int vertices, int terrainVersion) {
        return validate(view, vertices, terrainVersion, true);
    }

    synchronized boolean validateAsync(GLMapView view, MapSceneModel sceneModel,
            int terrainVersion) {
        if (!this.drawCommon())
            return false;

        final int numPoints = this.points.limit() / 3;
        if (this.points == null || numPoints < 3)
            return false;

        if (this.baseElevationVersion != terrainVersion) {
            double v = view.getElevation(
                    (this.subjectMbb.maxY + this.subjectMbb.minY) / 2d,
                    (this.subjectMbb.maxX + this.subjectMbb.minX) / 2d);
            // if no terrain elevation is available, assume ellipsoid surface
            if (!GeoPoint.isAltitudeValid(v))
                v = 0d;
            this.baseElevationVersion = terrainVersion;

            // the base elevation has changed, vertices must be rebuilt
            if (this.baseElevation != v) {
                this.verticesVersion = ~this.verticesVersion;
            }
            this.baseElevation = v;
        }

        final int srid = sceneModel.mapProjection.getSpatialReferenceID();

        // project the vertices
        if (srid != this.verticesVersion ||
                this.vertexType != GLGeometry.VERTICES_PROJECTED ||
                terrainVersion != this.baseElevationVersion ||
                !this.vertexHasBaseEl) {

            double lat;
            double lon;
            double alt;

            GeoPoint scratchGeo = GeoPoint.createMutable();
            PointD scratchD = new PointD(0d, 0d, 0d);
            for (int i = 0; i < numPoints; i++) {
                lon = Unsafe.getDouble(this.pointsPtr + ((i * 3) * 8));
                lat = Unsafe.getDouble(this.pointsPtr + ((i * 3 + 1) * 8));
                alt = Unsafe.getDouble(this.pointsPtr + ((i * 3 + 2) * 8));
                scratchGeo.set(lat, lon);
                scratchGeo.set(alt + baseElevation);
                sceneModel.mapProjection.forward(scratchGeo, scratchD);
                Unsafe.setFloats(this.verticesPtr + (i * 4 * 3),
                        (float) scratchD.x,
                        (float) scratchD.y,
                        (float) scratchD.z);
            }

            this.verticesVersion = srid;
            this.vertexHasBaseEl = true;
        }

        this.vertexType = GLGeometry.VERTICES_PROJECTED;
        return true;
    }

    private boolean validate(GLMapView view, int vertices, int terrainVersion,
            boolean vertexUsesBaseEl) {
        if (!this.drawCommon())
            return false;

        final int numPoints = this.points.limit() / 3;
        if (this.points == null || numPoints < 3)
            return false;

        if (this.baseElevationVersion != terrainVersion) {
            double v = view.getTerrainMeshElevation(
                    (this.subjectMbb.maxY + this.subjectMbb.minY) / 2d,
                    (this.subjectMbb.maxX + this.subjectMbb.minX) / 2d);
            // if no terrain elevation is available, assume ellipsoid surface
            if (Double.isNaN(v))
                v = 0d;
            this.baseElevationVersion = terrainVersion;

            // the base elevation has changed, vertices must be rebuilt
            if (this.baseElevation != v && vertexUsesBaseEl) {
                this.verticesVersion = ~this.verticesVersion;
            }
            this.baseElevation = v;
        }

        // project the vertices
        switch (vertices) {
            case GLGeometry.VERTICES_PIXEL:
                if (this.verticesVersion != view.drawVersion
                        || this.vertexType != vertices) {
                    // translation and scale for altitude values
                    final double tz = (baseElevation + view.elevationOffset);
                    final double sz = view.elevationScaleFactor;

                    double lat;
                    double lon;
                    double alt;
                    for (int i = 0; i < numPoints; i++) {
                        lon = Unsafe.getDouble(this.pointsPtr + ((i * 3) * 8));
                        lat = Unsafe
                                .getDouble(this.pointsPtr + ((i * 3 + 1) * 8));
                        alt = Unsafe
                                .getDouble(this.pointsPtr + ((i * 3 + 2) * 8));
                        view.scratch.geo.set(lat, lon);
                        view.scratch.geo.set(
                                (alt + tz) * sz);
                        view.scene.mapProjection.forward(view.scratch.geo,
                                view.scratch.pointD);
                        view.scene.forward.transform(view.scratch.pointD,
                                view.scratch.pointD);
                        Unsafe.setFloats(this.verticesPtr + (i * 4 * 3),
                                (float) view.scratch.pointD.x,
                                (float) view.scratch.pointD.y,
                                (float) view.scratch.pointD.z);
                    }

                    this.verticesVersion = view.drawVersion;
                }
                break;
            case GLGeometry.VERTICES_PROJECTED:
                if (view.drawSrid != this.verticesVersion ||
                        this.vertexType != vertices ||
                        (vertexUsesBaseEl
                                && terrainVersion != this.baseElevationVersion)
                        ||
                        this.vertexHasBaseEl != vertexUsesBaseEl) {

                    double lat;
                    double lon;
                    double alt;

                    for (int i = 0; i < numPoints; i++) {
                        lon = Unsafe.getDouble(this.pointsPtr + ((i * 3) * 8));
                        lat = Unsafe
                                .getDouble(this.pointsPtr + ((i * 3 + 1) * 8));
                        alt = Unsafe
                                .getDouble(this.pointsPtr + ((i * 3 + 2) * 8));
                        view.scratch.geo.set(lat, lon);
                        if (vertexUsesBaseEl)
                            view.scratch.geo.set(
                                    alt + baseElevation);
                        else
                            view.scratch.geo.set(alt);
                        view.scene.mapProjection.forward(view.scratch.geo,
                                view.scratch.pointD);
                        Unsafe.setFloats(this.verticesPtr + (i * 4 * 3),
                                (float) view.scratch.pointD.x,
                                (float) view.scratch.pointD.y,
                                (float) alt);
                    }

                    this.verticesVersion = view.drawSrid;
                    this.vertexHasBaseEl = vertexUsesBaseEl;
                }
                break;
            default:
                throw new IllegalArgumentException();
        }

        this.vertexType = vertices;
        return true;
    }
}
