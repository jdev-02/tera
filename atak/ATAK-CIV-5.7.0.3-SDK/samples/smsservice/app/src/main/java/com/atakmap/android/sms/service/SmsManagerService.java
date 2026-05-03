package com.atakmap.android.sms.service;

import android.Manifest;
import android.app.Service;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.IBinder;
import android.os.RemoteException;
import android.provider.Telephony;
import android.telephony.SmsManager;
import android.telephony.SubscriptionManager;

import androidx.annotation.Nullable;

/**
 * This service runs completely devoid of all ATAK supplied classes.   It also inherits the
 * permissions from the AndroidManifest because it is a service.
 */
public class SmsManagerService extends Service {

    private static final String TAG = "SmsManagerService";

    private ILogger log;
    private ISmsCallback callback;
    private SmsReceiver smsReceiver = new SmsReceiver();

    @Override
    public void onCreate() {
        super.onCreate();
        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction(Telephony.Sms.Intents.SMS_RECEIVED_ACTION);
        intentFilter.setPriority(2147483647);
        registerReceiver(smsReceiver,intentFilter);
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return mBinder;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        unregisterReceiver(smsReceiver);
    }


    /**
     * The remote implementation of the Sms Manager with contains the registration of the logger
     * as well as the registration and of the sms receiver.
     */
    private final ISmsManager.Stub mBinder = new ISmsManager.Stub() {
        @Override
        public void registerLogger(final ILogger log) throws RemoteException {
            SmsManagerService.this.log = log;
            smsReceiver.register(log);
        }

        @Override
        public void registerReceiver(ISmsCallback smsCallback) throws RemoteException {
            SmsManagerService.this.callback = smsCallback;
            smsReceiver.register(callback);
        }

        @Override
        public void sendSMS(String destination, String message) throws RemoteException {
            final SmsManager smsManager = SmsManager.getDefault();

            smsManager.sendTextMessage(destination, null, message, null, null);
            if (log != null) {
                log.d(TAG, "sent the sms", "");
            }
        }

        @Override
        public void killService() {
            SmsManagerService.this.stopSelf();
        }

        @Override
        public boolean hasPemissions() {
            return checkSelfPermission( Manifest.permission.READ_SMS)
                    == PackageManager.PERMISSION_GRANTED;
        }
    };
}
