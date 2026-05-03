
package com.atakmap.android.hello3d;

import java.util.Collection;
import java.util.HashSet;
import java.util.Set;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.AbstractLayer;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;

import android.util.Log;

public final class ExtrudedPolygonsExample extends AbstractLayer {

    private Set<Polygon> polys;

    public ExtrudedPolygonsExample() {
        super("Extruded Polygons Example");
        Log.d("debug", "Extruded PolygonsExample");
        // circa MGRS 17S Qv 00365 60329

        Polygon bldg1 = createPoly(new GeoPoint[] {
                new GeoPoint(35.76720, -78.78344),
                new GeoPoint(35.76686, -78.78354),
                new GeoPoint(35.76692, -78.78388),
                new GeoPoint(35.76725, -78.78378),
                new GeoPoint(35.76720, -78.78344),
        },
                3d);

        Polygon bldg2 = createPoly(new GeoPoint[] {
                new GeoPoint(35.76731, -78.78317),
                new GeoPoint(35.76725, -78.78289),
                new GeoPoint(35.76692, -78.78304),
                new GeoPoint(35.76698, -78.78333),
                new GeoPoint(35.76731, -78.78317),
        },
                3d);

        polys = new HashSet<Polygon>();
        polys.add(bldg1);
        polys.add(bldg2);
    }

    public Collection<Polygon> getPolygons() {
        return this.polys;
    }

    public int getColor() {
        return 0xC07F7F7F;
    }

    private static Polygon createPoly(GeoPoint[] points, double height) {
        LineString exterior = new LineString(3);
        for (int i = 0; i < points.length; i++)
            exterior.addPoint(points[i].getLongitude(), points[i].getLatitude(),
                    height);

        Polygon retval = new Polygon(3);
        retval.addRing(exterior);
        return retval;
    }
}
