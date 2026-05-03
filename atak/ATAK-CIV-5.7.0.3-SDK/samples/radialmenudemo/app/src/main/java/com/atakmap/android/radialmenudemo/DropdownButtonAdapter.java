package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;

import androidx.annotation.NonNull;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.android.widgets.MapWidget;

import gov.tak.api.widgets.IMapWidget;

public class DropdownButtonAdapter extends ArrayAdapter<IMapWidget> {
    public DropdownButtonAdapter(@NonNull Context context, int resource) {
        super(context, resource);
    }

    @NonNull
    @Override
    public View getView (int position, View convertView, ViewGroup parent) {

        DropdownButtonView buttonView = null == convertView ?
                (DropdownButtonView) PluginLayoutInflater
                        .inflate(super.getContext(), R.layout.dropdown_button, null) :
                (DropdownButtonView) convertView;

        buttonView.populateLayout(getItem(position));

        return buttonView;
    }
}
