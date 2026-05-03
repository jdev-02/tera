
package com.atakmap.android.hellobuildings;

import com.atakmap.android.hellobuildings.plugin.R;
//import com.atakmap.android.hellobuildings.elevation.OSMElevationMosaicDB;
import com.atakmap.android.hellobuildings.opengl.GLBuildingsExample;
import com.atakmap.android.hierarchy.HierarchyListFilter;
import com.atakmap.android.hierarchy.HierarchyListItem;
import com.atakmap.android.maps.AbstractMapComponent;
import com.atakmap.android.maps.DeepMapItemQuery;
import com.atakmap.android.maps.MapGroup;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.overlay.AbstractMapOverlay2;
import com.atakmap.android.overlay.MapOverlay2;
import com.atakmap.map.elevation.ElevationManager;
import com.atakmap.map.layer.AbstractLayer;
import com.atakmap.map.layer.opengl.GLLayerFactory;

import android.content.Context;
import android.content.Intent;
import android.widget.BaseAdapter;

public class HelloBuildingsMapComponent extends AbstractMapComponent {
    public Context pluginContext;
    public static final String TAG = "HelloBuildingsMapComponent";
    AbstractLayer mMapLayer;
    private MapOverlay2 overlayIntegration;

    public void onCreate(Context context, Intent intent, MapView view) {
        context.setTheme(R.style.ATAKPluginTheme);
        GLLayerFactory.register(GLBuildingsExample.SPI);

        pluginContext = context;

        mMapLayer = new BuildingsExample();
        view.addLayer(MapView.RenderStack.VECTOR_OVERLAYS, mMapLayer);

        //OSMElevationMosaicDB eldb = new OSMElevationMosaicDB(((BuildingsExample)mMapLayer).getDataStore());
        //ElevationManager.registerDataSpi(eldb);
        //ElevationManager.registerElevationSource(eldb);

        this.overlayIntegration = new AbstractMapOverlay2() {
            @Override
            public HierarchyListItem getListModel(BaseAdapter adapter,
                    long capabilities,
                    HierarchyListFilter preferredFilter) {
                return new LayerOverlayManagerListItem(mMapLayer);
            }

            @Override
            public String getIdentifier() {
                return this.getName();
            }

            @Override
            public String getName() {
                return "OSM Buildings Demo";
            }

            @Override
            public MapGroup getRootGroup() {
                return null;
            }

            @Override
            public DeepMapItemQuery getQueryFunction() {
                return null;
            }
        };

        view.getMapOverlayManager().addOverlay(this.overlayIntegration);
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        view.removeLayer(MapView.RenderStack.VECTOR_OVERLAYS, mMapLayer);
        view.getMapOverlayManager().removeOverlay(this.overlayIntegration);
        mMapLayer = null;
    }

    @Override
    public void onStart(Context context, MapView view) {
    }

    @Override
    public void onStop(Context context, MapView view) {
    }

    @Override
    public void onPause(Context context, MapView view) {
    }

    @Override
    public void onResume(Context context, MapView view) {
    }
}
