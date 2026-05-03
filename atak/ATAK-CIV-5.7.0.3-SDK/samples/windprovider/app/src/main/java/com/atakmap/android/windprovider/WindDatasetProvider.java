package com.atakmap.android.windprovider;

import android.content.Context;

import com.atakmap.android.databridge.Dataset;
import com.atakmap.android.databridge.DatasetDefinition;
import com.atakmap.android.databridge.DatasetElement;
import com.atakmap.android.databridge.DatasetProvider;
import com.atakmap.android.databridge.DatasetProviderCallback;
import com.atakmap.android.databridge.DatasetQueryParam;
import com.atakmap.android.windprovider.importwind.OnlineWindImport;
import com.atakmap.android.windprovider.importwind.WindInfo;
import com.atakmap.android.windprovider.importwind.parsers.WindParser;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import gov.tak.api.util.Disposable;

public class WindDatasetProvider implements DatasetProvider, Disposable {

    private final String BASEUID = "bf736561-a12e-4091-8d36-5d97cc678de0";

    private final WindParser windParser;
    private final OnlineWindImport onlineWindImport;
    private final Context pContext;
    private final DatasetDefinition definition;
    private final String uid;

    public WindDatasetProvider(OnlineWindImport onlineWindImport, WindParser windParser, Context pContext) {
        this.onlineWindImport = onlineWindImport;
        this.windParser = windParser;
        this.pContext = pContext;
        this.uid = "provider." + BASEUID + "." + windParser.getName();
        definition = new DatasetDefinition(BASEUID, "wind-data-v1");
        definition.addDataElement(new DatasetElement("altitude", "the altitude in meters", DatasetElement.Type.Integer, false));
        definition.addDataElement(new DatasetElement("direction", "the direction in true degrees", DatasetElement.Type.Integer, false));
        definition.addDataElement(new DatasetElement("speed", "the speed in knots", DatasetElement.Type.Integer, false));
        definition.addDataElement(new DatasetElement("requested_location", "the requested location", DatasetElement.Type.GeoPoint, true));
        if (windParser.supportTimeOffset())
            definition.addDataElement(new DatasetElement("time_offset", "the time offset", DatasetElement.Type.Long, true));
        definition.seal();
    }

    @Override
    public String getUID() {
        return uid;
    }

    @Override
    public String getName() {
        return windParser.getName();
    }

    @Override
    public String getDescription() {
        return "Wind data from: " + windParser.getName();
    }

    @Override
    public String getPackageName() {
        return pContext.getPackageName();
    }

    @Override
    public List<DatasetDefinition> getDefinitions() {
        return Collections.singletonList(definition);
    }

    @Override
    public void subscribe(final String tag, final List<DatasetQueryParam> query, final DatasetProviderCallback datasetProviderCallback) {
        GeoPoint gp = null;
        int offset = -1;
        for (DatasetQueryParam queryParam : query) {
            if (queryParam.key.equals("requested_location")) {
                if (queryParam.value instanceof GeoPoint)
                    gp = (GeoPoint) queryParam.value;
            } else if (queryParam.key.equals("time_offset")) {
                if (queryParam.value instanceof Integer)
                    offset = (Integer) queryParam.value;
            }
        }
        final GeoPoint fgp = gp;
        final int foffset = offset;

        onlineWindImport.getWinds(windParser, gp, offset, false, new OnlineWindImport.WindReceiver() {
            final List<Dataset> retval = new ArrayList<>();

            @Override
            public void receivedWindFromServer(List<WindInfo> winds) {
                for (WindInfo info : winds) {
                    Dataset ds = new Dataset(uid);
                    ds.set("speed", info.getSpeed());
                    ds.set("direction", info.getDirection());
                    ds.set("altitude", info.getAltitude());
                    ds.set("requested_location", fgp);
                    ds.set("time_offset", foffset);
                    ds.seal();
                    retval.add(ds);
                }
            }

            @Override
            public void receivedPressureQNH(double qnh) {

            }

            @Override
            public void error(String msg) {
                datasetProviderCallback.onData(tag, WindDatasetProvider.this, query, Collections.emptyList(), DatasetProviderCallback.Status.ERROR, msg );
            }

            @Override
            public void completed() {
                datasetProviderCallback.onData(tag, WindDatasetProvider.this, query, retval, DatasetProviderCallback.Status.COMPLETE, "" );
            }
        });
    }

    @Override
    public void unsubscribe(DatasetProviderCallback datasetProviderCallback) {

    }

    @Override
    public void dispose() {

    }
}
