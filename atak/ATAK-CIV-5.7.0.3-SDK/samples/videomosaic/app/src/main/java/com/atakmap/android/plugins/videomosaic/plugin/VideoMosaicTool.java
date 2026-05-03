
package com.atakmap.android.plugins.videomosaic.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.plugins.VideoOverlay.R;
import com.atakmap.android.plugins.videomosaic.VideoMosaicComponent;

public class VideoMosaicTool extends AbstractPluginTool {
    
    public VideoMosaicTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                VideoMosaicComponent.SHOW_VIDEO_OVERLAY_TOOL);


    }

}
