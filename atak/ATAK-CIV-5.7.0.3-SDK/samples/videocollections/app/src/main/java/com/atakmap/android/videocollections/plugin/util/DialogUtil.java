package com.atakmap.android.videocollections.plugin.util;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.text.TextUtils;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.EditText;

import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.video.VideoListDialog;
import com.atakmap.android.video.manager.VideoManager;
import com.atakmap.android.videocollections.plugin.R;
import com.atakmap.android.videocollections.plugin.data.VideoCollection;
import com.atakmap.android.videocollections.plugin.data.VideoCollectionList;
import com.atakmap.android.videocollections.plugin.data.VideoFeed;
import com.atakmap.android.videocollections.plugin.ui.VideoCollectionsInfoPane;

import java.util.ArrayList;
import java.util.List;

import gov.tak.api.video.ConnectionEntry;

public class DialogUtil {
    public static void showNewCollectionDialog(MapItem item, Context pluginCtx, VideoCollectionsInfoPane infoPane, List<VideoFeed> feeds) {
        View dialogView = LayoutInflater.from(pluginCtx).inflate(R.layout.dialog_video_collection, null);
        AlertDialog.Builder builder = new AlertDialog.Builder(MapView.getMapView().getContext())
                .setTitle("Add Video Collection")
                .setView(dialogView)
                .setCancelable(true)
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Confirm", new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int i) {
                        String  uid = ((EditText) dialogView.findViewById(R.id.edit_vc_uid)).getText().toString(),
                                alias = ((EditText) dialogView.findViewById(R.id.edit_vc_alias)).getText().toString();

                        if (TextUtils.isEmpty(uid) || TextUtils.isEmpty(alias)) {
                            // TODO: more detailed validation?
                            ToastUtil.show("Error: Invalid information");
                            dialog.dismiss();
                            return;
                        }

                        VideoCollectionList vcList = VideoCollectionList.fromMapItem(item);

                        VideoCollection vc = new VideoCollection();
                        vc.putAttribute("alias", alias);
                        vc.putAttribute("uid", uid);

                        if (feeds != null)
                            vc.feedList.addAll(feeds);

                        vcList.add(vc);
                        vcList.putToMeta(item);

                        infoPane.updateForItem(item);
                        dialog.dismiss();
                    }
                });
        builder.create().show();
    }

    public static void showNewFeedDialog(MapItem item, Context pluginCtx, VideoCollectionsInfoPane infoPane) {
        new VideoListDialog(MapView.getMapView())
                .show(null, VideoManager.getInstance().getConnectionEntries(null, false), true, new VideoListDialog.Callback() {
                    @Override
                    public void onVideosSelected(List<ConnectionEntry> list) {
                        VideoCollectionList vcList = VideoCollectionList.fromMapItem(item);
                        String[] choices = new String[vcList.size() + 1];

                        choices[0] = "Add a new collection";
                        for (int i = 0; i < vcList.size(); i++) {
                            VideoCollection vc = vcList.get(i);
                            choices[i + 1] = "" + i + ": " + vc.getAttribute("alias");
                        }

                        new AlertDialog.Builder(MapView.getMapView().getContext())
                                .setTitle("Select a Video Collection to Add To")
                                .setNegativeButton("Cancel", null)
                                .setSingleChoiceItems(choices, 0, new DialogInterface.OnClickListener() {
                                    @Override
                                    public void onClick(DialogInterface dialog, int i) {
                                        List<VideoFeed> feeds = new ArrayList<>();
                                        for (ConnectionEntry ce : list) {
                                            VideoFeed feed = new VideoFeed();
                                            feed.putAttribute("alias", ce.getAlias());
                                            String uri = ConnectionEntry.getURL(ce, false);
                                            if (ce.getProtocol() == ConnectionEntry.Protocol.FILE)
                                                uri = "file://" + uri;
                                            feed.putAttribute("url", uri);
                                            feeds.add(feed);
                                            Log.d("|>", ""+ce.getProtocol());
                                            Log.d("|>", feed.getAttribute("url"));
                                        }
                                        if (i == 0) {
                                            showNewCollectionDialog(item, pluginCtx, infoPane, feeds);
                                            dialog.dismiss();
                                            return;
                                        }
                                        vcList.get(i - 1).feedList.addAll(feeds);
                                        infoPane.updateForItem(item);
                                        dialog.dismiss();
                                    }
                                })
                                .create()
                                .show();
                    }
                });
    }
}
