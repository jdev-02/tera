package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.util.AttributeSet;

import com.atakmap.android.action.MapAction;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.radialmenudemo.plugin.R;

import gov.tak.api.widgets.IMapMenuButtonWidget;

public class OnClickView extends AssetSpinnerView<IMapMenuButtonWidget.OnButtonClickHandler> {

    final protected MenuWidgetFactory factory;

    public OnClickView(Context context, AttributeSet attrs) {
        super(context, attrs);
        setPathAndLabel("actions", R.string.onclickTitle);
        factory = new MenuWidgetFactory();
    }

    @Override
    protected IMapMenuButtonWidget.OnButtonClickHandler resolve(String xmlResource) {
        final MapAction action = factory.resolveAction(xmlResource);

        if (action == null)
            return null;

        return new IMapMenuButtonWidget.OnButtonClickHandler() {
            @Override
            public boolean isSupported(Object o) {
                return o instanceof MapItem || o == null;
            }
            @Override
            public void performAction(Object o) {
                if (isSupported(o)) {
                    action.performAction(MapView.getMapView(), (MapItem)o);
                }
            }
        };
    }
}
