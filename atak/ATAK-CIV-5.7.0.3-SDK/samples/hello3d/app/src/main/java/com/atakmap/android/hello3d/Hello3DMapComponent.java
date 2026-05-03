
package com.atakmap.android.hello3d;

import com.atakmap.android.features.FeatureDataStoreDeepMapItemQuery;
import com.atakmap.android.features.FeatureDataStoreMapOverlay;
import com.atakmap.android.hierarchy.HierarchyListFilter;
import com.atakmap.android.hierarchy.HierarchyListItem;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.menu.PluginMenuParser;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;
import com.atakmap.map.layer.feature.AttributeSet;
import com.atakmap.map.layer.feature.DataStoreException;
import com.atakmap.map.layer.feature.Feature;
import com.atakmap.map.layer.feature.FeatureDataStore2;
import com.atakmap.map.layer.feature.FeatureDataStore3;
import com.atakmap.map.layer.feature.FeatureLayer3;
import com.atakmap.map.layer.feature.FeatureSet;
import com.atakmap.map.layer.feature.Utils;
import com.atakmap.map.layer.feature.datastore.FeatureSetDatabase2;
import com.atakmap.map.layer.feature.style.Style;
import com.atakmap.map.layer.feature.geometry.Point;
import com.atakmap.map.layer.feature.geometry.Geometry;
import com.atakmap.map.layer.feature.geometry.GeometryCollection;
import com.atakmap.map.layer.feature.geometry.LineString;
import com.atakmap.map.layer.feature.geometry.Polygon;
import com.atakmap.map.layer.feature.style.BasicFillStyle;
import com.atakmap.map.layer.feature.style.BasicStrokeStyle;
import com.atakmap.map.layer.feature.style.CompositeStyle;
import com.atakmap.map.layer.feature.style.LabelPointStyle;
import com.atakmap.map.layer.feature.style.IconPointStyle;
import com.atakmap.map.layer.opengl.GLLayerFactory;
import com.atakmap.android.hello3d.plugin.R;


import com.atakmap.android.dropdown.DropDownMapComponent;
import com.atakmap.android.ipc.AtakBroadcast.DocumentedIntentFilter;

import android.content.Context;
import android.content.Intent;
import android.widget.BaseAdapter;


public class Hello3DMapComponent extends DropDownMapComponent {
    public Context pluginContext;
    public static final String TAG = "Hello3DMapComponent";
    private FeatureDataStore2 buildingsDataStore;
    private ExtrudedPolygonsExample epe;
    private ExtrudedPolygonsBatchExample epbe;
    private static long fsid = -1;

    private FeatureDataStoreMapOverlay overlay;

    private static final double MIN_RESOLUTION = 25d;

    // demonstrates the movement of objects in the scene
    private static Thread movementThread;
    private static boolean cancelled = false;
    //private static final double MIN_RESOLUTION = Double.MAX_VALUE;
    

    private FeatureDropDownReceiver fddr;


    public void onCreate(Context context, Intent intent, MapView view) {
        context.setTheme(R.style.ATAKPluginTheme);
        pluginContext = context;


        // register the layer renderers for the various example layers
        GLLayerFactory.register(GLExtrudedPolygonsExample.SPI);
        GLLayerFactory.register(GLExtrudedPolygonsBatchExample.SPI);
        GLLayerFactory.register(GLHelloBuildings.SPI);

        // create a FeatureDataStore
        try {

            buildingsDataStore = createExampleFeatureDataStore();
        } catch (DataStoreException dse) {
            Log.d(TAG, "data store creation error", dse);
        }

        // add in the ability to provide a hit test for these features.
        FeatureLayer3 layer = new FeatureLayer3( "Building Footprints", buildingsDataStore);
        FeatureDataStoreDeepMapItemQuery query = new FeatureDataStoreDeepMapItemQuery(
                layer) {
            protected MapItem featureToMapItem(Feature feature) {
                MapItem retval = super.featureToMapItem(feature);
                retval.setMetaString("menu",  PluginMenuParser.getMenu(pluginContext, "menu/feature.xml"));
                retval.setMetaLong("featureid", feature.getId());
                return retval;
            }
        };


        // construct the new drop down for the features
        fddr = new FeatureDropDownReceiver(view, pluginContext, buildingsDataStore);
        DocumentedIntentFilter filter = new DocumentedIntentFilter();
        filter.addAction("com.atakmap.android.hello3d.FeatureDetails",
                         "customized view for the features in this example");
        this.registerDropDownReceiver(fddr, filter);



        overlay = new FeatureDataStoreMapOverlay(
                view.getContext(), layer.getDataStore(), null, layer.getName(),
                "file://asset/nothing", query,null,null) {
           @Override
            public HierarchyListItem getListModel(BaseAdapter adapter, long capabilities, HierarchyListFilter filter) {
                return super.getListModel(adapter, capabilities, filter);

                //return null if you don't want this FeatureDataStore showing up in the list.
                //return null;
            }

        };

        view.getMapOverlayManager().addFilesOverlay(overlay);

        // add the two simple example layers
        view.addLayer(MapView.RenderStack.VECTOR_OVERLAYS,
                epe = new ExtrudedPolygonsExample());
        view.addLayer(MapView.RenderStack.VECTOR_OVERLAYS,
                epbe = new ExtrudedPolygonsBatchExample());

        // create a new FeatureLayer and add it to the map. The library provided
        // renderer will automatically create footprints from the content
        view.addLayer(MapView.RenderStack.VECTOR_OVERLAYS,
                layer);

        // create a new HelloBuildings layer and add it to the map. The custom
        // renderer will show 3D representations of the geometries
        view.addLayer(MapView.RenderStack.VECTOR_OVERLAYS,
                new HelloBuildings(buildingsDataStore));

    }

    private static FeatureDataStore2 createExampleFeatureDataStore()  throws DataStoreException {
        // define the footprints of some buildings
        GeoPoint[] bld1 = new GeoPoint[] {
                new GeoPoint(35.76847, -78.78419),
                new GeoPoint(35.76836, -78.78420),
                new GeoPoint(35.76836, -78.78446),
                new GeoPoint(35.76847, -78.78445),
                new GeoPoint(35.76847, -78.78419),
        };
        GeoPoint[] bld2 = new GeoPoint[] {
                new GeoPoint(35.76840, -78.78446),
                new GeoPoint(35.76851, -78.78446),
                new GeoPoint(35.76851, -78.78455),
                new GeoPoint(35.76839, -78.78455),
                new GeoPoint(35.76840, -78.78446),
        };
        GeoPoint[] bld3 = new GeoPoint[] {
                new GeoPoint(35.76859, -78.78456),
                new GeoPoint(35.76848, -78.78456),
                new GeoPoint(35.76847, -78.78479),
                new GeoPoint(35.76858, -78.78478),
                new GeoPoint(35.76859, -78.78456),
        };
        GeoPoint[] bld4 = new GeoPoint[] {
                new GeoPoint(35.76861, -78.78511),
                new GeoPoint(35.76850, -78.78511),
                new GeoPoint(35.76851, -78.78558),
                new GeoPoint(35.76862, -78.78557),
                new GeoPoint(35.76861, -78.78511),
        };
        GeoPoint[] bld5 = new GeoPoint[] {
                new GeoPoint(35.76825, -78.78544),
                new GeoPoint(35.76825, -78.78484),
                new GeoPoint(35.76814, -78.78485),
                new GeoPoint(35.76816, -78.78543),
                new GeoPoint(35.76825, -78.78544),
        };
        GeoPoint[] bld6 = new GeoPoint[] {
                new GeoPoint(35.76806, -78.78544),
                new GeoPoint(35.76805, -78.78486),
                new GeoPoint(35.76795, -78.78486),
                new GeoPoint(35.76794, -78.78545),
                new GeoPoint(35.76806, -78.78544),
        };

        // the feature data store is a container for Feature objects. It
        // provides database type semantics for managing membership, iteration
        // and searching.
        final FeatureDataStore3 retval;

        // the library provides several implementations of the FeatureDataStore
        // interface.  The implementation is an
        // in-memory implementation
        retval = new FeatureSetDatabase2(null);

                  

        // all features must be members of a Feature Set. The Feature Set is
        // some logical grouping of features. Hierarchical representations may
        // be emulated by specifying Feature Sets as paths
        fsid = retval.insertFeatureSet(new FeatureSet(
                "Hello3D", // what generated the features
                "Buildings", // the type of the featuers
                "Buildings", // the feature set name
                MIN_RESOLUTION, // min resolution threshold 
                0d)); // max resolution threshold


        retval.setFeatureSetVisible(fsid, true);

        // for each of the footprints defined, we will create a Feature. A
        // Feature is the composition of: geometry, style and attribtues
        // (metadata).

        retval.insertFeature( new Feature(fsid,
                "Building 1",
                create3DGeometry(bld1, 3),
                new CompositeStyle(new Style[] {
                        new BasicStrokeStyle(0xFF7F3F3F, 3f),
                        new BasicFillStyle(0xC07F3F3F),
                }),
                new AttributeSet()));

        retval.insertFeature(new Feature(fsid,
                "Building 2",
                create3DGeometry(bld2, 3),
                new CompositeStyle(new Style[] {
                        new BasicStrokeStyle(0xFF7F3F3F, 3f),
                        new BasicFillStyle(0xC07F3F3F),
                }),
                new AttributeSet()));


        retval.insertFeature(new Feature(fsid,
                "Building 3",
                create3DGeometry(bld3, 3),
                new CompositeStyle(new Style[] {
                        new BasicStrokeStyle(0xFF7F3F3F, 3f),
                        new BasicFillStyle(0xC07F3F3F),
                }),
                new AttributeSet()));

        retval.insertFeature(new Feature(fsid,
                "Building 4",
                create3DGeometry(bld4, 9),
                new CompositeStyle(new Style[] {
                        new BasicStrokeStyle(0xFF7F3F3F, 3f),
                        new BasicFillStyle(0xC07F3F3F),
                }),
                new AttributeSet()));


        retval.insertFeature(new Feature(fsid,
                "Building 5",
                create3DGeometry(bld5, 6),
                new CompositeStyle(new Style[] {
                        new BasicStrokeStyle(0xFF7F3F3F, 3f),
                        new BasicFillStyle(0xC07F3F3F),
                }),
                new AttributeSet()));

        retval.insertFeature(new Feature(fsid,
                "Building 6",
                create3DGeometry(bld6, 12),
                new CompositeStyle(new Style[] {
                        new BasicStrokeStyle(0xFF7F3F3F, 3f),
                        new BasicFillStyle(0xC07F3F3F),
                }),
                new AttributeSet()));

         Style style;

         // Example on how to draw an icon with text to the screen.
         style = new IconPointStyle(0xFF0000FF,
              "https://maps.google.com/mapfiles/kml/paddle/wht-blank.png",
              0, 0, 0, 0, 0, true);

        long id = retval.insertFeature(new Feature(fsid,
                "Landmark with Icon",
                new Point(-78.78546, 35.76802),
                style,
                new AttributeSet()));


        Feature ee = Utils.getFeature(retval, id);
        ee.getAttributes().setAttribute("addToObjList", 0);
        


        long moving_feature_id =
                retval.insertFeature(new Feature(fsid,
                        "Moving Icon",
                        new Point(-78.78596, 35.76602, 100),
                        style,
                        null));


        //simulateMovingFeature(retval, moving_feature_id);

        // Example on how to draw just text to the screen.
        style = new LabelPointStyle( "Landmark Building", 0xFFFFFFFF, 0xFF000000,
                            LabelPointStyle.ScrollMode.OFF, 0f, 0, 0, 45, false, 14d, 4.0f);

        retval.insertFeature(new Feature(fsid,
                    "Landmark Label",
                    new Point(-78.78746, 35.77002),
                    style,
                    null));


        // Example on how to draw a style composed of an icon point style and a label point style
        // to the screen.
        IconPointStyle style_icon = new IconPointStyle(0xFF00FFFF,
                "https://maps.google.com/mapfiles/kml/paddle/wht-blank.png",
                0, 0, 0, 0, 0, true);

        LabelPointStyle style_label = new LabelPointStyle(
                "Stylized Text", 0xFFFFFF00, 0xFF000000,
                LabelPointStyle.ScrollMode.OFF, 0f, 0, 100,
                0, false);

        CompositeStyle style_composite = new CompositeStyle(new Style[] {style_icon, style_label});


        BasicStrokeStyle bs = new BasicStrokeStyle(0xFFFFFF00, 3);
        LineString ls = new LineString(3);
        ls.addPoint(-78.78944, 35.77100, 201);
        ls.addPoint(-78.78900, 35.77120, 260);
        ls.addPoint(-78.78877, 35.77000, 101);

        retval.insertFeature(new Feature(fsid,
                "linestring relative", ls, bs, null, Feature.AltitudeMode.Relative, 0.0));



        Polygon polygon = new Polygon(3);


        LineString interior = new LineString(3);
        interior.addPoint(-2.509058374039033,52.80297390793135,2000);
        interior.addPoint(-2.497919003821374,52.80297390793135,2000);
        interior.addPoint(-2.497919003821374,52.80297390793135,1500);
        interior.addPoint(-2.509058374039033,52.80297390793135,1500);
        interior.addPoint(-2.509058374039033,52.80297390793135,2000);

        polygon.addRing(interior);

        retval.insertFeature(new Feature(fsid,
                "polygon_box", polygon, bs, null, Feature.AltitudeMode.Relative, 0.0));


        ls = new LineString(3);
        ls.addPoint(-78.78944, 35.77000, 201);
        ls.addPoint(-78.78900, 35.77020, 260);
        ls.addPoint(-78.78877, 35.76900, 101);

        retval.insertFeature(new Feature(fsid,
                "linestring clamp", ls, null, null, Feature.AltitudeMode.ClampToGround, 0.0));

        ls = new LineString(3);
        ls.addPoint(-78.78944, 35.76900, 201);
        ls.addPoint(-78.78900, 35.76920, 260);
        ls.addPoint(-78.78877, 35.76800, 101);

        retval.insertFeature(new Feature(fsid,
                "linestring absolute", ls, null, null, Feature.AltitudeMode.Absolute, 0.0));

        // Example on how to get a feature from a Feature ID.
        //Utils.getFeature(retval, testId);

        
        retval.insertFeature(new Feature(fsid,
                "RelativeTest",
                new Point(-78.78946, 35.77202,  250),
                style_composite,
                null, Feature.AltitudeMode.Relative, -1.0));

        retval.insertFeature(new Feature(fsid,
                "AbsoluteTest",
                new Point(-78.78940, 35.77202,  250),
                style_composite,
                null, Feature.AltitudeMode.Absolute, -1.0));

        retval.insertFeature(new Feature(fsid,
                "ClampToGroundTest",
                new Point(-78.78934, 35.77202,  250),
                style_composite,
                null, Feature.AltitudeMode.ClampToGround, -1.0));



        return retval;
    }

    /**
     * Creates a 3D geometry given the footprint of a building and its height,
     * in meters. The x,y coordinates will correspond to longitude and latitude,
     * respectively, and the z coordinate will refer to relative height in
     * meters.
     * 
     * @param buildingFootprint The building footprint
     * @param height            The height of the building, in meters
     * 
     * @return A 3D geometry that represents the building, describing the roof
     *         and sides.
     */
    private static Geometry create3DGeometry(GeoPoint[] buildingFootprint,
            double height) {
        // the returned geometry will be a GeometryCollection instance, with a
        // dimension of 3 indicating that it stores coordinates as x,y,z
        GeometryCollection retval = new GeometryCollection(3);

        // note that the below loops could be collapsed into a single iteration
        // over the building footprint. separate loops are used here for the
        // sake of clarity.
        LineString ring;

        // create the "top" of the building
        ring = new LineString(3);
        for (int i = 0; i < buildingFootprint.length; i++) {
            //for(int i = buildingFootprint.length-1; i >= 0; i++) {
            ring.addPoint(buildingFootprint[i].getLongitude(),
                    buildingFootprint[i].getLatitude(),
                    height);
        }

        // add the top to the collection
        retval.addGeometry(createSimplePolygon(ring));

        for (int i = 0; i < buildingFootprint.length - 1; i++) {
            // generate a polygon for each side
            ring = new LineString(3);
            ring.addPoint(buildingFootprint[i].getLongitude(),
                    buildingFootprint[i].getLatitude(),
                    height);
            ring.addPoint(buildingFootprint[i + 1].getLongitude(),
                    buildingFootprint[i + 1].getLatitude(),
                    height);
            ring.addPoint(buildingFootprint[i + 1].getLongitude(),
                    buildingFootprint[i + 1].getLatitude(),
                    0);
            ring.addPoint(buildingFootprint[i].getLongitude(),
                    buildingFootprint[i].getLatitude(),
                    0);
            ring.addPoint(buildingFootprint[i].getLongitude(),
                    buildingFootprint[i].getLatitude(),
                    height);

            // add the side to the collection
            retval.addGeometry(createSimplePolygon(ring));
        }

        return retval;
    }


    /**
     * Added solely to demonstrate the current issue with changing the name or geometry of a feature
     * @param fds the FeatureDataStore that contains the feature
     * @param fid the feature
     */
    private static void simulateMovingFeature(final FeatureDataStore3 fds, final long fid) {

        movementThread = new Thread() {
            public void run() {
                int i = 0;
                try {
                    while (!cancelled) {
                        try {
                            Thread.sleep(5000);
                        } catch (Exception e) {
                        }
                        final GeoPoint gp = new GeoPoint(35.77202, -78.78946 + (i * .00001));
                        final String name = "test change - " + (i++);
                        Log.d(TAG, "move the feature: " + fid + " with new name: " + name + " to: " + gp);

                        fds.acquireModifyLock(true);
                        fds.updateFeature(fid, FeatureDataStore3.PROPERTY_FEATURE_NAME, name, null, null,null, 0);
                        fds.updateFeature(fid, FeatureDataStore3.PROPERTY_FEATURE_GEOMETRY, null,
                                new Point(gp.getLongitude(), gp.getLatitude()), null, null, 0);
                        Log.d(TAG, "moved the feature: " + fid + " with new name: " + name + " to: " + gp);

                        IconPointStyle style = new IconPointStyle(0xFF0000FF + (i * 100),
                                "https://maps.google.com/mapfiles/kml/paddle/wht-blank.png",
                                0, 0, 0, 0, 0, true);

                        fds.updateFeature(fid, FeatureDataStore3.PROPERTY_FEATURE_STYLE, null, null, style, null, 0);

                        fds.releaseModifyLock();
                    }
                } catch (Exception e) {
                    Log.d(TAG, "exception occured", e);
                }
            }
        };
        movementThread.start();

    }

    private static Polygon createSimplePolygon(LineString exterior) {
        Polygon retval = new Polygon(exterior.getDimension());
        retval.addRing(exterior);
        return retval;
    }

    @Override
    protected void onDestroyImpl(Context context, MapView view) {
        cancelled = true;
        if (movementThread != null)
            movementThread.interrupt();
        try {
            if (buildingsDataStore != null)
                buildingsDataStore.deleteFeatureSet(fsid);
        } catch (DataStoreException dse) {
            Log.d(TAG, "datastoreexception", dse);
        }
        view.removeLayer(MapView.RenderStack.VECTOR_OVERLAYS,
                epe);
        view.removeLayer(MapView.RenderStack.VECTOR_OVERLAYS,
                epbe);
        view.getMapOverlayManager().removeOverlay(overlay);

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
