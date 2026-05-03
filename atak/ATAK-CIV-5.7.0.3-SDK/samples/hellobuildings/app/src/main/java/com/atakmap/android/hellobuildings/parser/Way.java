
package com.atakmap.android.hellobuildings.parser;

import java.util.ArrayList;
import java.util.HashMap;

public class Way extends Element {
    ArrayList<Node> mNodeList;
    HashMap<String, String> mTags;

    public Way(long id) {
        super(id);
        mNodeList = new ArrayList<Node>();
    }

    public Way(long id, ArrayList<Node> nl) {
        super(id);
        mNodeList = nl;
    }

    public boolean addNode(Node n) {
        return mNodeList.add(n);
    }

    public void setTags(HashMap<String, String> tags) {
        mTags = tags;
    }

    public void putTag(String k, String v) {
        if (mTags == null) {
            mTags = new HashMap<String, String>();
        }
        mTags.put(k, v);
    }

    public String getTag(String k) {
        return mTags.get(k);
    }

    public void setNodeList(ArrayList<Node> nl) {
        mNodeList = nl;
    }
}
