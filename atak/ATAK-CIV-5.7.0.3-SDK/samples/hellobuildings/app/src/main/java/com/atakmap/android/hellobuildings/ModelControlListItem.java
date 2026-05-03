
package com.atakmap.android.hellobuildings;

import com.atakmap.android.hierarchy.action.Visibility2;
import com.atakmap.android.hierarchy.items.AbstractHierarchyListItem2;
import com.atakmap.map.MapRenderer;
import com.atakmap.map.layer.Layer2;
import com.atakmap.map.layer.control.ModelControl;
import com.atakmap.math.MathUtils;
import com.atakmap.util.Visitor;

public class ModelControlListItem extends AbstractHierarchyListItem2
        implements Visibility2 {

    private final Layer2 layer;
    private final MapRenderer renderer;
    private final int mask;

    public ModelControlListItem(Layer2 layer, MapRenderer renderer, int mask) {
        this.layer = layer;
        this.renderer = renderer;
        this.mask = mask;
    }

    @Override
    public int getVisibility() {
        final boolean[] hasMask = new boolean[1];
        final boolean visited = renderer.visitControl(this.layer,
                new Visitor<ModelControl>() {
                    @Override
                    public void visit(ModelControl object) {
                        hasMask[0] = MathUtils.hasBits(object.getVisible(),
                                mask);
                    }
                }, ModelControl.class);
        // if the control was not present, assume everything is visible
        hasMask[0] |= !visited;
        return hasMask[0] ? VISIBLE : INVISIBLE;
    }

    @Override
    public boolean setVisible(final boolean visible) {
        final boolean visited = renderer.visitControl(this.layer,
                new Visitor<ModelControl>() {
                    @Override
                    public void visit(ModelControl object) {
                        if (visible)
                            object.setVisible(object.getVisible() | mask);
                        else
                            object.setVisible(object.getVisible() & ~mask);
                    }
                }, ModelControl.class);
        // if the control was not present, assume everything is visible
        return !visited || visible;
    }

    @Override
    public boolean hideIfEmpty() {
        return false;
    }

    @Override
    public String getTitle() {
        switch (mask) {
            case ModelControl.TEXTURE:
                return "Texture";
            case ModelControl.WIREFRAME:
                return "Wireframe";
            case ModelControl.TEXTURE | ModelControl.WIREFRAME:
                return "Texture & Wireframe";
            default:
                return "Model Mask 0x" + Integer.toString(mask, 16);
        }
    }

    @Override
    public int getDescendantCount() {
        return 0;
    }

    @Override
    public Object getUserObject() {
        return null;
    }

    @Override
    public boolean isChildSupported() {
        return false;
    }

    @Override
    protected void refreshImpl() {
    }

}
