package com.atakmap.android.elevation.dsm.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;

public class DSMManagerTool extends AbstractPluginTool {

    public DSMManagerTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.dsm),
                                "com.atakmap.android.elevation.dsm.SHOW_DSM_MANAGER");
    }
}
