package com.atakmap.android.videocollections.plugin;

import com.atakmap.android.cot.detail.CotDetailHandler;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.videocollections.plugin.data.VideoCollectionList;
import com.atakmap.comms.CommsMapComponent;
import com.atakmap.coremap.cot.event.CotDetail;
import com.atakmap.coremap.cot.event.CotEvent;

import java.util.HashSet;

public class VideoCollectionsDetailHandler extends CotDetailHandler {

    protected VideoCollectionsDetailHandler() {
        super(new HashSet<String>() {{
            add(VideoCollectionList.ELEMENT_NAME);
            add(VideoCollectionList.DETAIL_NAME);
        }});
    }

    @Override
    public CommsMapComponent.ImportResult toItemMetadata(MapItem item, CotEvent event, CotDetail detail) {
        VideoCollectionList vcl = VideoCollectionList.fromCotDetail(detail);
        vcl.putToMeta(item);
        return CommsMapComponent.ImportResult.SUCCESS;
    }

    @Override
    public boolean toCotDetail(MapItem item, CotEvent event, CotDetail root) {
        return false;
    }
}
