
package com.atakmap.android.hello3d;

import java.util.Collection;
import java.util.HashSet;
import java.util.Set;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.AbstractLayer;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;

public class ExtrudedPolygonsBatchExample extends AbstractLayer {

    private Set<Polygon> polys;

    public ExtrudedPolygonsBatchExample() {
        super("Extruded Polygons Batch Example");

        // circa MGRS 17S Qv 00365 60329

        Polygon bldg1 = createPoly(new GeoPoint[] {
                new GeoPoint(35.76831, -78.78275),
                new GeoPoint(35.76824, -78.78253),
                new GeoPoint(35.76790, -78.78267),
                new GeoPoint(35.76798, -78.78289),
                new GeoPoint(35.76831, -78.78275),
        },
                3d);

        Polygon bldg2 = createPoly(new GeoPoint[] {
                new GeoPoint(35.76844, -78.78318),
                new GeoPoint(35.76841, -78.78306),
                new GeoPoint(35.76802, -78.78322),
                new GeoPoint(35.76806, -78.78333),
                new GeoPoint(35.76814, -78.78331),
                new GeoPoint(35.76819, -78.78347),
                new GeoPoint(35.76812, -78.78351),
                new GeoPoint(35.76816, -78.78363),
                new GeoPoint(35.76845, -78.78350),
                new GeoPoint(35.76840, -78.78339),
                new GeoPoint(35.76831, -78.78342),
                new GeoPoint(35.76827, -78.78326),
                new GeoPoint(35.76844, -78.78318),
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
        return 0xC03F3F7F;
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
