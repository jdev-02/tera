
package com.atakmap.android.hellobuildings.opengl;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.DoubleBuffer;
import java.nio.FloatBuffer;
import java.nio.ShortBuffer;


import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPoint.AltitudeReference;


import com.atakmap.lang.Unsafe;
import com.atakmap.map.MapSceneModel;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureCursor;
import com.atakmap.map.layer.feature.FeatureDefinition;
import com.atakmap.map.layer.feature.FeatureDefinition2;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.GeometryFactory;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.map.opengl.GLMapView;
import com.atakmap.math.PointD;

public final class ExtrudedPolygonData {
    Envelope mbb;
    DoubleBuffer points;
    FloatBuffer projected;
    int projectedSrid;
    long version;
    double baseElevation;
    int baseElevationVersion;
    ShortBuffer indices;

    public void updateGeometry(FeatureCursor f) {
        updateGeometryImpl(f.getVersion(), f.getGeomCoding(),
                f.getRawGeometry());
    }

    public void updateGeometry(Feature f) {
        updateGeometryImpl(f.getVersion(),
                FeatureDefinition2.GEOM_ATAK_GEOMETRY, f.getGeometry());
    }

    public void updateGeometry(long version, Geometry geometry) {
        updateGeometryImpl(version, FeatureDefinition2.GEOM_ATAK_GEOMETRY,
                geometry);
    }

    private synchronized void updateGeometryImpl(long version, int geomCoding,
            Object rawGeom) {
        if (version == this.version)
            return;

        if (this.points != null)
            this.points.limit(0);

        Geometry geom = null;
        switch (geomCoding) {
            case FeatureDefinition.GEOM_SPATIALITE_BLOB:
                geom = GeometryFactory.parseSpatiaLiteBlob((byte[]) rawGeom);
                break;
            case FeatureDefinition.GEOM_WKB:
                geom = GeometryFactory.parseWkb((byte[]) rawGeom);
                break;
            case FeatureDefinition.GEOM_WKT:
                geom = GeometryFactory.parseWkt((String) rawGeom);
                break;
            case FeatureDefinition.GEOM_ATAK_GEOMETRY:
                geom = (Geometry) rawGeom;
                break;
            default:
                return;
        }

        LineString subject;
        if (geom instanceof LineString)
            subject = (LineString) geom;
        else if (geom instanceof Polygon)
            subject = ((Polygon) geom).getExteriorRing();
        else
            return;

        final int numPoints = subject.getNumPoints();
        final int vertexCount = numPoints - 1;
        if (vertexCount < 4)
            return;

        long pointsPtr;
        if (this.points == null
                || (this.points.capacity() < (3 * 2 * vertexCount))) {
            ByteBuffer buf;

            buf = Unsafe.allocateDirect(3 * 2 * vertexCount * 8);
            buf.order(ByteOrder.nativeOrder());
            this.points = buf.asDoubleBuffer();
            pointsPtr = Unsafe.getBufferPointer(this.points);

            buf = Unsafe.allocateDirect(
                    ((vertexCount * 6) + ((vertexCount - 2) * 3)) * 2);
            buf.order(ByteOrder.nativeOrder());
            this.indices = buf.asShortBuffer();
            final long indicesPtr = Unsafe.getBufferPointer(this.indices);

            long topPtr = pointsPtr;
            long bottomPtr = topPtr + (vertexCount * 3 * 8);
            long indexPtr = indicesPtr;
            for (int i = 0; i < vertexCount; i++) {
                final double x = subject.getX(i);
                final double y = subject.getY(i);
                final double z = subject.getZ(i);

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

        if (this.projected == null
                || this.projected.capacity() < (3 * 2 * vertexCount)) {
            ByteBuffer buf;

            buf = Unsafe.allocateDirect(2 * 3 * vertexCount * 8);
            buf.order(ByteOrder.nativeOrder());
            this.projected = buf.asFloatBuffer();
        }
    }

    public synchronized boolean validateProjected(GLMapView view,
            MapSceneModel sceneModel, int terrainVersion) {
        if (this.points == null)
            return false;

        final int numPoints = this.points.limit() / 3;
        if (numPoints < 3)
            return false;

        if (this.baseElevationVersion != terrainVersion) {
            double v = view.getElevation(
                    (this.mbb.maxY + this.mbb.minY) / 2d,
                    (this.mbb.maxX + this.mbb.minX) / 2d);
            // if no terrain elevation is available, assume ellipsoid surface
            if (!GeoPoint.isAltitudeValid(v))
                v = 0d;
            this.baseElevationVersion = terrainVersion;

            // the base elevation has changed, vertices must be rebuilt
            if (this.baseElevation != v) {
                this.projectedSrid = ~this.projectedSrid;
            }
            this.baseElevation = v;
        }

        final int srid = sceneModel.mapProjection.getSpatialReferenceID();

        // project the vertices
        if (srid != this.projectedSrid) {
            double lat;
            double lon;
            double alt;

            final long pointsPtr = Unsafe.getBufferPointer(this.points);
            final long projectedPtr = Unsafe.getBufferPointer(this.projected);

            GeoPoint scratchGeo = GeoPoint.createMutable();
            PointD scratchD = new PointD(0d, 0d, 0d);
            for (int i = 0; i < numPoints; i++) {
                lon = Unsafe.getDouble(pointsPtr + ((i * 3) * 8));
                lat = Unsafe.getDouble(pointsPtr + ((i * 3 + 1) * 8));
                alt = Unsafe.getDouble(pointsPtr + ((i * 3 + 2) * 8));
                scratchGeo.set(lat, lon);
                scratchGeo.set(alt + baseElevation);
                sceneModel.mapProjection.forward(scratchGeo, scratchD);
                Unsafe.setFloats(projectedPtr + (i * 4 * 3),
                        (float) scratchD.x,
                        (float) scratchD.y,
                        (float) scratchD.z);
            }
            this.projectedSrid = srid;
        }

        return true;
    }
}
