
package com.atakmap.android.radialmenudemo.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.radialmenudemo.DropdownMenuReceiver;

import gov.tak.api.util.Disposable;

public class RadialMenuDemoTool extends AbstractPluginTool implements Disposable {

    public RadialMenuDemoTool(final Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                DropdownMenuReceiver.SHOW_PLUGIN);
    }

    @Override
    public void dispose() {

    }
}
