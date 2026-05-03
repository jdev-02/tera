package com.atakmap.android.videocollections.plugin.data;

import android.content.Intent;

import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.video.VideoDropDownReceiver;

import java.util.HashMap;
import java.util.Map;

public class VideoFeed {

    public static final String ELEMENT_NAME = "feed";

    private final Map<String,String> attributes = new HashMap<String, String>() {{
        // uri
        put("url", ""); // required
        put("thumbnail", null);
        // string
        put("uid", null);
        put("alias", null);
        put("classification", null);
        put("preferredMacAddress", null);
        // boolean
        put("active", null);
        put("rtspReliable", null);
        put("ignoreEmbeddedKLV", null);
        // short
        put("order", null);
        put("bitrate", null);
        put("timeout", null);
        put("buffer", null);
        // int
        put("width", null);
        put("height", null);
        put("roverPort", null);
        // float
        put("range", null);
        put("latitude", null);
        put("longitude", null);
        put("heading", null);
        put("fov", null);
    }};

    public VideoFeed() {}

    public void putAttribute(String key, String value) {
        if (attributes.containsKey(key))
            attributes.put(key, value);
    }

    public String getAttribute(String key) {
        return attributes.get(key);
    }

    public boolean hasAttribute(String key) {
        return attributes.containsKey(key);
    }

    public void display() {
        Intent intent = new Intent(VideoDropDownReceiver.DISPLAY);
        intent.putExtra("videoUrl", attributes.get("url"));

        for (String key : attributes.keySet()) {
            intent.putExtra(key, attributes.get(key));
        }

        AtakBroadcast.getInstance().sendBroadcast(intent);
    }
}