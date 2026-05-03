
package com.atakmap.android.plugins;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.plugins.VideoOverlay.R;

public class VideoOverlayTool extends AbstractPluginTool {

    private Context context;

    public VideoOverlayTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                VideoOverlayComponent.SHOW_VIDEO_OVERLAY_TOOL);

    }
}
