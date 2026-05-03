
package com.atakmap.android.hellobuildings;

import com.atakmap.android.hierarchy.action.Visibility2;
import com.atakmap.android.hierarchy.items.AbstractHierarchyListItem2;
import com.atakmap.android.maps.MapView;
import com.atakmap.map.MapControl;
import com.atakmap.map.layer.Layer;
import com.atakmap.map.layer.Layer2;
import com.atakmap.map.layer.control.ModelControl;
import com.atakmap.util.Visitor;

public class LayerOverlayManagerListItem extends AbstractHierarchyListItem2
        implements Visibility2 {

    private Layer layer;

    public LayerOverlayManagerListItem(Layer layer) {
        this.layer = layer;

        if (hasControl(this.layer, ModelControl.class)) {
            this.children.add(new ModelControlListItem((Layer2) this.layer,
                    MapView.getMapView().getGLSurface().getGLMapView(),
                    ModelControl.TEXTURE));
            this.children.add(new ModelControlListItem((Layer2) this.layer,
                    MapView.getMapView().getGLSurface().getGLMapView(),
                    ModelControl.WIREFRAME));
        }
    }

    @Override
    public int getVisibility() {
        return this.layer.isVisible() ? VISIBLE : INVISIBLE;
    }

    @Override
    public boolean setVisible(boolean visible) {
        this.layer.setVisible(visible);
        return visible;
    }

    @Override
    public boolean hideIfEmpty() {
        return false;
    }

    @Override
    public String getTitle() {
        return this.layer.getName();
    }

    @Override
    public int getDescendantCount() {
        return this.getChildCount();
    }

    @Override
    public Object getUserObject() {
        return null;
    }

    @Override
    public int getChildCount() {
        return getChildren().size();
    }

    @Override
    public boolean isChildSupported() {
        return true;
    }

    @Override
    protected void refreshImpl() {
    }

    private static <T extends MapControl> boolean hasControl(Layer layer,
            Class<T> controlClazz) {
        if (!(layer instanceof Layer2))
            return false;

        return MapView.getMapView().getGLSurface().getGLMapView()
                .visitControl((Layer2) layer, new Visitor<T>() {
                    @Override
                    public void visit(T object) {
                    }
                },
                        controlClazz);
    }
}
