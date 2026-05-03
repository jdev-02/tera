package com.atakmap.android.sms.service;


// Declare any non-default types here with import statements

interface ILogger {

    void e(String tag, String msg, String exception);

    void d(String tag, String msg, String exception);

}

