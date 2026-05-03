
package com.atakmap.android.hellobuildings.opengl;

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
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.math.PointD;
import com.atakmap.util.Releasable;

public class GLExtrudingPolygon implements Releasable {

    /** the exterior ring of the polygon */
    LineString subject;
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
     * The version of the vertex buffer content. This value should be compared
     * with {@link GLMapView#drawSrid}.
     */
    private int verticesSrid;
    private double verticesLcsOriginX;
    private double verticesLcsOriginY;
    private double verticesLcsOriginZ;

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

    private boolean initBuffers() {
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

    synchronized boolean validateAsync(GLMapView view, MapSceneModel sceneModel,
            int terrainVersion) {
        if (!this.initBuffers())
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
                this.verticesSrid = ~this.verticesSrid;
            }
            this.baseElevation = v;
        }

        final int srid = sceneModel.mapProjection.getSpatialReferenceID();

        // project the vertices
        if (srid != this.verticesSrid ||
                verticesLcsOriginX != 0d ||
                verticesLcsOriginY != 0d ||
                verticesLcsOriginZ != 0d ||
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

            this.verticesSrid = srid;
            this.vertexHasBaseEl = true;

            this.verticesLcsOriginX = 0d;
            this.verticesLcsOriginY = 0d;
            this.verticesLcsOriginZ = 0d;
        }

        return true;
    }

    synchronized boolean validateAsync(GLMapView view,
            LocalCoordinateSystem lcs, int terrainVersion) {
        if (!this.initBuffers())
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
                this.verticesSrid = ~this.verticesSrid;
            }
            this.baseElevation = v;
        }

        final int srid = lcs.proj.getSpatialReferenceID();

        // project the vertices
        if (srid != this.verticesSrid ||
                lcs.origin.x != verticesLcsOriginX ||
                lcs.origin.y != verticesLcsOriginY ||
                lcs.origin.z != verticesLcsOriginZ ||
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
                lcs.proj.forward(scratchGeo, scratchD);
                lcs.apply(scratchD, scratchD);
                Unsafe.setFloats(this.verticesPtr + (i * 4 * 3),
                        (float) scratchD.x,
                        (float) scratchD.y,
                        (float) scratchD.z);
            }

            this.verticesSrid = srid;
            this.vertexHasBaseEl = true;

            this.verticesLcsOriginX = lcs.origin.x;
            this.verticesLcsOriginY = lcs.origin.y;
            this.verticesLcsOriginZ = lcs.origin.z;
        }

        return true;
    }

}
