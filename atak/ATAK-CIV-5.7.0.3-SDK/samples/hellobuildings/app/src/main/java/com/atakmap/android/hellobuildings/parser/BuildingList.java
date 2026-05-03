
package com.atakmap.android.hellobuildings.parser;

import java.io.PrintWriter;
import java.util.Collection;
import java.util.HashMap;

import com.atakmap.coremap.log.Log;

public class BuildingList {

    public static final String TAG = "BuildingList";

    private HashMap<String, Building> mBuildingList;

    public BuildingList() {
        mBuildingList = new HashMap<String, Building>();
    }

    public void put(String k, Building n) {
        mBuildingList.put(k, n);
    }

    public Building get(String k) {
        return mBuildingList.get(k);
    }

    public Collection<Building> values() {
        return mBuildingList.values();
    }

    public int size() {
        return mBuildingList.size();
    }

    public void writeKML(String fn) {
        try {
            PrintWriter writer = new PrintWriter(fn, "UTF-8");
            writer.print(Building.kmlHeader());
            for (Building B : values()) {
                writer.print(B.toKML());
            }

            writer.print(Building.kmlFooter());
            writer.close();
        } catch (Exception e) {
            Log.e(TAG,"error",e);
        }
    }

    public void destroy() {
        mBuildingList = null;
    }
}
