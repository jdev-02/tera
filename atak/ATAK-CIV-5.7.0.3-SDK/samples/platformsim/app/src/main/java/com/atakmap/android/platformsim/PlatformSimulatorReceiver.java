
package com.atakmap.android.platformsim;

import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Point;
import android.graphics.PointF;
import android.preference.PreferenceManager;

import com.atakmap.android.gui.coordinateentry.CoordinateEntryCapability;
import com.atakmap.android.importexport.CotEventFactory;
import com.atakmap.android.maps.Marker;
import com.atakmap.coremap.log.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.Spinner;
import android.widget.Toast;

import com.atakmap.android.cot.CotMapComponent;
import com.atakmap.android.dropdown.DropDown.OnStateListener;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.maps.MapEvent;
import com.atakmap.android.maps.MapEventDispatcher.MapEventDispatchListener;
import com.atakmap.android.maps.MapTouchController;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.util.AltitudeUtilities;
import com.atakmap.android.platformsim.plugin.R;
import com.atakmap.coremap.conversions.CoordinateFormat;
import com.atakmap.coremap.conversions.CoordinateFormatUtilities;
import com.atakmap.coremap.conversions.Span;
import com.atakmap.coremap.conversions.SpanUtilities;
import com.atakmap.coremap.cot.event.CotEvent;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPointMetaData;
import com.atakmap.coremap.maps.coords.GeoCalculations;
import com.atakmap.map.elevation.ElevationManager;


import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.TimeZone;
import java.util.UUID;

public class PlatformSimulatorReceiver extends DropDownReceiver
        implements OnStateListener {
    public static String TAG = "PlatformSimulatorReceiver";
    //private static SimpleDateFormat TIME_FORMATTER = new SimpleDateFormat("HH':'mm':'ss");  Never used EMD
    public static final String SHOW_PLATFORM_SIM = "com.atakmap.android.platformsim.SHOW_PLATFORM_SIM";

    /**
     * Controls how the CoT messages are constructed -- either dynamically from
     * Marker/MapItem objects or by constructing the CoT XML by hand
     */
    private static boolean COT_FROM_MARKER = true;

    private View wxView;
    private MapView mapView;
    private Context pluginContext;
    private SharedPreferences _prefs;

    private Button platformSimOrbitCoordButton;
    private ImageButton platformSimOrbitCenterPickPointButton;
    private EditText platformSimRadiusEditText;
    private Spinner platformSimOrbitRadiusUnitSpinner;
    private ImageButton platformSimOrbitRadiusPickPointButton;
    private Button platformSimSpiCoordButton;
    private ImageButton platformSimSpiPickPointButton;
    private Button platformSimClearButton;
    private Button platformSimPauseButton;
    private Button platformSimResumeButton;

    private GeoPointMetaData orbitCenter;
    private GeoPointMetaData spi;
    private double orbitRadiusMeters;
    private boolean paused;
    private boolean disposed;

    public PlatformSimulatorReceiver(final MapView mapView,
            final Context context) {
        super(mapView);
        this.pluginContext = context;
        this.mapView = mapView;

        orbitCenter = null;
        spi = null;
        orbitRadiusMeters = 0d;
        paused = false;

        Log.d(TAG, "Starting WxReport Drop Down Receiver");
        LayoutInflater inflater = (LayoutInflater) context
                .getSystemService(context.LAYOUT_INFLATER_SERVICE);
        wxView = inflater.inflate(R.layout.platform_simulator_layout, null);
        _prefs = PreferenceManager
                .getDefaultSharedPreferences(mapView.getContext());

        this.disposed = false;

        Thread t = new Thread(new Simulator());
        t.setDaemon(true);
        t.setPriority(Thread.NORM_PRIORITY);
        t.start();
    }

    public synchronized void disposeImpl() {
        this.disposed = true;
        this.notify();
    }

    @Override
    public void onReceive(final Context context, Intent intent) {
        platformSimOrbitCoordButton = (Button) wxView
                .findViewById(R.id.platformSimOrbitCoordButton);
        platformSimOrbitCenterPickPointButton = (ImageButton) wxView
                .findViewById(R.id.platformSimOrbitCenterPickPointButton);
        platformSimRadiusEditText = (EditText) wxView
                .findViewById(R.id.platformSimRadiusEditText);
        platformSimOrbitRadiusUnitSpinner = (Spinner) wxView
                .findViewById(R.id.platformSimOrbitRadiusUnitSpinner);
        platformSimOrbitRadiusPickPointButton = (ImageButton) wxView
                .findViewById(R.id.platformSimOrbitRadiusPickPointButton);
        platformSimSpiCoordButton = (Button) wxView
                .findViewById(R.id.platformSimSpiCoordButton);
        platformSimSpiPickPointButton = (ImageButton) wxView
                .findViewById(R.id.platformSimSpiPickPointButton);
        platformSimClearButton = (Button) wxView
                .findViewById(R.id.platformSimClearButton);
        platformSimPauseButton = (Button) wxView
                .findViewById(R.id.platformSimPauseButton);
        platformSimResumeButton = (Button) wxView
                .findViewById(R.id.platformSimResumeButton);

        final CoordUpdateHandler orbitCenterPointHandler = new CoordUpdateHandler() {
            public void onCoordUpdated(final GeoPointMetaData point) {
                getMapView().post(new Runnable() {
                    public void run() {
                        platformSimOrbitRadiusPickPointButton
                                .setEnabled(point != null);
                    }
                });

                synchronized (PlatformSimulatorReceiver.this) {
                    orbitCenter = point;
                    PlatformSimulatorReceiver.this.notify();
                }
            }

            public GeoPointMetaData getPoint() {
                synchronized (PlatformSimulatorReceiver.this) {
                    return (orbitCenter != null) ? orbitCenter
                            : mapView.getCenterPoint();
                }
            }
        };
        addCoordButtonListener(getMapView(), pluginContext,
                platformSimOrbitCoordButton, _prefs, orbitCenterPointHandler);
        addCoordPickListener(getMapView(), pluginContext,
                platformSimOrbitCenterPickPointButton, _prefs,
                orbitCenterPointHandler);
        addCoordPickListener(getMapView(), pluginContext,
                platformSimOrbitRadiusPickPointButton, _prefs,
                new CoordUpdateHandler() {
                    public void onCoordUpdated(GeoPointMetaData point) {
                        synchronized (PlatformSimulatorReceiver.this) {
                            if (point == null || orbitCenter == null) {
                                orbitRadiusMeters = 0d;
                            } else {
                                orbitRadiusMeters = orbitCenter.get()
                                        .distanceTo(point.get());
                            }
                            PlatformSimulatorReceiver.this.notify();
                        }
                    }

                    public GeoPointMetaData getPoint() {
                        return null;
                    }
                });

        final CoordUpdateHandler spiPointHandler = new CoordUpdateHandler() {
            public void onCoordUpdated(final GeoPointMetaData point) {
                synchronized (PlatformSimulatorReceiver.this) {
                    spi = point;
                    PlatformSimulatorReceiver.this.notify();
                }
            }

            public GeoPointMetaData getPoint() {
                synchronized (PlatformSimulatorReceiver.this) {
                    return (spi != null) ? spi : mapView.getCenterPoint();
                }
            }
        };
        addCoordButtonListener(getMapView(), pluginContext,
                platformSimSpiCoordButton, _prefs, spiPointHandler);
        addCoordPickListener(getMapView(), pluginContext,
                platformSimSpiPickPointButton, _prefs, spiPointHandler);

        platformSimClearButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                synchronized (PlatformSimulatorReceiver.this) {
                    spi = null;
                    orbitCenter = null;
                    orbitRadiusMeters = 0d;
                    PlatformSimulatorReceiver.this.notify();
                }
            }
        });
        platformSimPauseButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                synchronized (PlatformSimulatorReceiver.this) {
                    paused = true;
                    PlatformSimulatorReceiver.this.notify();
                }
            }
        });
        platformSimResumeButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                synchronized (PlatformSimulatorReceiver.this) {
                    paused = false;
                    PlatformSimulatorReceiver.this.notify();
                }
            }
        });

        // If we receive an intent to show the weather GUI, set date/time
        if (intent.getAction().equals(SHOW_PLATFORM_SIM)) {
            showDropDown(wxView, HALF_WIDTH, FULL_HEIGHT, HALF_WIDTH,
                    FULL_HEIGHT, this);
        }
    }

    public void onDropDownSelectionRemoved() {
    }

    @Override
    public void onDropDownVisible(boolean v) {
    }

    @Override
    public void onDropDownSizeChanged(double width, double height) {
    }

    @Override
    public void onDropDownClose() {
        // GUI is closing, pop listeners to reactivate older ones
        Log.d(TAG, "Popping map event dispatch listeners");
        mapView.getMapEventDispatcher().popListeners();

        // Want other map events like clicks and long presses to be active, so unlock touch controller
        Log.d(TAG, "Unlocking touch controller");
        MapTouchController touchController = mapView.getMapTouchController();
        touchController.unlockControls();
    }

    private static void updateCoordButton(Context ctx, Button button,
            GeoPoint point, SharedPreferences prefs) {
        CoordinateFormat cFormat = CoordinateFormat.MGRS;
        final String coordDisplayPref = prefs.getString("coord_display_pref",
                ctx.getString(
                        com.atakmap.app.R.string.coord_display_pref_default));
        if (coordDisplayPref != null) {
            cFormat = CoordinateFormat.find(coordDisplayPref);
        }

        final String p = CoordinateFormatUtilities.formatToString(point,
                cFormat);
        final String a = AltitudeUtilities.format(point, prefs);
        button.setText(p + "\n" + a);
    }

    private static void addCoordButtonListener(final MapView mapView,
            final Context pluginCtx, final Button button,
            final SharedPreferences prefs, final CoordUpdateHandler handler) {
        final Context appCtx = mapView.getContext();

        Context ctx = MapView.getMapView().getContext();
        CoordinateEntryCapability.getInstance(ctx).showDialog(
                ctx.getString(com.atakmap.app.R.string.rb_coord_title),
                null, true,
                MapView.getMapView().getPointWithElevation(), null, false,
                new CoordinateEntryCapability.ResultCallback() {
                    @Override
                    public void onResultCallback(String s, GeoPointMetaData geoPointMetaData, String s1) {
                        handler.onCoordUpdated(geoPointMetaData);
                    }
                });
    }

    private static void addCoordPickListener(final MapView mapView,
            final Context pluginCtx, final ImageButton button,
            final SharedPreferences prefs, final CoordUpdateHandler handler) {
        final Context appCtx = mapView.getContext();
        button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Toast.makeText(mapView.getContext(),
                        "Select the point on the map", Toast.LENGTH_SHORT)
                        .show();

                mapView.getMapEventDispatcher().addMapEventListener(
                        MapEvent.MAP_CLICK, new MapEventDispatchListener() {

                            @Override
                            public void onMapEvent(MapEvent event) {
                                PointF p = event.getPointF();
                                if (p != null)
                                    handler.onCoordUpdated(
                                            mapView.inverseWithElevation(p.x, p.y));

                                // clean up the listener
                                mapView.getMapEventDispatcher()
                                        .removeMapEventListener(
                                                MapEvent.MAP_CLICK, this);
                            }
                        });
            }
        });
    }

    /**************************************************************************/

    private static interface CoordUpdateHandler {
        public void onCoordUpdated(GeoPointMetaData point);

        public GeoPointMetaData getPoint();
    }

    private class Simulator implements Runnable {
        public void run() {
            final String uid = UUID.randomUUID().toString();

            final double speedMPH = 85;
            final double speed = SpanUtilities.convert(
                    speedMPH,
                    Span.MILE,
                    Span.METER) / 3600d; // meters-per-second

            final long updateInterval = 33;
            double traveled = 0;
            GeoPoint orbitPath;
            long startTime = System.currentTimeMillis();
            int direction = -1; // 1 CW; -1 CCW

            GeoPointMetaData spiLocal;
            GeoPointMetaData orbitCenterLocal;
            double orbitRadiusLocal;

            while (true) {
                synchronized (PlatformSimulatorReceiver.this) {
                    if (disposed)
                        break;

                    boolean shouldWait = true;
                    shouldWait &= (spi == null);
                    shouldWait &= (orbitCenter == null);
                    shouldWait |= paused;

                    if (shouldWait) {
                        try {
                            PlatformSimulatorReceiver.this.wait();
                        } catch (InterruptedException ignored) {
                        }

                        // when resuming, reset the start time
                        startTime = System.currentTimeMillis();
                        continue;
                    }

                    spiLocal = spi;
                    orbitCenterLocal = orbitCenter;
                    orbitRadiusLocal = orbitRadiusMeters;
                }

                traveled += ((double) (System.currentTimeMillis() - startTime)
                        / 1000.0) * speed;
                startTime = System.currentTimeMillis();

                // compute the platform location based on the distance traveled
                if (orbitCenterLocal != null) {
                    orbitPath = GeoCalculations.pointAtDistance(
                            orbitCenterLocal.get(),
                            Math.toDegrees(traveled / orbitRadiusLocal)
                                    * direction,
                            orbitRadiusLocal);

                    Log.d(TAG, "test: " + ElevationManager.getElevationMetadata(orbitPath));
                    orbitPath = new GeoPoint(orbitPath, GeoPoint.Access.READ_WRITE);
                    // set height based on approximately 45deg elevation
                    orbitPath.set(Math.tan(Math.toRadians(45d))*orbitRadiusLocal);
                } else {
                    orbitPath = null;
                }

                // generate SPI
                if (spiLocal != null && spiLocal.get().isValid()) {
                    final String spiCOT = generateSPI(uid, "Platform Simulator SPI", spiLocal.get());
                    // broadcast the PPLI (platform location) internal (have it
                    // show on the user's map) AND send to all other ATAK users
                    // on the local network and TAK Server. We can toggle
                    // 'internal' and 'external' to control whether it gets
                    // processed and shown on the user's map or to other users
                    broadcastCoTMessage(spiCOT, true, true);
                }

                // generate PPLI
                if (orbitPath != null && orbitPath.isValid()) {
                    final String ppliCOT = generatePPLI(uid, "Platform Simulator", orbitPath);
                    // broadcast the PPLI (platform location) internal (have it
                    // show on the user's map) AND send to all other ATAK users
                    // on the local network and TAK Server. We can toggle
                    // 'internal' and 'external' to control whether it gets
                    // processed and shown on the user's map or to other users
                    broadcastCoTMessage(ppliCOT, true, true);
                }

                try {
                    Thread.sleep(updateInterval);
                } catch (InterruptedException ignored) {
                }
            }
        }
    }

    private static String generatePPLI(String uid, String callsign, GeoPoint loc) {
        if(COT_FROM_MARKER) {
            Marker ppli = generatePPLIMarker(uid, callsign, loc);

            // as is illustrated in the 'helloworld' plugin, a Marker instance
            // can be programmatically added to the map. we can also convert
            // a Marker instance (or any MapItem instance) into a CoT message
            // via the CotEventFactory class.
            final CotEvent event = CotEventFactory.createCotEvent(ppli);

            // check that a CoT event could be generated, if not, return null
            if(event == null)
                return null;

            return event.toString();
        } else {
            return generatePPLICoTMessage(uid, callsign, loc);
        }
    }

    private static Marker generatePPLIMarker(String uid, String callsign, GeoPoint loc) {
        long now = System.currentTimeMillis();

        SimpleDateFormat isoDateFormat = new SimpleDateFormat(
                "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
        isoDateFormat.setTimeZone(TimeZone.getTimeZone("GMT"));

        Date nowDate = new Date();
        String nowDateString = isoDateFormat.format(nowDate);

        // set the stale time 3 1/2 seconds from now
        nowDate.setTime(nowDate.getTime() + 3500);
        String staleDateString = isoDateFormat.format(nowDate);

        Marker ppli = new Marker(loc, uid);
        // the type of the marker, a = atom, f = friendly, A = aircraft
        ppli.setType("a-f-A");
        ppli.setTitle(callsign);


        // the following are optional, and map to CoT fields.

        // we need to set the "callsign" metadata value for conversion to CoT
        ppli.setMetaString("callsign", callsign);
        // we can optionally define the "how" -- how was the message generated.
        // "m-g" stands for Machine Generated
        ppli.setMetaString("how", "m-g");
        // when was the message created
        ppli.setMetaString("start", nowDateString);
        // when do we want the message to go "stale" -- staleness will be
        // displayed on other ATAK user's devices as a grayed out icon
        ppli.setMetaString("stale", staleDateString);

        return ppli;
    }

    private static String generatePPLICoTMessage(String uid, String callsign, GeoPoint loc) {
        long now = System.currentTimeMillis();

        SimpleDateFormat isoDateFormat = new SimpleDateFormat(
                "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
        isoDateFormat.setTimeZone(TimeZone.getTimeZone("GMT"));

        Date nowDate = new Date();
        String nowDateString = isoDateFormat.format(nowDate);

        // set the stale time 3 1/2 seconds from now
        nowDate.setTime(nowDate.getTime() + 3500);
        String staleDateString = isoDateFormat.format(nowDate);

        StringBuffer sb = new StringBuffer();
        sb.append(
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
                .append("<event version=\"2.0\" uid=\"")
                .append(uid)
                .append("\" type=\"a-f-A\" time=\"")
                .append(nowDateString)
                .append("\" start=\"")
                .append(nowDateString)
                .append("\" stale=\"")
                .append(staleDateString)
                .append("\" how=\"m-g\">")
                .append("<point lat=\"")
                .append(loc.getLatitude())
                .append("\" lon=\"")
                .append(loc.getLongitude())
                .append("\" hae=\"")
                .append(loc.getAltitude())
                .append("\" ce=\"9999999\" le=\"9999999\"/>")
                .append("<detail>")
                .append("<contact callsign=\"" + callsign + "\"/>")
                .append("</detail>")
                .append("</event>");

        return sb.toString();
    }

    private static String generateSPI(String uid, String callsign, GeoPoint loc) {
        if(COT_FROM_MARKER) {
            Marker spi = generateSPIMarker(uid, callsign, loc);

            // as is illustrated in the 'helloworld' plugin, a Marker instance
            // can be programmatically added to the map. we can also convert
            // a Marker instance (or any MapItem instance) into a CoT message
            // via the CotEventFactory class.
            final CotEvent event = CotEventFactory.createCotEvent(spi);

            // check that a CoT event could be generated, if not, return null
            if(event == null)
                return null;

            return event.toString();
        } else  {
            return generateSPICoTMessage(uid, callsign, loc);
        }
    }

    private static Marker generateSPIMarker(String uid, String callsign, GeoPoint loc) {
        long now = System.currentTimeMillis();

        SimpleDateFormat isoDateFormat = new SimpleDateFormat(
                "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
        isoDateFormat.setTimeZone(TimeZone.getTimeZone("GMT"));

        Date nowDate = new Date();
        String nowDateString = isoDateFormat.format(nowDate);

        // set the stale time 3 1/2 seconds from now
        nowDate.setTime(nowDate.getTime() + 3500);
        String staleDateString = isoDateFormat.format(nowDate);

        Marker spi = new Marker(loc, uid + ".SPI");
        // the type of the item -- this is the special type for SPI points
        spi.setType("b-m-p-s-p-i");
        spi.setTitle(callsign);


        // the following are optional, and map to CoT fields.

        // we need to set the "callsign" metadata value for conversion to CoT
        spi.setMetaString("callsign", callsign);
        // we can optionally define the "how" -- how was the message generated.
        // "m-g" stands for Machine Generated
        spi.setMetaString("how", "h-e");
        // when was the message created
        spi.setMetaString("start", nowDateString);
        // when do we want the message to go "stale" -- staleness will be
        // displayed on other ATAK user's devices as a grayed out icon
        spi.setMetaString("stale", staleDateString);

        // create the "link" by specifying the parent UID and type
        spi.setMetaString("parent_uid", uid);
        spi.setMetaString("parent_type", "a-f-A");

        return spi;
    }
    private static String generateSPICoTMessage(String uid, String callsign, GeoPoint loc) {
        long now = System.currentTimeMillis();

        SimpleDateFormat isoDateFormat = new SimpleDateFormat(
                "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
        isoDateFormat.setTimeZone(TimeZone.getTimeZone("GMT"));

        Date nowDate = new Date();
        String nowDateString = isoDateFormat.format(nowDate);
        nowDate.setTime(nowDate.getTime() + 3500);
        String staleDateString = isoDateFormat.format(nowDate);

        StringBuffer sb = new StringBuffer();
        sb.append(
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
                .append("<event version=\"2.0\" uid=\"")
                .append(uid).append(".SPI1")
                .append("\" type=\"b-m-p-s-p-i\" time=\"")
                .append(nowDateString)
                .append("\" start=\"")
                .append(nowDateString)
                .append("\" stale=\"")
                .append(staleDateString)
                .append("\" how=\"h-e\">")
                .append("<point lat=\"")
                .append(loc.getLatitude())
                .append("\" lon=\"")
                .append(loc.getLongitude())
                .append("\" hae=\"")
                .append(loc.getAltitude())
                .append("\" ce=\"9999999\" le=\"9999999\"/>")
                .append("<detail>")
                .append("<contact callsign=\"")
                .append(callsign)
                .append("\"/>")
                .append("<link relation=\"p-p\" uid=\"")
                .append(uid)
                .append("\" type=\"a-f-G-U-C\"/>")
                .append("<precisionlocation geopointsrc=\"Calc\" altsrc=\"DTED0\"/>")
                .append("</detail>")
                .append("</event>");

        return sb.toString();
    }

    /**
     * Broadcasts the specified CoT message. Internal broadcast is the pipeline
     * ATAK uses to process CoT messages received. Internal broadcast messages
     * will be parsed and show up on the user's map. External broadcast is the
     * transmit pipeline and will send the CoT message to all outputs configured
     * in ATAK, including any TAK server connections.
     *
     * @param internal  <code>true</code> to broadcast internal (receive on the
     *                  user's device).
     * @param external  <code>true</code> to broadcast external (send to all
     *                  ATAK users on the local network and any TAK Server
     *                  connections.
     */
    private static void broadcastCoTMessage(String cot, boolean internal, boolean external) {
        CotMapComponent.getExternalDispatcher()
                .dispatch(CotEvent.parse(cot));
        CotMapComponent.getInternalDispatcher()
                .dispatch(CotEvent.parse(cot));
    }
}
