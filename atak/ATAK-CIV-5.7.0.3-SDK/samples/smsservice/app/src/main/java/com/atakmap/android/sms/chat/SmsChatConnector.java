package com.atakmap.android.sms.chat;

import com.atakmap.android.contact.Connector;
import com.atakmap.android.contact.PluginConnector;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.sms.SmsDropDownReceiver;
import com.atakmap.app.R;

public class SmsChatConnector extends Connector {
    public final static Connector PLUGIN_CONNECTOR = new SmsChatConnector(SmsDropDownReceiver.ACTION_SEND_CHAT_SMS) {
        @Override
        public String getConnectionType() {
            return PluginConnector.CONNECTOR_TYPE;
        }
    };

    public final static String CONNECTOR_TYPE = "connector.smschat";

    private final String _smsAddress;

    public SmsChatConnector(final String smsAddress) {
        _smsAddress = smsAddress;
    }

    @Override
    public String getConnectionString() {
        return _smsAddress;
    }

    @Override
    public String getConnectionType() {
        return CONNECTOR_TYPE;
    }

    @Override
    public String getConnectionLabel() {
        return "SMS";
    }

    @Override
    public String getIconUri() {
        return GetIconUri();
    }

    public static String GetIconUri() {
        return "android.resource://"
                + MapView.getMapView().getContext()
                .getPackageName()
                + "/"
                + R.drawable.sms_icon;
    }

    @Override
    public int getPriority() {
        return 2;
    }
}

