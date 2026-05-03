
package com.atakmap.android.hellobuildings.parser;

import java.util.ArrayList;
import java.util.HashMap;

import org.xml.sax.Attributes;
import org.xml.sax.SAXException;
import org.xml.sax.helpers.DefaultHandler;

public class ParserHandler extends DefaultHandler {

    boolean D = false;
    boolean mNode = false;
    boolean mMember = false;
    boolean mWay = false;
    boolean mRelation = false;
    boolean mTag = false;
    boolean mNd = false;
    Node mTempNode = null;
    Way mTempWay = null;
    ArrayList<Node> mTempNodeList;
    String mTempId;

    NodeList mNodeList;
    BuildingList mBuildingList;

    HashMap<String, String> mTags;

    public ParserHandler(NodeList nl, BuildingList bl) {
        mNodeList = nl;
        mBuildingList = bl;
    }

    @Override
    public void startElement(String uri,
            String localName, String qName, Attributes attributes)
            throws SAXException {
        if (qName.equalsIgnoreCase("node")) {
            String id = attributes.getValue("id");
            String lat = attributes.getValue("lat");
            String lon = attributes.getValue("lon");
            if (D)
                System.out.println(
                        "Node: id : " + id + " (" + lat + "," + lon + ")");
            mTempNode = new Node(Long.parseLong(id), Double.parseDouble(lat),
                    Double.parseDouble(lon));
            mNodeList.put(id, mTempNode);
            mNode = true;
            mTags = new HashMap<String, String>();
        } else if (qName.equalsIgnoreCase("member")) {
            String type = attributes.getValue("type");
            if (D)
                System.out.println("member : " + type);
            mMember = true;
        } else if (qName.equalsIgnoreCase("way")) {
            String id = attributes.getValue("id");
            mTempId = id;
            if (D)
                System.out.println("Way: id : " + id);
            mWay = true;
            mTags = new HashMap<String, String>();
            mTempNodeList = new ArrayList<Node>();
            ;
        } else if (qName.equalsIgnoreCase("relation")) {
            String id = attributes.getValue("id");
            if (D)
                System.out.println("Relation: id : " + id);
            mRelation = true;
            mTags = new HashMap<String, String>();
        } else if (qName.equalsIgnoreCase("tag")) {
            String k = attributes.getValue("k");
            String v = attributes.getValue("v");
            if (D)
                System.out.println("tag: (" + k + "=" + v + ")");
            mTag = true;
            mTags.put(k, v);
        } else if (qName.equalsIgnoreCase("nd")) {
            String ref = attributes.getValue("ref");
            if (D)
                System.out.println("nd: ref : " + ref);
            mNd = true;
            Node tempNode = mNodeList.get(ref);
            mTempNodeList.add(tempNode);
        }
    }

    @Override
    public void endElement(String uri,
            String localName, String qName) throws SAXException {
        if (D)
            System.out.println("End Element :" + qName);

        if (qName.equalsIgnoreCase("way")) {

            if (mTags != null &&
                    (mTags.containsKey("building")
                            || mTags.containsKey("building:part"))) {
                mTempWay = new Building(Long.parseLong(mTempId));
                mTempWay.setTags(mTags);
                mTempWay.setNodeList(mTempNodeList);
                if (D)
                    System.out.println(((Building) mTempWay).toString());
                mBuildingList.put(mTempId, (Building) mTempWay);
            } else {
                mTempWay = new Way(Long.parseLong(mTempId));
                mTempWay.setNodeList(mTempNodeList);
                if (mTags != null) {
                    mTempWay.setTags(mTags);
                }
            }

        } else if (qName.equalsIgnoreCase("relation")) {
            // TODO:
        } else if (qName.equalsIgnoreCase("node")) {
            mTempNode = null;
            // TODO:
        } else if (qName.equalsIgnoreCase("member")) {
            // TODO:
        }

    }

    @Override
    public void characters(char ch[],
            int start, int length) throws SAXException {
        if (mNode) {
            if (D)
                System.out.println("Node: " + new String(ch, start, length));
            mNode = false;
        } else if (mMember) {
            if (D)
                System.out.println("member: " + new String(ch, start, length));
            mMember = false;
        } else if (mWay) {
            if (D)
                System.out.println("Way: " + new String(ch, start, length));
            mWay = false;
        } else if (mRelation) {
            if (D)
                System.out
                        .println("relation: " + new String(ch, start, length));
            mRelation = false;
        } else if (mTag) {
            if (D)
                System.out.println("tag: " + new String(ch, start, length));
            mTag = false;
        }
    }
}
