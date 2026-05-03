package com.atakmap.android.videocollections.plugin.ui;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.videocollections.plugin.R;
import com.atakmap.android.videocollections.plugin.data.VideoCollection;
import com.atakmap.android.videocollections.plugin.data.VideoCollectionList;
import com.atakmap.android.videocollections.plugin.data.VideoFeed;
import com.atakmap.android.videocollections.plugin.util.DialogUtil;

public class VideoCollectionsInfoPane extends DropDownReceiver {

    private final Context pluginCtx;
    private final View mainView;

    private MapItem currentItem = null;

    public VideoCollectionsInfoPane(MapView mapView, Context pluginCtx) {
        super(mapView);
        this.pluginCtx = pluginCtx;
        this.mainView = PluginLayoutInflater.inflate(pluginCtx, R.layout.video_collections_layout, null);
    }

    public void show(MapItem item) {
        String title = "Video Collections for " + item.get("callsign");
        ((TextView) mainView.findViewById(R.id.title)).setText(title);

        mainView.findViewById(R.id.add_feed_btn).setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                DialogUtil.showNewFeedDialog(item, pluginCtx, VideoCollectionsInfoPane.this);
            }
        });

        LinearLayout collectionListView = mainView.findViewById(R.id.video_collection_list);
        collectionListView.removeAllViews();

        VideoCollectionList vcList = VideoCollectionList.fromMapItem(item);

        for (int i = 0; i < vcList.size(); i++) {
            final int vcIdx = i;
            VideoCollection vc = vcList.get(i);

            View collectionItemView = PluginLayoutInflater
                    .inflate(pluginCtx, R.layout.video_collection_list_item, null);
            ((TextView) collectionItemView.findViewById(R.id.collection_alias)).setText(vc.getAttribute("alias"));

            collectionItemView.findViewById(R.id.btn_remove_vc).setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    new AlertDialog.Builder(MapView.getMapView().getContext())
                            .setTitle("Confirm collection delete")
                            .setPositiveButton("Confirm", new DialogInterface.OnClickListener() {
                                @Override
                                public void onClick(DialogInterface dialogInterface, int i) {
                                    VideoCollectionList vcList = VideoCollectionList.fromMapItem(item);
                                    vcList.remove(vcIdx);
                                    vcList.putToMeta(item);

                                    updateForItem(item);
                                }
                            })
                            .setNegativeButton("Cancel", null)
                            .create().show();
                }
            });

            LinearLayout feedListView = collectionItemView.findViewById(R.id.feed_list);

            for (int j = 0; j < vc.feedList.size(); j++) {
                final int feedIdx = j;
                VideoFeed feed = vc.feedList.get(j);

                View feedItemView = PluginLayoutInflater
                        .inflate(pluginCtx, R.layout.feed_list_item, null);

                String feedAlias = feed.hasAttribute("alias") ? feed.getAttribute("alias") : "<Unnamed Feed>";
                ((TextView) feedItemView.findViewById(R.id.feed_alias)).setText(feedAlias);
                ((TextView) feedItemView.findViewById(R.id.feed_url)).setText(feed.getAttribute("url"));

                feedItemView.findViewById(R.id.play_btn).setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        feed.display();
                    }
                });

                feedItemView.findViewById(R.id.btn_remove_feed).setOnClickListener(new View.OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        new AlertDialog.Builder(MapView.getMapView().getContext())
                                .setTitle("Confirm feed delete")
                                .setPositiveButton("Confirm", new DialogInterface.OnClickListener() {
                                    @Override
                                    public void onClick(DialogInterface dialogInterface, int i) {
                                        VideoCollectionList vcList = VideoCollectionList.fromMapItem(item);
                                        vcList.get(vcIdx).feedList.remove(feedIdx);
                                        vcList.putToMeta(item);

                                        updateForItem(item);
                                    }
                                })
                                .setNegativeButton("Cancel", null)
                                .create().show();
                    }
                });

                feedListView.addView(feedItemView);
            }

            collectionListView.addView(collectionItemView);
        }

        currentItem = item;

        if (!isVisible()) {
            showDropDown(mainView, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH, HALF_HEIGHT, false);
            setRetain(true);
        }
    }

    public void updateForItem(MapItem item) {
        if (isVisible() && currentItem == item)
            show(item);
    }

    @Override
    protected void disposeImpl() {}

    @Override
    public void onReceive(Context context, Intent intent) {}
}