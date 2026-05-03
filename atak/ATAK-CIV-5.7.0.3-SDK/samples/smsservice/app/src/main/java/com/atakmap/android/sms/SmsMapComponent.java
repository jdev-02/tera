
package com.atakmap.android.sms;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.IBinder;
import android.os.RemoteException;
import android.widget.Toast;

import com.atakmap.android.cot.CotMapComponent;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.maps.AbstractMapComponent;
import com.atakmap.android.maps.MapView;

import com.atakmap.android.sms.chat.SmsChatService;
import com.atakmap.android.sms.chat.SmsConnectorHandler;
import com.atakmap.android.sms.chat.SmsContactDatabase;
import com.atakmap.android.sms.service.ILogger;
import com.atakmap.android.sms.service.ISmsManager;
import com.atakmap.android.sms.service.PermissionActivity;
import com.atakmap.android.sms.service.SmsManagerService;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;
import com.atakmap.android.sms.plugin.R;

import java.io.File;


/**
 * Since this is an example, I will provide a drop down or other user experience in the
 * user interface
 */
public class SmsMapComponent extends AbstractMapComponent {

    private static final String TAG = "SmsMapComponent";

    private Context pluginContext;
    private MapView view;

    ISmsManager service;

    SmsChatService chatService;
    SmsConnectorHandler smsConnectorHandler;
    SmsContactDatabase smsContactDatabase;

    private final ILogger logger = new ILogger.Stub() {
        @Override
        public void e(String tag, String msg, String exception) {
            if (!FileSystemUtils.isEmpty(exception))
                msg = msg + "\n" + exception;
            Log.e(tag, msg);
        }

        @Override
        public void d(String tag, String msg, String exception) {
            if (!FileSystemUtils.isEmpty(exception))
                msg = msg + "\n" + exception;
            Log.d(tag, msg);
        }
    };

    private final ServiceConnection connection = new ServiceConnection() {
        @Override
        public void onServiceConnected(ComponentName className, IBinder iBinder) {

            service = ISmsManager.Stub.asInterface(iBinder);
            Log.d(TAG, "connected to the SMS service");
            chatService.setSmsManager(service);
            try {
                // register a logger so that logging text from the service can be added to the
                // ATAK logging subsystem.
                service.registerLogger(logger);
            } catch (RemoteException re) {
                Log.d(TAG, "error registering the remote logging capability", re);
            }

            try {
                // register the remove event listener
                service.registerReceiver(chatService);
            } catch (RemoteException re) {
                Log.d(TAG, "error registering the remote SMS listener", re);
            }

            MapView.getMapView().post(new Runnable() {
                @Override
                public void run() {
                    try {
                        requestPermissions();
                    } catch(RemoteException e) {
                        Log.d(TAG, "error obtaining permissions for the remote SMS listener", e);
                    }
                }
            });
        }

        @Override
        public void onServiceDisconnected(ComponentName arg0) {
            Log.d(TAG, "disconnected from the SMS service");
        }
    };

    private SmsDropDownReceiver ddr;

    public void onCreate(final Context context, Intent intent,
            final MapView view) {

        context.setTheme(R.style.ATAKPluginTheme);
        pluginContext = context;
        this.view = view;

        final File contactDbFile = FileSystemUtils.getItem("tools/smsservice/contacts.db");
        contactDbFile.getParentFile().mkdirs();
        smsContactDatabase = new SmsContactDatabase(contactDbFile.getAbsolutePath());
        chatService = new SmsChatService(view, smsContactDatabase);
        smsConnectorHandler = new SmsConnectorHandler();
        CotMapComponent.getInstance().getContactConnectorMgr()
                .addContactHandler(smsConnectorHandler);

        startService();

        this.ddr = new SmsDropDownReceiver(view, context, chatService);
        AtakBroadcast.DocumentedIntentFilter filter = new AtakBroadcast.DocumentedIntentFilter();
        filter.addAction(SmsDropDownReceiver.ACTION_SHOW_PLUGIN, "Shows SMS Chat Service");
        filter.addAction(SmsDropDownReceiver.ACTION_SEND_CHAT_SMS, "Sends SMS Chat message");
        filter.addAction(SmsDropDownReceiver.ACTION_ADD_SMS_CONTACT, "Starts new chat with SMS number");
        AtakBroadcast.getInstance().registerReceiver(ddr, filter);
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        AtakBroadcast.getInstance().unregisterReceiver(ddr);
        ddr = null;

        CotMapComponent.getInstance().getContactConnectorMgr()
                .removeContactHandler(smsConnectorHandler);

        stopService();

        smsContactDatabase.dispose();
    }

    private void requestPermissions() throws RemoteException{
        if (!service.hasPemissions()) {
            try {
                android.util.Log.i(TAG, "Requesting permission");
                Intent intent = new Intent(Intent.ACTION_MAIN);
                intent.setClassName(pluginContext.getPackageName(), PermissionActivity.class.getName());
                MapView.getMapView().getContext().startActivity(intent);
            } catch(Throwable t) {
                android.util.Log.e(TAG, "Failed to launch PermissionActivity", t);
            }
        }
    }

    void startService() {
        if(service != null) {
            Log.w(TAG, "SMS Service already started");
            return;
        }

        // kick off the service which is running in its own process space and governed by the
        // permissions in the plugins AndroidManifest.xml
        final Intent serviceIntent = new Intent(pluginContext, SmsManagerService.class);
        view.getContext().bindService(serviceIntent, connection, Context.BIND_AUTO_CREATE);

        Log.i(TAG, "SMS Service started");
    }

    void stopService() {
        if(service == null) {
            Log.w(TAG, "SMS Service already stopped");
            return;
        }

        try {
            service.killService();
        } catch(RemoteException e) {
            Log.e(TAG, "Failed to send SMS", e);
        }
        view.getContext().unbindService(connection);
        service = null;

        Log.i(TAG, "SMS Service stopped");
    }
}
