
package com.atakmap.android.hellobuildings.parser;

import java.util.Collection;
import java.util.HashMap;

public class NodeList {
    private HashMap<String, Node> mNodeList;

    public NodeList() {
        mNodeList = new HashMap<String, Node>();
    }

    public void put(String k, Node n) {
        mNodeList.put(k, n);
    }

    public Node get(String k) {
        return mNodeList.get(k);
    }

    public Collection<Node> values() {
        return mNodeList.values();
    }

    public int size() {
        return mNodeList.size();
    }

    public void destroy() {
        mNodeList = null;
    }
}
