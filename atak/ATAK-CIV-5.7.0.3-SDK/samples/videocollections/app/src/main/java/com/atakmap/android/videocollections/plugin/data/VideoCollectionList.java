package com.atakmap.android.videocollections.plugin.data;

import com.atakmap.android.maps.MapItem;
import com.atakmap.coremap.cot.event.CotAttribute;
import com.atakmap.coremap.cot.event.CotDetail;

import java.util.ArrayList;
import java.util.Iterator;

import gov.tak.api.util.AttributeSet;

public class VideoCollectionList extends ArrayList<VideoCollection> {

    public static final String ELEMENT_NAME = "videoCollections";
    public static final String DETAIL_NAME = "__" + ELEMENT_NAME;

    public VideoCollectionList() {
        super();
    }

    public VideoCollection getActive() {
        for (VideoCollection vc : this) {
            if (Boolean.parseBoolean(vc.getAttribute("active")))
                return vc;
        }
        return null;
    }

    public static VideoCollectionList fromCotDetail(CotDetail detail) {
        if (detail == null)
            return null;

        String name = detail.getElementName();
        if (!(name.equals(ELEMENT_NAME) || name.equals(DETAIL_NAME)))
            return null;

        VideoCollectionList videoCollectionList = new VideoCollectionList();

        for (CotDetail vcDetail : detail.getChildren()) {
            if (!vcDetail.getElementName().equals(VideoCollection.ELEMENT_NAME))
                continue;

            VideoCollection videoCollection = new VideoCollection();
            for (CotAttribute attr : vcDetail.getAttributes())
                videoCollection.putAttribute(attr.getName(), attr.getValue());

            for (CotDetail fDetail : vcDetail.getChildren()) {
                if (!fDetail.getElementName().equals(VideoFeed.ELEMENT_NAME))
                    continue;

                VideoFeed feed = new VideoFeed();
                for (CotAttribute attr : fDetail.getAttributes())
                    feed.putAttribute(attr.getName(), attr.getValue());

                videoCollection.feedList.add(feed);
            }
            videoCollectionList.add(videoCollection);
        }

        return videoCollectionList;
    }

    public static VideoCollectionList fromMapItem(MapItem item) {
        AttributeSet as = item.getMetaAttributeSet(ELEMENT_NAME);
        VideoCollectionList videoCollections = new VideoCollectionList();
        if (as != null)
           for (String name: as.getAttributeNames()) {
                videoCollections.add(new VideoCollection(as.getAttributeSetAttribute(name)));
            }

        return videoCollections;
    }

    public void putToMeta(MapItem item) {
        AttributeSet as = new AttributeSet();
        for (int i = 0; i < this.size(); ++i) {
            VideoCollection vc = this.get(i);
            as.setAttribute(Integer.toString(i), vc.getAttributeSet());
        }

        item.setMetaAttributeSet(ELEMENT_NAME, as);
    }
}
