package com.atakmap.android.platformsim.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;

public class PlatformSimulatorTool extends AbstractPluginTool {

    public PlatformSimulatorTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.weather),
                "com.atakmap.android.platformsim.SHOW_PLATFORM_SIM");
    }
}
