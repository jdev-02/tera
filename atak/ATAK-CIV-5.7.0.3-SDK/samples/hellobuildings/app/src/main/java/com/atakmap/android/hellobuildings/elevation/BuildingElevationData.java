
package com.atakmap.android.hellobuildings.elevation;


import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPointMetaData;
import com.atakmap.map.elevation.AbstractElevationData;
import com.atakmap.map.elevation.ElevationManager;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.geometry.Envelope;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.GeometryCollection;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Point;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.math.Rectangle;

final class BuildingElevationData extends AbstractElevationData {

    final static ElevationManager.QueryParameters DTM_PARAMS = new ElevationManager.QueryParameters();
    static {
        DTM_PARAMS.elevationModel = MODEL_TERRAIN;
    }

    Feature feature;
    Geometry geometry;
    Envelope mbb;
    Double baseEl;
    double height;

    BuildingElevationData(Feature f) {
        super(MODEL_SURFACE, "OSM", 0d);

        this.feature = feature;
        this.geometry = f.getGeometry();
        if (geometry != null)
            mbb = geometry.getEnvelope();
        baseEl = null;
        height = getHeight(geometry);
    }

    @Override
    public double getResolution() {
        return 0;
    }

    @Override
    public double getElevation(double latitude, double longitude) {
        if (!Rectangle.contains(mbb.minX, mbb.minY, mbb.maxX, mbb.maxY,
                latitude, longitude))
            return Double.NaN;
        if (baseEl == null) {
            double a = ElevationManager.getElevation(
                    (mbb.maxY + mbb.minY) / 2d, (mbb.maxX + mbb.minX) / 2d,
                    DTM_PARAMS);
            if (GeoPoint.isAltitudeValid(a))
                baseEl = Double.valueOf(a);
            else
                baseEl = Double.valueOf(Double.NaN);
        }

        if (Double.isNaN(baseEl))
            return height;
        else
            return height + baseEl;
    }

    private static double getHeight(Geometry g) {
        if (g.getDimension() != 3)
            return Double.NaN;
        if (g instanceof Point) {
            return ((Point) g).getZ();
        } else if (g instanceof LineString) {
            LineString ls = (LineString) g;
            double v = ls.getZ(0);
            for (int i = 1; i < ls.getNumPoints(); i++) {
                if (ls.getZ(i) > v)
                    v = ls.getZ(i);
            }
            return v;
        } else if (g instanceof Polygon) {
            return getHeight(((Polygon) g).getExteriorRing());
        } else if (g instanceof GeometryCollection) {
            double v = Double.NaN;
            for (Geometry child : ((GeometryCollection) g).getGeometries()) {
                double cv = getHeight(child);
                if (Double.isNaN(v) || cv > v)
                    v = cv;
            }
            return v;
        } else {
            return Double.NaN;
        }
    }

}
