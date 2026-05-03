package com.atakmap.android.sms.service;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.widget.Toast;

/**
 * This is an Activity launched by the Service in order to set permissions.
 */
public class PermissionActivity extends Activity {
    private static final int READ_SMS_PERMISSIONS_REQUEST = 62753;
    @Override
    protected void onCreate(Bundle savedBundle) {
        super.onCreate(savedBundle);
        requestPermissions(new String[]{
                Manifest.permission.READ_SMS,
                Manifest.permission.SEND_SMS,
                Manifest.permission.RECEIVE_SMS},
                READ_SMS_PERMISSIONS_REQUEST);
    }
    @Override
    protected void onDestroy() {
        super.onDestroy();
    }

    public void onRequestPermissionsResult(int requestCode,
                                           String permissions[],
                                            int[] grantResults) {
        // Make sure it's our original READ_CONTACTS request
        if (requestCode == READ_SMS_PERMISSIONS_REQUEST) {
            if (grantResults.length == 3 &&
                    grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "Read SMS permission granted", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "Read SMS permission denied", Toast.LENGTH_SHORT).show();
            }
            finish();
        } else {
            super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        }
    }
}
