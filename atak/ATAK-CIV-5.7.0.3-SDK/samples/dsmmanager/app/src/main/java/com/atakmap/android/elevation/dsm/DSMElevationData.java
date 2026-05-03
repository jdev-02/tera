
package com.atakmap.android.elevation.dsm;

import com.atakmap.coremap.conversions.Span;
import com.atakmap.coremap.conversions.SpanUtilities;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.elevation.AbstractElevationData;
import com.atakmap.map.elevation.ElevationChunk;
import com.atakmap.map.elevation.ElevationData;
import com.atakmap.map.elevation.ElevationDataSpi;
import com.atakmap.map.gdal.GdalElevationChunk;
import com.atakmap.map.gdal.GdalLibrary;
import com.atakmap.map.layer.raster.DatasetProjection2;
import com.atakmap.map.layer.raster.DefaultDatasetProjection2;
import com.atakmap.map.layer.raster.ImageInfo;
import com.atakmap.math.PointD;

import org.gdal.gdal.Dataset;

import java.util.Arrays;
import java.util.Iterator;

import gov.tak.api.engine.map.coords.GeoCalculations;

public final class DSMElevationData extends AbstractElevationData {

    public final static ElevationDataSpi SPI = new ElevationDataSpi() {

        @Override
        public ElevationData create(ImageInfo object) {
            ElevationInfo info = DSMManager.getDb()
                    .getElevationInfo(object.path);
            if (info == null)
                return null;
            return new DSMElevationData(info);
        }

        @Override
        public int getPriority() {
            return 2;
        }
    };

    private final ElevationInfo info;
    private final DatasetProjection2 proj;

    DSMElevationData(ElevationInfo info) {
        super(info.model, info.type, info.maxGsd);

        this.info = info;
        this.proj = new DefaultDatasetProjection2(info.srid,
                info.width,
                info.height,
                info.upperLeft,
                info.upperRight,
                info.lowerRight,
                info.lowerLeft);
    }

    @Override
    public double getResolution() {
        return this.info.maxGsd;
    }

    @Override
    public double getElevation(double latitude, double longitude) {
        PointD img = new PointD(0d, 0d);
        if (!this.proj.groundToImage(new GeoPoint(latitude, longitude), img))
            return Double.NaN;

        ElevationChunk chunk = null;
        try {
            Dataset dataset = GdalLibrary.openDatasetFromPath(this.info.datasetUri != null ?
                    this.info.datasetUri : this.info.path);
            if (dataset == null)
                return Double.NaN;

            chunk = GdalElevationChunk.create(dataset, true, type, info.maxGsd, info.model, false);
            double height = chunk.sample(latitude, longitude);
            // required return is to be in HAE - but the underlying database stored it as  either HAE or MSL

            if (this.info.reference.equals("MSL")) {
                height = GeoCalculations.mslToHae(latitude,
                        longitude, height);
            }
            return SpanUtilities.convert(height, this.info.units, Span.METER);
        } catch (Throwable t) {
            return Double.NaN;
        } finally {
            if (chunk != null)
                chunk.dispose();
        }
    }

    @Override
    public void getElevation(Iterator<GeoPoint> points, double[] elevations,
            Hints hints) {

        ElevationChunk chunk = null;
        try {
            Dataset dataset = GdalLibrary.openDatasetFromPath(this.info.datasetUri != null ?
                    this.info.datasetUri : this.info.path);
            if (dataset == null) {
                Arrays.fill(elevations, Double.NaN);
                return;
            }

            chunk = GdalElevationChunk.create(dataset, true, type, info.maxGsd, info.model, false);
            if(chunk == null) {
                Arrays.fill(elevations, Double.NaN);
                return;
            }

            double[] lla = new double[elevations.length*3];
            int count = 0;
            while(points.hasNext()) {
                GeoPoint p = points.next();
                lla[count*3+1] = p.getLatitude();
                lla[count*3] = p.getLongitude();
                lla[count*3+2] = Double.NaN;
                count++;
            }

            final boolean mslToHae = this.info.reference.equals("MSL");
            chunk.sample(lla, 0, count);
            for(int i = 0; i < count; i++) {
                double height = lla[i*3+2];
                if (mslToHae) {
                    height = GeoCalculations.mslToHae(lla[i*3+1],
                            lla[i*3], height);
                }
                elevations[i] = SpanUtilities.convert(height, this.info.units, Span.METER);;
            }
        } catch (Throwable t) {
            Arrays.fill(elevations, Double.NaN);
            t.printStackTrace();
        } finally {
            if (chunk != null)
                chunk.dispose();
        }
    }
}
