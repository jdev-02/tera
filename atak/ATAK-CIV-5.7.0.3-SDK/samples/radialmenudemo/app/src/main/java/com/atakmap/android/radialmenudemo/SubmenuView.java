package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.util.AttributeSet;

import com.atakmap.android.menu.MapMenuWidget;
import com.atakmap.android.radialmenudemo.plugin.R;

import gov.tak.api.widgets.IMapMenuWidget;

public class SubmenuView extends AssetSpinnerView<IMapMenuWidget> {

    final protected MenuWidgetFactory factory;

    public SubmenuView(Context context, AttributeSet attrs) {
        super(context, attrs);
        setPathAndLabel("menus", R.string.submenuTitle);
        factory = new MenuWidgetFactory();
    }

    @Override
    protected MapMenuWidget resolve(String xmlResource) {
        return factory.resolveMenu(xmlResource);
    }
}
