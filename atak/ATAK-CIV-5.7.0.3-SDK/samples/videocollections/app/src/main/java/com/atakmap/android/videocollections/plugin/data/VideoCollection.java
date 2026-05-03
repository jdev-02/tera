package com.atakmap.android.videocollections.plugin.data;

import com.atakmap.coremap.log.Log;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import gov.tak.api.util.AttributeSet;

public class VideoCollection {
    private static final String TAG = VideoCollection.class.getSimpleName();

    public static final String ELEMENT_NAME = "videoCollection";

    public final List<VideoFeed> feedList = new ArrayList<>();
    private final Map<String,String> attributes = new HashMap<String, String>() {{
        // string
        put("uid", "");   // required
        put("alias", ""); // required
        put("classification", null);
        // uri
        put("thumbnail", null);
        // boolean
        put("active", null);
    }};

    public VideoCollection() {}


    public VideoCollection(AttributeSet attributeSet) {
        attributes.put("uid", attributeSet.getStringAttribute("uid"));
        attributes.put("alias", attributeSet.getStringAttribute("alias"));
        attributes.put("classification", attributeSet.getStringAttribute("classification"));
        attributes.put("thumbnail", attributeSet.getStringAttribute("thumbnail"));
        attributes.put("active", attributeSet.getStringAttribute("active"));
    }

    public AttributeSet getAttributeSet() {
        AttributeSet attributeSet = new AttributeSet();
        attributeSet.setAttribute("uid", attributes.get("uid"));
        attributeSet.setAttribute("alias", attributes.get("alias"));
        attributeSet.setAttribute("classification", attributes.get("classification"));
        attributeSet.setAttribute("thumbnail", attributes.get("thumbnail"));
        attributeSet.setAttribute("active", attributes.get("active"));
        return attributeSet;
    }

    public void putAttribute(String key, String value) {
        if (attributes.containsKey(key))
            attributes.put(key, value);
    }

    public String getAttribute(String key) {
        return attributes.get(key);
    }

    public void display() {
        VideoFeed feed = null;

        if (feedList.size() == 0) {
            Log.w(TAG, "No feeds in this VideoCollection");
            return;
        }

        for (VideoFeed f : feedList)
            if (Boolean.parseBoolean(f.getAttribute("active")))
                feed = f;

        if (feed == null)
            feed = feedList.get(0);

        feed.display();
    }
}
