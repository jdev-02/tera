package com.atakmap.android.windprovider.importwind;

public class WindParseException extends Exception {

    public WindParseException(String msg) {
        super(msg);
    }

    public WindParseException(String msg, Exception initCause) {
        super(msg, initCause);
    }

}
