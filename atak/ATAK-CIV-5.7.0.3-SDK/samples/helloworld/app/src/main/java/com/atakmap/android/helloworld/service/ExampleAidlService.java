
package com.atakmap.android.helloworld.service;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.os.RemoteException;

import androidx.annotation.Nullable;

import com.atakmap.android.helloworld.aidl.ILogger;
import com.atakmap.android.helloworld.aidl.SimpleService;

/**
 * Please note, this service does not run in the same process space as ATAK and therefore does not
 * have access to the ATAK supplied classes, for example GeoPoint.
 * This is a simple example on how to use AIDL between a plugin and a service that exists in the
 * same apk.
 */
public class ExampleAidlService extends Service {

    private final String TAG = "ExampleAidlService";

    private ExampleAidlImpl exampleAidlService;

    @Override
    public void onCreate() {
        super.onCreate();
        exampleAidlService = new ExampleAidlImpl();
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return exampleAidlService;
    }

    public class ExampleAidlImpl extends SimpleService.Stub {

        com.atakmap.android.helloworld.aidl.ILogger log;

        @Override
        public void registerLogger(final ILogger log) throws RemoteException {
            this.log = log;
        }

        @Override
        public int add(int a, int b) throws RemoteException {
            if (log != null) {
                log.d(TAG, "preparing warp drive calculator for a=" + a + ", b="
                        + b, "");
            }
            return a + b;
        }
    }
}
