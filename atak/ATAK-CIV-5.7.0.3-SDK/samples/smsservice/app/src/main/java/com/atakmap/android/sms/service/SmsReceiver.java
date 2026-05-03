package com.atakmap.android.sms.service;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.RemoteException;
import android.telephony.SmsMessage;

public class SmsReceiver extends BroadcastReceiver {
    private final static String TAG = "SmsReceiver";
    private ILogger log;
    private ISmsCallback callback;
    public SmsReceiver() {

    }

    public void register(ILogger log) {
        this.log = log;
    }

    public void register(ISmsCallback callback) {
        this.callback = callback;
    }

    public final String SMS_BUNDLE = "pdus";
    @Override
    public void onReceive(Context context, Intent intent) {
        Bundle intentExtras = intent.getExtras();

        try {
            log.d(TAG, "received sms", "");
        } catch (RemoteException ignored) { }

        if (intentExtras != null) {
            Object[] sms = (Object[]) intentExtras.get(SMS_BUNDLE);
            String smsMessageStr = "";
            for (int i = 0; i < sms.length; ++i) {
                String format = intentExtras.getString("format");
                SmsMessage smsMessage = SmsMessage.createFromPdu((byte[]) sms[i], format);

                String smsBody = smsMessage.getMessageBody().toString();
                String address = smsMessage.getOriginatingAddress();
                try {
                    callback.receivedSms(address, smsBody);
                } catch (RemoteException ignored) {
                    // error occurred
                }
            }
        }
    }
}
