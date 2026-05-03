// INotificationService.aidl
package com.atakmap.android.helloworld.aidl;

import com.atakmap.android.helloworld.aidl.ILogger;


interface SimpleService {



    /**
     * Pass a logging mechanism over to the Service so that the logs can be written to the
     * appropriate logger.
     */
    void registerLogger(ILogger log);

    /**
     * Adds two numbers and returns the result.
     */
    int add(int a, int b);
}
