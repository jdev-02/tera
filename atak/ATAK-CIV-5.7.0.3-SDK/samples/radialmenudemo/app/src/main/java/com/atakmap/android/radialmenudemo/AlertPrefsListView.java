package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.util.AttributeSet;
import android.view.View;
import android.widget.ImageButton;
import android.widget.ListView;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.radialmenudemo.plugin.R;

import java.util.ArrayList;
import java.util.List;

public class AlertPrefsListView extends ListView implements
        AlertPrefsAdapter.ButtonHandler {

    final static String UNSPECIFIED = "-*- UNSPECIFIED -*-";

    private AlertPrefsAdapter adapter;
    private View headerView;

    public AlertPrefsListView(Context context, AttributeSet attrs) {
        super(context, attrs);

        adapter = new AlertPrefsAdapter(getContext(),
                R.layout.alert_prefs_entry);
        adapter.setHandler(this);
        setAdapter(adapter);

        headerView = PluginLayoutInflater.inflate(getContext(), R.layout.alert_prefs_header, null);
        addHeaderView(headerView);

        ImageButton addButton = (ImageButton) headerView.findViewById(R.id.prefs_add);
        addButton.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View view) {
                adapter.add(UNSPECIFIED);
                adapter.sort(String.CASE_INSENSITIVE_ORDER);
                adapter.notifyDataSetChanged();
            }
        });
    }

    @Override
    public void onButtonDelete(int position) {
        final String item = adapter.getItem(position);
        if (null != item) {
            adapter.remove(item);
            adapter.sort(String.CASE_INSENSITIVE_ORDER);
            adapter.notifyDataSetChanged();
        }
    }

    void populateLayout(int titleId, List<String> prefList) {
        TextView titleView = (TextView) headerView.findViewById(R.id.prefs_title);
        titleView.setText(titleId);

        adapter.clear();
        adapter.addAll(prefList);
    }

    List<String> get() {
        List<String> arrayList = new ArrayList<>();
        for (int index = 0, max = adapter.getCount();
             max > index; ++index) {
            arrayList.add(adapter.getItem(index));
        }
        return arrayList;
    }
}
