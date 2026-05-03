package com.atakmap.android.sms.chat;

import android.content.Intent;
import android.os.Bundle;
import android.os.RemoteException;

import com.atakmap.android.chat.ChatDatabase;
import com.atakmap.android.contact.Connector;
import com.atakmap.android.contact.ContactPresenceDropdown;
import com.atakmap.android.contact.Contacts;
import com.atakmap.android.contact.IndividualContact;
import com.atakmap.android.contact.SmsConnector;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.sms.service.ISmsCallback;
import com.atakmap.android.sms.service.ISmsManager;
import com.atakmap.coremap.log.Log;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import gov.tak.api.contact.IContact;
import gov.tak.api.contact.IContactService;
import gov.tak.api.cot.CoordinatedTime;

public final class SmsChatService extends ISmsCallback.Stub {

    public static final String TAG = "SmsChatService";


    // DB
    private final ChatDatabase chatDb;

    private final MapView _mapView;
    private final IContactService _contactStore;

    private ISmsManager _smsService;

    final Map<String, IndividualContact> _smsContacts = new HashMap<>();

    public SmsChatService(MapView mapView, IContactService contactStore) {
        _mapView = mapView;
        chatDb = ChatDatabase.getInstance(null);
        _contactStore = contactStore;
        _smsService = null;

        if(_contactStore != null) {
            for(IContact contact : _contactStore.getAllContacts()) {
                if(contact instanceof IndividualContact) {
                    IndividualContact smsContact = (IndividualContact)contact;
                    Contacts.getInstance().addContact(smsContact);
                    _smsContacts.put(smsContact.getConnector(SmsConnector.CONNECTOR_TYPE).getConnectionString(), smsContact);
                }
            }
        }
    }

    static String sanitizeAddress(String address) {
        if(address.isEmpty())
            return null;
        do {
            address = address.replaceAll("[\\-\\(\\)\\s]", "");
            if(address.charAt(0) == '+')
                break;
            if(address.length() == 10)
                address = "1" + address;
            address = "+" + address;
        } while(false);
        if(!address.matches("\\+\\d{11}"))
            return null;
        return address;
    }
    public synchronized IndividualContact addSmsContact(String address) {
        address = sanitizeAddress(address);
        if(address == null)
            return null;
        IndividualContact contact = _smsContacts.get(address);
        if(contact == null) {
            _smsContacts.put(address, contact = new SmsContact(address));
            if(_contactStore != null)
                _contactStore.addContact(contact);
            Contacts.getInstance().addContact(contact);
        }
        return contact;
    }

    @Override
    public synchronized void receivedSms(String source, String message) {
        Log.d(TAG, source + " " + message);

        IndividualContact contact = addSmsContact(source);

        final String selfUid = _mapView.getSelfMarker().getUID();
        final String messageId = UUID.randomUUID().toString();

        final CoordinatedTime now = new CoordinatedTime();

        Bundle messageBundle = new Bundle();
        messageBundle.putString("conversationId", contact.getUid());
        messageBundle.putString("messageId", messageId);
        messageBundle.putStringArray("destinations", new String[] { selfUid });
        messageBundle.putString("parent", "RootContactGroup");
        messageBundle.putString("status", "NONE");
        messageBundle.putString("conversationName", contact.getName());
        messageBundle.putString("uid", selfUid);
        messageBundle.putString("senderUid", contact.getUid());
        messageBundle.putString("message", message);
        messageBundle.putLong("sentTime", now.getMilliseconds());
        messageBundle.putString("senderCallsign", contact.getTitle());

        chatDb.addChat(messageBundle);
        sendToUiLayer(messageBundle);

        //Log.d(TAG, "bundle contents\n" + bundle);
    }


    private void sendToUiLayer(Bundle chatMessageBundle) {
        //Log.d(TAG, "Sending Chat message to UI layer: " + chatMessageBundle);
        Intent gotNewChat = new Intent();
        gotNewChat.setAction("com.atakmap.android.chat.NEW_CHAT_MESSAGE");
        gotNewChat.putExtra("id", chatMessageBundle.getLong("id"));
        gotNewChat.putExtra("groupId", chatMessageBundle.getLong("groupId"));
        gotNewChat.putExtra("conversationId",
                chatMessageBundle.getString("conversationId"));
        AtakBroadcast.getInstance().sendBroadcast(gotNewChat);

        // Refresh chat drop-down (if it's open)
        AtakBroadcast.getInstance().sendBroadcast(new Intent(
                ContactPresenceDropdown.REFRESH_LIST));
    }

    /**
     * Given a cot message bundle and a destination, send the message out to
     * to the appropriate destination.
     * @param message the chat message content
     * @param destination individual contact destination to send the chat message to.
     */
    public void sendMessage(IndividualContact destination, String message) {
        final Connector sms = destination.getConnector(SmsChatConnector.CONNECTOR_TYPE);
        if(sms == null)
            return;

        try {
            _smsService.sendSMS(sms.getConnectionString(), message);
        } catch(RemoteException e) {
            Log.e(TAG, "Remote invocation error sending sms", e);
        }
    }

    public void setSmsManager(ISmsManager service) {
        _smsService = service;
    }
}
