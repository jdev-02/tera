package com.atakmap.android.sms;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.Toast;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.chat.ChatManagerMapComponent;
import com.atakmap.android.contact.Contact;
import com.atakmap.android.contact.Contacts;
import com.atakmap.android.contact.IndividualContact;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.preference.AtakPreferences;
import com.atakmap.android.sms.chat.SmsChatService;
import com.atakmap.android.sms.plugin.R;

public class SmsDropDownReceiver extends DropDownReceiver {

    public final static String ACTION_SHOW_PLUGIN = "com.atakmap.android.sms.SHOW_PLUGIN";
    public final static String ACTION_ADD_SMS_CONTACT = "com.atakmap.android.sms.ADD_SMS_CONTACT";
    public final static String ACTION_SEND_CHAT_SMS = "com.atakmap.android.sms.SEND_CHAT_SMS";
    final static String TAG = "SmsDropDownReceiver";
    final Context pluginContext;

    View mainLayout = null;

    SmsChatService smsChat;

    public SmsDropDownReceiver(MapView mapView, Context pluginContext, SmsChatService smsChat) {
        super(mapView);

        this.pluginContext = pluginContext;
        this.smsChat = smsChat;
    }

    @Override
    protected void disposeImpl() {

    }

    @Override
    public void onReceive(Context context, Intent intent) {
        switch(intent.getAction()) {
            case ACTION_SHOW_PLUGIN:
            {
                if(mainLayout == null) {
                    mainLayout = PluginLayoutInflater.inflate(pluginContext, R.layout.main_layout, null);

                    mainLayout.findViewById(R.id.startNewChat).setOnClickListener(new View.OnClickListener() {
                        @Override
                        public void onClick(View view) {
                            final Context appContext = getMapView().getContext();;
                            final EditText text = new EditText(appContext);
                            text.setInputType(InputType.TYPE_CLASS_NUMBER);
                            new AlertDialog.Builder(appContext)
                                        .setTitle("Add SMS Contact")
                                        .setCancelable(true)
                                        .setPositiveButton("OK", new DialogInterface.OnClickListener() {
                                            @Override
                                            public void onClick(DialogInterface dialogInterface, int i) {
                                                final IndividualContact contact = smsChat.addSmsContact(text.getText().toString());
                                                contact.onSelected(AtakPreferences.getInstance(appContext).getSharedPrefs());
                                            }
                                        })
                                        .setView(text)
                                        .create()
                                    .show();
                        }
                    });
                }
                showDropDown(mainLayout,
                        SmsDropDownReceiver.HALF_WIDTH, SmsDropDownReceiver.FULL_HEIGHT,
                        SmsDropDownReceiver.FULL_WIDTH, SmsDropDownReceiver.HALF_HEIGHT);
                break;
            }
            case ACTION_ADD_SMS_CONTACT:
            {
                final Context appContext = getMapView().getContext();;
                final EditText editText = new EditText(appContext);
                editText.setInputType(InputType.TYPE_CLASS_NUMBER);
                editText.postDelayed(new Runnable() {
                    @Override
                    public void run() {
                        editText.setOnFocusChangeListener(new View.OnFocusChangeListener() {
                            @Override
                            public void onFocusChange(View v, boolean hasFocus) {
                                editText.post(new Runnable() {
                                    @Override
                                    public void run() {
                                        InputMethodManager inputMethodManager= (InputMethodManager) getMapView().getContext().getSystemService(Context.INPUT_METHOD_SERVICE);
                                        inputMethodManager.showSoftInput(editText, InputMethodManager.SHOW_IMPLICIT);
                                    }
                                });
                            }
                        });
                        editText.requestFocus();
                    }
                }, 100);
                new AlertDialog.Builder(appContext)
                        .setTitle("Start SMS Chat")
                        .setCancelable(true)
                        .setPositiveButton("OK", new DialogInterface.OnClickListener() {
                            @Override
                            public void onClick(DialogInterface dialogInterface, int i) {
                                final IndividualContact contact = smsChat.addSmsContact(editText.getText().toString());
                                if(contact == null)
                                    Toast.makeText(appContext, "Invalid SMS Number: " + editText.getText(), Toast.LENGTH_LONG).show();
                                else
                                    contact.onSelected(AtakPreferences.getInstance(appContext).getSharedPrefs());
                            }
                        })
                        .setView(editText)
                        .create()
                        .show();
                break;
            }
            case ACTION_SEND_CHAT_SMS:
                final Bundle chatMessage = intent.getBundleExtra(ChatManagerMapComponent.PLUGIN_SEND_MESSAGE_EXTRA);
                if(chatMessage == null)
                    break;

                String text = chatMessage.getString("message");
                if(text == null)
                    break;

                String[] destinations = chatMessage.getStringArray("destinations");
                if(destinations == null)
                    break;

                for(String destination : destinations) {
                    Contact contact = Contacts.getInstance().getContactByUuid(destination);
                    if(!(contact instanceof IndividualContact))
                        continue;
                    smsChat.sendMessage((IndividualContact) contact, text);
                }
                break;
        }
    }
}
