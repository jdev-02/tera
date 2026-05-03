
package com.atakmap.android.hellobuildings.parser;

class Node extends Element {
    //<node id="3707044715" visible="true" version="1" changeset="33469235" timestamp="2015-08-20T19:13:58Z" 
    // user="DGerveno" uid="2536370" lat="42.1380842" lon="-0.4100642"/>
    double lat;
    double lon;

    public Node(long id, double lat, double lon) {
        super(id);
        this.lat = lat;
        this.lon = lon;
    }
}
