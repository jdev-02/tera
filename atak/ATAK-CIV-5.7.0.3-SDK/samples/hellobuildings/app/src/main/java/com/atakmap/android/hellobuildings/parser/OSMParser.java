
package com.atakmap.android.hellobuildings.parser;

import java.io.File;

import javax.xml.parsers.SAXParser;
import javax.xml.parsers.SAXParserFactory;

import com.atakmap.coremap.log.Log;

public final class OSMParser {

    public final static  String TAG = "OSMParser";

    public final static String DEFAULT_SERVER = "https://openstreetmap.org/api/0.6/map";

    private OSMParser() {
    }

    // XXX - this needs to change to Overpass API
    // see http://wiki.openstreetmap.org/wiki/Overpass_API
    // see http://overpass-turbo.eu/
    // sample Overpass QL for buildings 
    /*
        [out:xml];
        (
          way(poly:"50.7 7.1 50.7 7.2 50.75 7.15")[building];
          <;
        );
        (._;>;);
        out meta;
     */
    public static String getOsmURI(double W_LAT, double S_LON, double E_LAT,
            double N_LON) {
        return getOsmURI(DEFAULT_SERVER, W_LAT, S_LON, E_LAT, N_LON);
    }

    public static String getOsmURI(String serverUrl, double W_LAT, double S_LON,
            double E_LAT, double N_LON) {
        return serverUrl + "?bbox=" +
                S_LON + "," +
                W_LAT + "," +
                N_LON + "," +
                E_LAT;
    }

    public static String getOsmURI(String W_LAT, String S_LON, String E_LAT,
            String N_LON) {
        return getOsmURI(DEFAULT_SERVER, W_LAT, S_LON, E_LAT, N_LON);
    }

    public static String getOsmURI(String serverUrl, String W_LAT, String S_LON,
            String E_LAT, String N_LON) {
        return serverUrl + "?bbox=" +
                S_LON + "," +
                W_LAT + "," +
                N_LON + "," +
                E_LAT;
    }

    public static void main(String[] args) {

        try {
            //File inputFile = new File("input.txt");
            File inputFile = new File("/sdcard/atak/mapnyc.osm");
            SAXParserFactory factory = SAXParserFactory.newInstance();
            SAXParser saxParser = factory.newSAXParser();
            NodeList nl = new NodeList();
            BuildingList bl = new BuildingList();
            ParserHandler userhandler = new ParserHandler(nl, bl);
            saxParser.parse(inputFile, userhandler);

            //System.out.println("Size: "+  nl.size());

            //BuildingList.getInstance().writeKML("Filename.kml");

        } catch (Exception e) {
            Log.e(TAG,"error",e);
        }
    }
}
