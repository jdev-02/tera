
package com.atakmap.android.helloworld;

import android.graphics.Color;
import android.os.SystemClock;

import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.location.framework.Location;
import com.atakmap.android.location.framework.LocationDerivation;
import com.atakmap.android.location.framework.LocationProvider;
import com.atakmap.coremap.maps.coords.GeoCalculations;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.coremap.maps.coords.GeoPointMetaData;

import java.util.Random;
import java.util.Timer;
import java.util.TimerTask;

import gov.tak.api.cot.CoordinatedTime;

public class HelloworldLocationProvider extends LocationProvider {

    private static final String TAG = "HelloworldLocationProvider";

    boolean enabled;
    private final int GPS_VALIDITY_TIME = 5000;
    private Timer timer = new Timer();

    public HelloworldLocationProvider() {

        timer.schedule(new TimerTask() {
            @Override
            public void run() {
                if (enabled) {
                    Location lastLocation = getLastReportedLocation();
                    GeoPoint lastPoint;

                    if (lastLocation != null) {
                        lastPoint = lastLocation.getPoint();
                    } else {
                        lastPoint = new GeoPoint(50.1109,8.6821);
                    }

                    final GeoPoint newPoint =
                            GeoCalculations.pointAtDistance(lastPoint, Math.random() * 360, Math.random() * 30);
                    final Location l = new ManualEntryLocation(GeoPointMetaData.wrap(newPoint));
                    fireLocationChanged(l);
                }
            }
        }, 0, 1000);
    }




    @Override
    public String getUniqueIdentifier() {
        return "helloworld-location-provider";
    }

    @Override
    public String getTitle() {
        return "Helloworld Provider";
    }

    @Override
    public String getDescription() {
        return "Demonstration of Helloworld injecting new positons into ATAK";
    }

    @Override
    public String getSource() {
        return "Dummy Location";
    }

    @Override
    public String getSourceCategory() {
        return "USER";
    }

    @Override
    public int getSourceColor() {
        return Color.BLUE;
    }

    @Override
    public synchronized void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    @Override
    public boolean getEnabled() {
        return enabled;
    }

    @Override
    public void dispose() {
        timer.cancel();

    }



    class ManualEntryLocation implements Location {
        GeoPointMetaData point;

        ManualEntryLocation(GeoPointMetaData point) {
            this.point = point;
        }

        @Override
        public long getLocationDerivedTime() {
            return CoordinatedTime.currentTimeMillis();
        }

        @Override
        public GeoPoint getPoint() {
            return point.get();
        }

        @Override
        public double getBearing() {
            return Double.NaN;
        }

        @Override
        public double getSpeed() {
            return Double.NaN;
        }

        @Override
        public double getBearingAccuracy() {
            return Double.NaN;
        }

        @Override
        public double getSpeedAccuracy() {
            return Double.NaN;
        }

        @Override
        public int getReliabilityScore() {
            return 100;
        }

        @Override
        public String getReliabilityReason() {
            return "Human Entered";
        }

        @Override
        public LocationDerivation getDerivation() {
            return new LocationDerivation() {
                @Override
                public String getHorizontalSource() {
                    return GeoPointMetaData.USER;
                }

                @Override
                public String getVerticalSource() {
                    return point.getAltitudeSource();
                }
            };
        }

        @Override
        public boolean isValid() {
            // within the GPS timeout window
            return SystemClock.elapsedRealtime()
                    - getLastUpdated() < GPS_VALIDITY_TIME;
        }
    }

}
