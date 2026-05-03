/*
 *  Copyright 2023 PAR Government Systems
 *
 *  Unlimited Rights:
 *  PAR Government retains ownership rights to this software.  The Government has Unlimited Rights
 *  to use, modify, reproduce, release, perform, display, or disclose this
 *  software as identified in the purchase order contract. Any
 *  reproduction of computer software or portions thereof marked with this
 *  legend must also reproduce the markings. Any person who has been provided
 *  access to this software must be aware of the above restrictions.
 */

package com.atakmap.android.windprovider.importwind;

import android.content.Context;

import com.atakmap.android.windprovider.importwind.parsers.WindParser;
import com.atakmap.android.windprovider.importwind.parsers.MarkSchulzeParser;
import com.atakmap.android.windprovider.importwind.parsers.NOAAParser;
import com.atakmap.android.windprovider.importwind.parsers.RyanCarltonParser;
import com.atakmap.android.windprovider.importwind.parsers.WindsAloftParser;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.locale.LocaleUtil;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.zip.GZIPInputStream;

import javax.net.ssl.HttpsURLConnection;

/**
 * Supports downloading and parsing wind data from a Wind Server configured in wind_servers.xml
 */
public class OnlineWindImport {

    private static final String TAG = "OnlineWindImport";

    public interface WindReceiver {
        void receivedWindFromServer(List<WindInfo> winds);
        void receivedPressureQNH(double qnh);
        void error(String msg);
        void completed();
    }

    private static final ArrayList<WindParser> parsers = new ArrayList<>();
    private final Context con;

    public OnlineWindImport(Context context) {
        con = context;
        parsers.add(new NOAAParser(con));
        parsers.add( new WindsAloftParser(con));
        parsers.add(new MarkSchulzeParser(con));
        parsers.add(new RyanCarltonParser(con));
    }

    public List<WindParser> getParsers() {
        return new ArrayList<>(parsers);
    }

    public void getWinds(WindParser parser, GeoPoint point, int offset, boolean pressureOnly,
                         WindReceiver wr) {
        Thread t = new RequestWindImportTask(parser, point, offset, pressureOnly, wr);
        t.start();
    }


    private static class RequestWindImportTask extends Thread {
        private final static String TAG = "RequestWindImportTask";

        private final WindReceiver windReceiver;
        private final WindParser parser;
        private String errorMsg;
        private final int hourOffset;
        private final boolean pressureOnly;
        private final GeoPoint location;


        RequestWindImportTask(final WindParser parser,
                              final GeoPoint point,
                              final int offset,
                              final boolean pressureOnly,
                              final WindReceiver windReceiver) {
            this.parser = parser;
            this.hourOffset = offset;
            this.pressureOnly = pressureOnly;
            this.location = point;
            this.windReceiver = windReceiver;
        }

        public void run() {
            String urlString = parser.url(location, hourOffset);
            String responseString = null;

            if (urlString.toLowerCase(LocaleUtil.getCurrent()).startsWith(
                    "https")) {
                responseString = getWindDataStandard(urlString);

            } else {
                HttpURLConnection urlConnection = null;
                try {
                    URL url = new URL(urlString);
                    urlConnection = (HttpURLConnection) url.openConnection();
                    InputStream in = new BufferedInputStream(urlConnection.getInputStream());
                    byte[] array = read(in);
                    try {
                        array = decompress(array);
                    } catch (Exception e) {
                        Log.d(TAG, "could not decompress");
                    }
                    responseString = new String(array,
                            FileSystemUtils.UTF8_CHARSET);
                } catch (IOException e) {
                    Log.e(TAG, "error", e);
                } finally {
                    assert urlConnection != null;
                    urlConnection.disconnect();
                }
            }

            if (pressureOnly) {
                if (parser instanceof MarkSchulzeParser) {
                    try {
                        double qnh = ((MarkSchulzeParser) parser)
                                .getQNH(responseString);
                        windReceiver.receivedPressureQNH(qnh);
                    } catch (Exception e) {
                        windReceiver.error(errorMsg);
                    }
                }
            } else {
                parseWinds(responseString);
            }

            windReceiver.completed();

        }

        /**
         * Gets wind data using the standard java capabilities which will verify against
         * the system trust store (default behavior) or will utilize the TAK server CA to
         * verify trust if a proxy is in use.
         */
        public String getWindDataStandard(String urlString) {

            String responseString;
            try {
                URL url = new URL(urlString);
                HttpsURLConnection conn = (HttpsURLConnection) url
                        .openConnection();
                conn.setRequestProperty("User-Agent", "TAK");

                // set Timeout and method
                conn.setReadTimeout(17000);
                conn.setConnectTimeout(17000);

                conn.connect();

                InputStream is = conn.getInputStream();

                try {
                    byte[] array = read(is);
                    try {
                        array = decompress(array);
                    } catch (Exception e) {
                        Log.d(TAG, "could not decompress");
                    }
                    responseString = new String(array,
                            FileSystemUtils.UTF8_CHARSET);
                    return responseString;
                } finally {
                    is.close();
                    conn.disconnect();
                }
            } catch (MalformedURLException | ClassCastException
                     | NullPointerException e) {
                Log.e(TAG, "error", e);
                return null;
            } catch (IOException e1) {
                Log.e(TAG, "error", e1);
                if (e1.getMessage() != null && e1.getMessage().contains("validation time:")) {
                    errorMsg = "Could not connect to server.\\u0020Check that device date is correct.";
                }
                return null;
            }
        }

        public byte[] read(InputStream is) throws IOException {
            ByteArrayOutputStream buffer = new ByteArrayOutputStream();

            int nRead;
            byte[] data = new byte[16384];

            while ((nRead = is.read(data, 0, data.length)) != -1) {
                buffer.write(data, 0, nRead);
            }

            buffer.flush();

            return buffer.toByteArray();
        }

        public byte[] decompress(byte[] array) throws IOException {
            return read(new GZIPInputStream(new ByteArrayInputStream(array)));
        }

        /**
         * Parse out the wind data from the response
         *
         * @param data - the string value of the wind data received
         */
        private void parseWinds(final String data) {

            // if no data was received
            if (data == null) {
                windReceiver.error("no data was received");
            }

            List<WindInfo> windInfo;
            try {
                windInfo = parser.parse(new ByteArrayInputStream(
                        data.getBytes(FileSystemUtils.UTF8_CHARSET)));
                Collections.sort(windInfo);
                windReceiver.receivedWindFromServer(windInfo);
            } catch (Exception e) {
                Log.e(TAG, "Error parsing values", e);
                Log.e(TAG, "server response:  ####" + data + "####");
                windReceiver.error("error parsing values");
            }
        }
    }
}
