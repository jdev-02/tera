package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.text.Editable;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.LinearLayout;

import androidx.annotation.NonNull;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.radialmenudemo.plugin.R;

public class AlertPrefsAdapter extends ArrayAdapter<String> {

    interface ButtonHandler {
        void onButtonDelete(int position);
    }

    private  ButtonHandler handler;

    public AlertPrefsAdapter(@NonNull Context context, int resource) {
        super(context, resource);
    }

    void setHandler(ButtonHandler handler) {
        this.handler = handler;
    }

    @NonNull
    @Override
    public View getView (final int position, View convertView, ViewGroup parent) {

        LinearLayout layout = null == convertView ?
                (LinearLayout) PluginLayoutInflater
                        .inflate(super.getContext(), R.layout.alert_prefs_entry, null) :
                (LinearLayout) convertView;

        final EditText editText = (EditText) layout.findViewById(R.id.prefs_entry);
        editText.setText(getItem(position));
        // FIXME - this focus change approach has scary characteristics
        // not sure what the right process to trap edits *when done*
        editText.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override
            public void onFocusChange(View view, boolean hasFocus) {
                if (!hasFocus) {
                    final String original = getItem(position);
                    final Editable editable = editText.getText();
                    if (null == editable) {
                        if (null != handler)
                            handler.onButtonDelete(position);
                    } else if (!editable.toString().equals(original)) {
                        remove(original);
                        add(editable.toString());
                        sort(String.CASE_INSENSITIVE_ORDER);
                        notifyDataSetChanged();
                    }
                }
            }
        });

        ImageButton button = (ImageButton) layout.findViewById(R.id.prefs_del);
        button.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                if (null != handler)
                    handler.onButtonDelete(position);
            }
        });

        return layout;
    }
}
