package com.atakmap.android.sms.chat;

import android.content.Context;

import com.atakmap.android.chat.ChatManagerMapComponent;
import com.atakmap.android.contact.Contact;
import com.atakmap.android.contact.ContactConnectorManager;
import com.atakmap.android.contact.Contacts;
import com.atakmap.android.contact.GroupContact;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.lang.Objects;


public class SmsConnectorHandler extends
        ContactConnectorManager.ContactConnectorHandler {

    private final static String TAG = "SmsConnectorHandler";

    public SmsConnectorHandler() {}

    @Override
    public boolean isSupported(String type) {
        return Objects.equals(SmsChatConnector.PLUGIN_CONNECTOR.getConnectionType(), type);
    }

    @Override
    public boolean hasFeature(
            ContactConnectorManager.ConnectorFeature feature) {
        return feature == ContactConnectorManager.ConnectorFeature.NotificationCount;
    }

    @Override
    public String getName() {
        return SmsChatConnector.CONNECTOR_TYPE;
    }

    @Override
    public String getDescription() {
        return "Connects device SMS with ATAK Contacts and Chat";
    }

    @Override
    public Object getFeature(String connectorType,
                             ContactConnectorManager.ConnectorFeature feature,
                             String contactUID, String connectorAddress) {

        if (feature == ContactConnectorManager.ConnectorFeature.NotificationCount) {
            Contact c = Contacts.getInstance().getContactByUuid(contactUID);
            if (c != null)
                return c.getExtras().getInt("unreadMessageCount", 0);
        }

        return null;
    }

    @Override
    public boolean handleContact(String connectorType, String contactUID,
                                 String address) {
        //TODO sometimes editable? Can that be determined later?
        //boolean editable = (mode != ContactListAdapter.ViewMode.HISTORY);

        if (!FileSystemUtils.isEmpty(contactUID)) {
            Log.d(TAG, "handleContact: " + contactUID + ", " + address);
            Contact list = Contacts.getInstance().getContactByUuid(contactUID);
            boolean editable = list == null || list.getExtras()
                    .getBoolean("editable", !(list instanceof GroupContact))
                    || list instanceof GroupContact
                    && !((GroupContact) list).getUnmodifiable();
            ChatManagerMapComponent.getInstance().openConversation(contactUID,
                    editable);

            //TODO is this step necessary?
            Contacts.getInstance().updateTotalUnreadCount();
            return true;
        }

        Log.w(TAG, "Unable to handleContact: " + contactUID + ", " + address);
        return false;
    }
}
