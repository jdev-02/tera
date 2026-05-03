
package com.atakmap.android.plugintemplate.plugin;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.plugintemplate.PluginTemplateDropDownReceiver;
import android.content.Context;
import gov.tak.api.util.Disposable;


public class PluginTemplateTool extends AbstractPluginTool implements Disposable {

    public PluginTemplateTool(Context context) {
        super(context,
                context.getString(R.string.app_name),
                context.getString(R.string.app_name),
                context.getResources().getDrawable(R.drawable.ic_launcher),
                PluginTemplateDropDownReceiver.SHOW_PLUGIN);
    }

    @Override
    public void dispose() {
    }
}
