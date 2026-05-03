package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.content.res.AssetManager;
import android.util.AttributeSet;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.radialmenudemo.plugin.R;

import java.io.IOException;
import java.util.ArrayList;

import static com.atakmap.android.maps.MapView.getMapView;

public abstract class AssetSpinnerView<T> extends LinearLayout implements
        AdapterView.OnItemSelectedListener {

    final static String nullEntry = "-*- Empty -*-";
    final static String defaultEntry = "-*- Current -*-";

    private ArrayList<String> resources;
    private ArrayAdapter<String> adapter;
    private Spinner spinner;

    T defaultType;
    T activeType;

    private String path;
    private int labelString;

    public AssetSpinnerView(Context context, AttributeSet attrs) {
        super(context, attrs);
        PluginLayoutInflater.inflate(getContext(), R.layout.view_spinner, this);
        defaultType = null;
        activeType = null;
    }

    protected void setPathAndLabel(String path,  int labelString) {
        this.path = path;
        this.labelString = labelString;
    }

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();

        TextView textView = (TextView) findViewById(R.id.spinner_label);
        textView.setText(labelString);

        final Context atakContext = getMapView().getContext();

        AssetManager assetManager = atakContext.getAssets();
        String[] assets = new String[]{}; // well formed in case of exception
        try {
            assets = assetManager.list(path);
        } catch (IOException e) {
            e.printStackTrace();
        }

        resources = new ArrayList<String>();
        resources.add(nullEntry); // always be able to "clear" selection
        for (String asset : assets) {
            resources.add(path + "/" + asset);
        }

        adapter = new ArrayAdapter<>(atakContext,
                android.R.layout.simple_spinner_item, resources);
        adapter.sort(String.CASE_INSENSITIVE_ORDER);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);

        spinner = (Spinner) this.findViewById(R.id.spinner);
        spinner.setAdapter(adapter);
        spinner.setOnItemSelectedListener(this);
    }

    protected abstract T resolve(String xmlResource);

    @Override
    public void onItemSelected(AdapterView<?> adapterView, View view, int position, long id) {
        final String selection = (String) spinner.getItemAtPosition(position);
        switch(selection) {
            case nullEntry:
                activeType = null;
                break;
            case defaultEntry:
                activeType = defaultType;
                break;
            default:
                activeType = resolve(selection);
                break;
        }
    }

    @Override
    public void onNothingSelected(AdapterView<?> adapterView) {
        activeType = null;
    }

    public void set(T activeType) {

        // Currently, there's no way to associate a fully created
        // types with the xml description that created it.
        // So, when setting this view, assume inbound widget
        // will be the default, and add it to the resource list.

        defaultType = activeType;

        final String selection = null == defaultType ?
                nullEntry : defaultEntry;

        // not the greatest, but all we have right now ...
        int position = resources.indexOf(selection);
        if (0 > position) {
            resources.add(selection);
            adapter.sort(String.CASE_INSENSITIVE_ORDER);
            position = resources.indexOf(selection);
        }
        spinner.setSelection(position);
    }

    public T get() {
        return activeType;
    }
}
