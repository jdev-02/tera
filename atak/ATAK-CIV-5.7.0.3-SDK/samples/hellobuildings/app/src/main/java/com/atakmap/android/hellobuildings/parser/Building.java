
package com.atakmap.android.hellobuildings.parser;

import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.feature.geometry.GeometryCollection;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;

import java.util.ArrayList;

import com.atakmap.coremap.log.Log;

public class Building extends Way {

    public static final String TAG = "Building";

    public Building(long id) {
        super(id);

    }

    public Building(long id, ArrayList<Node> nl) {
        super(id, nl);
    }

    public double getLevels() {
        try {
            if (mTags.containsKey("building:levels")) {
                return Double.parseDouble(mTags.get("building:levels"));
            }
        } catch (Exception e) {
            Log.e(TAG,"error",e);
        }
        return 1d;
    }

    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("Building id: " + id + "\n");
        if (mTags.containsKey("building")) {
            sb.append("building: " + mTags.get("building") + "\n");
        }
        if (mTags.containsKey("building:min_level")) {
            sb.append("min_level: " + mTags.get("building:min_level") + ", ");
        }
        if (mTags.containsKey("building:levels")) {
            sb.append("levels: " + mTags.get("building:levels") + "\n");
        }
        for (Node n : mNodeList) {
            sb.append("ID: " + n.id + "\n");
            sb.append("Lat Lon: " + n.lat + "," + n.lon + "\n");
        }
        return sb.toString();
    }

    /*
     *     <Placemark>
        <name>Untitled Polygon</name>
        <styleUrl>#m_ylw-pushpin</styleUrl>
        <Polygon>
            <tessellate>1</tessellate>
            <outerBoundaryIs>
                <LinearRing>
                    <coordinates>
                        -92.28353118510111,36.08494938132413,0 -92.28495938640802,36.07254602112175,0 -92.27622665702147,36.07234734967967,0 -92.27230346238825,36.08447888415089,0 -92.28353118510111,36.08494938132413,0 
                    </coordinates>
                </LinearRing>
            </outerBoundaryIs>
        </Polygon>
    </Placemark>
     */
    public static String kmlHeader() {
        StringBuilder sb = new StringBuilder();
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
        sb.append(
                "<kml xmlns=\"http://www.opengis.net/kml/2.2\" xmlns:gx=\"http://www.google.com/kml/ext/2.2\" xmlns:kml=\"http://www.opengis.net/kml/2.2\" xmlns:atom=\"http://www.w3.org/2005/Atom\">\n");
        sb.append("<Document>\n");
        sb.append("    <name>Untitled Polygon.kml</name>\n");
        sb.append("    <Style id=\"s_ylw-pushpin\">\n");
        sb.append("        <IconStyle>\n");
        sb.append("            <scale>1.1</scale>\n");
        sb.append("            <Icon>\n");
        sb.append(
                "                <href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>\n");
        sb.append("            </Icon>\n");
        sb.append(
                "            <hotSpot x=\"20\" y=\"2\" xunits=\"pixels\" yunits=\"pixels\"/>\n");
        sb.append("        </IconStyle>\n");
        sb.append("    </Style>\n");
        sb.append("    <StyleMap id=\"m_ylw-pushpin\">\n");
        sb.append("        <Pair>\n");
        sb.append("            <key>normal</key>\n");
        sb.append("            <styleUrl>#s_ylw-pushpin</styleUrl>\n");
        sb.append("        </Pair>\n");
        sb.append("        <Pair>\n");
        sb.append("            <key>highlight</key>\n");
        sb.append("            <styleUrl>#s_ylw-pushpin_hl</styleUrl>\n");
        sb.append("        </Pair>\n");
        sb.append("    </StyleMap>\n");
        sb.append("    <Style id=\"s_ylw-pushpin_hl\">\n");
        sb.append("        <IconStyle>\n");
        sb.append("            <scale>1.3</scale>\n");
        sb.append("            <Icon>\n");
        sb.append(
                "                <href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>\n");
        sb.append("            </Icon>\n");
        sb.append(
                "            <hotSpot x=\"20\" y=\"2\" xunits=\"pixels\" yunits=\"pixels\"/>\n");
        sb.append("        </IconStyle>\n");
        sb.append("    </Style>\n");

        return sb.toString();
    }

    public static String kmlFooter() {
        return ("</Document>\n" +
                "</kml>\n");
    }

    public String toKML() {
        StringBuilder sb = new StringBuilder();

        sb.append("<Placemark>\n");
        sb.append("<name>ID: " + id + "</name>\n");
        sb.append("<styleUrl>#m_ylw-pushpin</styleUrl>\n");
        sb.append("<Polygon>\n");
        sb.append("    <tessellate>1</tessellate>\n");
        sb.append("    <outerBoundaryIs>\n");
        sb.append("        <LinearRing>\n");
        sb.append("            <coordinates>\n");
        for (Node n : mNodeList) {
            sb.append(n.lon + "," + n.lat + ",0 ");
        }
        sb.append("\n");
        //sb.append("                -92.28353118510111,36.08494938132413,0 -92.28495938640802,36.07254602112175,0 -92.27622665702147,36.07234734967967,0 -92.27230346238825,36.08447888415089,0 -92.28353118510111,36.08494938132413,0 \n");
        sb.append("            </coordinates>\n");
        sb.append("        </LinearRing>\n");
        sb.append("    </outerBoundaryIs>\n");
        sb.append("</Polygon>\n");
        sb.append("</Placemark>\n");
        return sb.toString();

    }

    public GeoPoint[] asGeoPointArray() {
        int size = mNodeList.size();
        GeoPoint[] ret = new GeoPoint[size];
        for (int i = 0; i < size; ++i) {
            ret[i] = new GeoPoint(mNodeList.get(i).lat, mNodeList.get(i).lon);
        }
        return ret;
    }

    /**
     * Returns the polygon representing the bounds of the building.
     * @param heightOffset  If <code>true</code>, the polygon will be 3D, with
     *                      the <code>z</code> values set to the height of the
     *                      building
     * @return  The polygon bounds of the building.
     */
    public Polygon asPolygon(boolean heightOffset) {
        int size = mNodeList.size();
        LineString exterior;
        if (heightOffset) {
            final double height = 3d * getLevels();
            exterior = new LineString(3);
            for (int i = 0; i < size; ++i) {
                exterior.addPoint(mNodeList.get(i).lon, mNodeList.get(i).lat,
                        height);
            }
        } else {
            exterior = new LineString(2);
            for (int i = 0; i < size; ++i) {
                exterior.addPoint(mNodeList.get(i).lon, mNodeList.get(i).lat);
            }
        }
        return new Polygon(exterior);
    }

    /**
     * Returns a multi-surface geometry representing the faces of the volume
     * defining the building.
     * @return  A multi-surface geometry representing the exterior faces of the
     *          volume defining the building.
     */
    public GeometryCollection asVolume() {
        Polygon polygon = asPolygon(true);

        // the returned geometry will be a GeometryCollection instance, with a
        // dimension of 3 indicating that it stores coordinates as x,y,z
        GeometryCollection retval = new GeometryCollection(3);

        // add the top to the collection
        retval.addGeometry(polygon);

        final LineString exterior = polygon.getExteriorRing();

        for (int i = 0; i < exterior.getNumPoints() - 1; i++) {
            // generate a polygon for each side
            LineString ring = new LineString(3);
            ring.addPoint(exterior.getX(i),
                    exterior.getY(i),
                    exterior.getZ(i));
            ring.addPoint(exterior.getX(i + 1),
                    exterior.getY(i + 1),
                    exterior.getZ(i + 1));
            ring.addPoint(exterior.getX(i + 1),
                    exterior.getY(i + 1),
                    0d);
            ring.addPoint(exterior.getX(i),
                    exterior.getY(i),
                    0d);
            ring.addPoint(exterior.getX(i),
                    exterior.getY(i),
                    exterior.getZ(i));

            // add the side to the collection
            Polygon side = new Polygon(ring.getDimension());
            side.addRing(ring);
            retval.addGeometry(side);
        }

        return retval;
    }
}
