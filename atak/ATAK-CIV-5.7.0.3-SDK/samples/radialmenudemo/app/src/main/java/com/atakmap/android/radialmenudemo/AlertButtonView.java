package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.util.AttributeSet;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Switch;

import com.atakmap.android.action.MapAction;
import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.menu.MapMenuWidget;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.android.widgets.WidgetIcon;

import gov.tak.api.widgets.IMapMenuButtonWidget;
import gov.tak.api.widgets.IMapMenuWidget;

public class AlertButtonView extends LinearLayout {

    public AlertButtonView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    public void populateLayout(MapMenuButtonWidget buttonWidget) {

        final WidgetIcon icon = buttonWidget.getIcon();
        final WidgetIconView widgetIconView = (WidgetIconView) findViewById(R.id.widget_icon);
        widgetIconView.set(icon);

        Switch disabledToggle = (Switch) findViewById(R.id.disabledValue);
        disabledToggle.setChecked(buttonWidget.isDisabled());

        OnClickView onClickView = (OnClickView) findViewById(R.id.onclick);
        onClickView.set(buttonWidget.getOnButtonClickHandler());

        SubmenuView submenuView = (SubmenuView) findViewById(R.id.submenu);
        submenuView.set(buttonWidget.getSubmenu());

        EditText weightEntry = (EditText) findViewById(R.id.weight);
        weightEntry.setText(String.valueOf(buttonWidget.getLayoutWeight()));

        EditText radiusEntry = (EditText) findViewById(R.id.radius);
        radiusEntry.setText(String.valueOf(buttonWidget.getOrientationRadius()));

        EditText widthEntry = (EditText) findViewById(R.id.width);
        widthEntry.setText(String.valueOf(buttonWidget.getButtonWidth()));
    }

    public WidgetIcon getWidgetIcon() {
        final WidgetIconView widgetIconView = (WidgetIconView) findViewById(R.id.widget_icon);
        return widgetIconView.get();
    }

    public boolean getDisabled() {
        Switch disabledToggle = (Switch) findViewById(R.id.disabledValue);
        return disabledToggle.isChecked();
    }

    public IMapMenuButtonWidget.OnButtonClickHandler getOnClick() {
        OnClickView onClickView = (OnClickView) findViewById(R.id.onclick);
        return onClickView.get();
    }

    public IMapMenuWidget getSubmenu() {
        SubmenuView submenuView = (SubmenuView) findViewById(R.id.submenu);
        return submenuView.get();
    }

    protected float getNumericValue(int viewId) {
        EditText valueText = (EditText) findViewById(viewId);
        return Float.parseFloat(valueText.getText().toString());
    }

    public float getButtonRadius() {
        return getNumericValue(R.id.radius);
    }

    public float getButtonWidth() {
        return getNumericValue(R.id.width);
    }

    public float getButtonWeight() { return getNumericValue(R.id.weight); }

}
