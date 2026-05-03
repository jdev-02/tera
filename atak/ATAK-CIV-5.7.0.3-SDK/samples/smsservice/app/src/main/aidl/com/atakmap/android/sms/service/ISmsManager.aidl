package com.atakmap.android.sms.service;

import com.atakmap.android.sms.service.ISmsCallback;
import com.atakmap.android.sms.service.ILogger;

interface ISmsManager {

    /**
     * Send a SMS as designated by a destination phone number and a message
     * @param destination the destination of the SMS message
     * @param message the message body
     */
    void sendSMS(String destination, String message);

    /**
     * Unregisters a sensor listener as part of the sensor manager service.
     */
    void registerReceiver(ISmsCallback smsCallback);


    /**
     * Pass a logging mechanism over to the Service so that the logs can be written to the
     * appropriate logger.
     */
    void registerLogger(ILogger log);


    void killService();

    boolean hasPemissions();

}
