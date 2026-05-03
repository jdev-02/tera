package com.atakmap.android.sms.chat;

import android.content.SharedPreferences;

import com.atakmap.android.contact.Connector;
import com.atakmap.android.contact.IndividualContact;
import com.atakmap.android.contact.SmsConnector;
import com.atakmap.android.maps.MapView;

/**
 * Represents an ATAK Contact list contact, for an XMPP buddy
 * Currently displayed only if available (online) and does not have a TAK User UID mapping b/c
 * in the latter case, the contact is already in the contact list
 */
public class SmsContact extends IndividualContact {

    private static final String TAG = "SmsContact";
    private static final String UID_PREFIX = "sms.";

    public SmsContact(String address) {
        super(address, UID_PREFIX + address);

        setDispatch(false);
        addConnector(new SmsConnector(address));
        addConnector(new SmsChatConnector(address));
        addConnector(SmsChatConnector.PLUGIN_CONNECTOR);
        setDispatch(true);
    }

    @Override
    public String getIconUri() {
        return "android.resource://"
                + MapView.getMapView().getContext().getPackageName()
                + "/" + com.atakmap.app.R.drawable.sms_icon;
    }

    @Override
    public Connector getDefaultConnector(SharedPreferences prefs) {
        return getConnector(SmsChatConnector.PLUGIN_CONNECTOR.getConnectionType());
    }
}
