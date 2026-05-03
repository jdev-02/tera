package com.atakmap.android.sms.service;


// Declare any non-default types here with import statements

interface ISmsCallback {

    void receivedSms(String source, String message);

}

