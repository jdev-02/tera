package com.atakmap.android.sms.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPluginTool;
import com.atakmap.android.sms.SmsDropDownReceiver;

public class SmsPluginTool extends AbstractPluginTool {
    public SmsPluginTool(Context context) {
        super(context, "Start SMS Chat", "Starts SMS Chat with Contact", context.getDrawable(R.drawable.ic_launcher), SmsDropDownReceiver.ACTION_ADD_SMS_CONTACT);
    }
}
