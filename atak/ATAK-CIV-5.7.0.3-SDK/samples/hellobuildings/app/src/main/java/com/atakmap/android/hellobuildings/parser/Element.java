
package com.atakmap.android.hellobuildings.parser;

import java.util.HashMap;
import java.util.Map;

class Element {
    protected long id; //Unique identifier
    private String user; //Username of last editor
    private long uid; //User id of last editor
    private String timestamp; //Time of last edit
    private boolean visible;
    private int version; //default: 1
    private long changeset;
    Map<String, String> tags;

    public Element(long id) {
        this.id = id;
        version = 1;
        visible = true;
        tags = new HashMap<String, String>();
    }

    public long getId() {
        return id;
    }
}
