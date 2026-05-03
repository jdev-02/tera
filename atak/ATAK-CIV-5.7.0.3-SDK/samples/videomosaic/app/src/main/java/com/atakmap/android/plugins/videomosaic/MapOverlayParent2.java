package com.atakmap.android.plugins.videomosaic;

import com.atakmap.android.maps.DeepMapItemQuery;
import com.atakmap.android.maps.DefaultMapGroup;
import com.atakmap.android.maps.MapGroup;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.overlay.MapOverlay;
import com.atakmap.android.overlay.MapOverlayParent;
import com.atakmap.coremap.maps.coords.GeoBounds;
import com.atakmap.coremap.maps.coords.GeoPoint;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedSet;

/**************************************************************************/

public class MapOverlayParent2 extends MapOverlayParent implements
        DeepMapItemQuery {

    private Set<MapOverlay> overlaysCopy;
    private MapGroup group;

    public MapOverlayParent2(MapView mapView, String id, String name,
                             String iconUri,
                             int order, boolean alwaysVisible) {
        super(mapView, id, name, iconUri, order, alwaysVisible);

        this.overlaysCopy = new LinkedHashSet<MapOverlay>();
        this.group = new DefaultMapGroup("Air Overlays");
        this.group.setMetaBoolean("customRenderer", true);
    }

    @Override
    public SortedSet<MapItem> deepHitTestItems(int xpos, int ypos,
                                               GeoPoint point, MapView view) {
        return null;
    }

    @Override
    public DeepMapItemQuery getQueryFunction() {
        return this;
    }

    @Override
    public MapGroup getRootGroup() {
        return this.group;
    }

    @Override
    public synchronized boolean add(MapOverlay overlay) {
        final boolean retval = super.add(overlay);
        this.overlaysCopy.add(overlay);
        return retval;
    }

    /**********************************************************************/
    // DeepMapItemQuery

    @Override
    public synchronized MapItem deepFindItem(Map<String, String> metadata) {
        DeepMapItemQuery query;
        MapItem result;
        for (MapOverlay overlay : this.overlaysCopy) {
            query = overlay.getQueryFunction();
            if (query != null) {
                result = query.deepFindItem(metadata);
                if (result != null)
                    return result;
            }
        }
        return null;
    }

    @Override
    public synchronized Collection<MapItem> deepFindItems(
            GeoBounds geobounds, Map<String, String> metadata) {
        return deepFindItems(metadata);
    }

    @Override
    public synchronized List<MapItem> deepFindItems(
            Map<String, String> metadata) {
        List<MapItem> retval = new LinkedList<MapItem>();

        DeepMapItemQuery query;
        for (MapOverlay overlay : this.overlaysCopy) {
            query = overlay.getQueryFunction();
            if (query != null)
                retval.addAll(query.deepFindItems(metadata));
        }
        return retval;
    }

    @Override
    public MapItem deepFindClosestItem(GeoPoint location, double threshold,
            Map<String, String> metadata) {

        DeepMapItemQuery query;
        MapItem candidate = null;
        double candidateDistance = Double.NaN;
        MapItem result;
        double resultDistance;
        for (MapOverlay overlay : this.overlaysCopy) {
            query = overlay.getQueryFunction();
            if (query != null) {
                result = query.deepFindClosestItem(location, threshold,
                        metadata);
                if (result != null) {
                    if (candidate != null) {
                        resultDistance = MapItem.computeDistance(result,
                                location);
                        if (resultDistance < candidateDistance)
                            candidate = result;
                    } else {
                        candidate = result;
                    }
                }
            }
        }
        return candidate;
    }

    @Override
    public Collection<MapItem> deepFindItems(GeoPoint location,
            double radius,
            Map<String, String> metadata) {
        List<MapItem> retval = new LinkedList<MapItem>();

        DeepMapItemQuery query;
        for (MapOverlay overlay : this.overlaysCopy) {
            query = overlay.getQueryFunction();
            if (query != null)
                retval.addAll(query.deepFindItems(location, radius,
                        metadata));
        }
        return retval;
    }

    @Override
    public MapItem deepHitTest(int xpos, int ypos, GeoPoint point,
            MapView view) {
        System.out.println("DEEP HIT");
        DeepMapItemQuery query;
        MapItem result;
        for (MapOverlay overlay : this.overlaysCopy) {
            query = overlay.getQueryFunction();
            if (query != null) {
                result = query.deepHitTest(xpos, ypos, point, view);
                System.out.println("result ---> " + result);
                if (result != null)
                    return result;
            }
        }
        return null;
    }
}
