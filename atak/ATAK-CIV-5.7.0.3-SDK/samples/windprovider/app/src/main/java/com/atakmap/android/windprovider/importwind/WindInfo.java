package com.atakmap.android.windprovider.importwind;

import static java.lang.Math.round;

import androidx.annotation.NonNull;

import com.atakmap.coremap.conversions.ConversionFactors;

import java.util.Objects;

/**
 * Object used to fill UI with wind information.
 */
public class WindInfo implements Comparable<WindInfo> {
    private final int altitude;
    private final int direction;
    private final int speed;

    /**
     * @param altitude  Altitude in feet.
     * @param direction Direction of wind relative to compass direction.
     * @param speed     Speed of wind in knots.
     */
    public WindInfo(final int altitude, final int direction, final int speed) {
        this.altitude = altitude;
        this.direction = direction;
        this.speed = speed;
    }

    @Override
    public int compareTo(WindInfo windInfo) {
        return Integer.compare(this.altitude, windInfo.getAltitude());
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        WindInfo windInfo = (WindInfo) o;
        return altitude == windInfo.altitude;
    }

    @Override
    public int hashCode() {
        return Objects.hash(altitude);
    }

    @NonNull
    @Override
    public String toString() {
        return "WindInfo{" +
                "altitude=" + altitude +
                ", direction=" + direction +
                ", speed=" + speed +
                '}';
    }

    /**
     * Returns the altitude associated with this wind info entry
     *
     * @return the altitude in feet
     */
    public int getAltitude() {
        return altitude;
    }

    /**
     * Returns the meteorological wind direction associated with this wind info entry
     *
     * @return Meteorological wind direction is defined as the direction from which it originates.
     */
    public int getDirection() {
        return direction;
    }


    /**
     * Returns the speed associated with this wind info entry
     *
     * @return the speed in knots
     */
    public int getSpeed() {
        return speed;
    }
}

