
package com.atakmap.android.demoflavor.plugin;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.demoflavor.DemoFlavorDropDownReceiver;
import android.content.Context;
import gov.tak.api.util.Disposable;


public class DemoFlavorTool extends AbstractPluginTool implements Disposable {

    public DemoFlavorTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                DemoFlavorDropDownReceiver.SHOW_PLUGIN);
    }

    @Override
    public void dispose() {
    }
}
