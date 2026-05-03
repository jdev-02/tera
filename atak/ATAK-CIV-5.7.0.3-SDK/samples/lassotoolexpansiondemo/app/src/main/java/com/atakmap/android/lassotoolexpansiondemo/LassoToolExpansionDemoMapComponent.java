
package com.atakmap.android.lassotoolexpansiondemo;

import android.content.Context;
import android.content.Intent;
import android.graphics.drawable.Drawable;
import android.widget.Toast;

import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.dropdown.DropDownMapComponent;

import com.atakmap.android.missionpackage.api.MissionPackageApi;
import com.atakmap.android.missionpackage.file.MissionPackageManifest;
import com.atakmap.android.missionpackage.lasso.LassoSelectionReceiver;
import com.atakmap.android.util.AttachmentManager;
import com.atakmap.coremap.log.Log;
import com.atakmap.android.lassotoolexpansiondemo.plugin.R;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class LassoToolExpansionDemoMapComponent extends DropDownMapComponent {

    private static final String TAG = "LassoToolExpansionDemoMapComponent";

    private Context pluginContext;

    private LassoSelectionReceiver.ExternalLassoCapability elc;

    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        context.setTheme(R.style.ATAKPluginTheme);
        super.onCreate(context, intent, view);
        pluginContext = context;

        LassoSelectionReceiver.registerExternalLassoCapability(elc = new LassoSelectionReceiver.ExternalLassoCapability() {
            @Override
            public String getUniqueIdentifier() {
                return UUID.randomUUID().toString();
            }

            @Override
            public Drawable getIcon() {
                return pluginContext.getDrawable(R.drawable.ic_launcher);
            }

            @Override
            public String getTitle() {
                return "Sample";
            }

            @Override
            public void process(List<Object> list) {
                final ArrayList<String> uids = new ArrayList<>();
                for (Object o: list) {
                    Log.d(TAG, "object: " + o);
                    if (o instanceof MapItem)
                        uids.add(((MapItem) o).getUID());
                }
                if (uids.isEmpty())
                    view.post(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(view.getContext(), "No Items Selected", Toast.LENGTH_SHORT).show();
                        }
                    });
                else {
                    MissionPackageManifest manifest = MissionPackageApi
                            .CreateTempManifest("transfer", true, true, null);
                    manifest.addMapItems(uids.toArray(new String[0]));
                    for (String uid : uids) {
                        manifest.addMapItem(uid);
                        List<File> attachments = AttachmentManager
                                .getAttachments(uid);
                        for (File attachment : attachments) {
                            manifest.addFile(attachment, uid);
                        }
                    }
                    MissionPackageApi.SendUIDs(view.getContext(), manifest,
                            (String)null, null, true);


                }

            }
        });
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        super.onDestroyImpl(context, view);
        LassoSelectionReceiver.unregisterExternalLassoCapability(elc);
    }

}
