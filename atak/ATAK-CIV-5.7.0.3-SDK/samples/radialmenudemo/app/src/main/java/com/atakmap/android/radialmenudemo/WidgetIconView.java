package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.content.res.AssetManager;
import android.graphics.Bitmap;
import android.util.AttributeSet;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.Spinner;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.maps.MapDataRef;
import com.atakmap.android.menu.PluginMenuParser;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.android.util.ATAKUtilities;
import com.atakmap.android.widgets.WidgetIcon;
import com.atakmap.coremap.log.Log;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;

import static com.atakmap.android.maps.MapView.getMapView;

public class WidgetIconView extends LinearLayout implements
        AdapterView.OnItemSelectedListener {

    final static String TAG = "WidgetIconView";

    final static String defaultEntry = "-*- Current -*-";

    final static int iconState = 0;
    final static int iconPixels = 96;

    ArrayList<String> resources;
    ArrayAdapter<String> adapter;
    Spinner spinner;

    String defaultIconUri;
    WidgetIcon widgetIcon;

    public WidgetIconView(Context context, AttributeSet attrs) {
        super(context, attrs);
        PluginLayoutInflater.inflate(getContext(), R.layout.view_widget_icon, this);
    }

    @Override
    protected void onFinishInflate() {
        super.onFinishInflate();

        final Context atakContext = getMapView().getContext();

        final AssetManager assetManager = getContext().getAssets();

        String[] assets = null;
        try {
            assets = assetManager.list("icons");
        } catch (IOException e) {
            e.printStackTrace();
        }

        resources = new ArrayList<String>(Arrays.asList(assets));

        adapter = new ArrayAdapter<>(atakContext,
                android.R.layout.simple_spinner_item, resources);
        adapter.sort(String.CASE_INSENSITIVE_ORDER);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);

        spinner = (Spinner) this.findViewById(R.id.icon_spinner);
        spinner.setAdapter(adapter);
        spinner.setOnItemSelectedListener(this);
    }

    @Override
    public void onItemSelected(AdapterView<?> adapterView, View view, int position, long id) {
        final String selection = (String) spinner.getItemAtPosition(position);

        String iconUri = null;
        MapDataRef mapDataRef = null;
        if (selection.equals(defaultEntry)) {
            iconUri = defaultIconUri;
        } else {
            // plugin scoped assets
            iconUri = PluginMenuParser.getItem(getContext(), "icons/" + selection);

            // application scoped assets, but that should never happen
            // because we never added them to the selectable list!
            if (0 == iconUri.length()) {
                iconUri = "asset:///icons/" + selection;
            }
        }
        mapDataRef = MapDataRef.parseUri(iconUri);

        Bitmap bitmap = ATAKUtilities.getUriBitmap(iconUri);

        if ((null == bitmap) || (null == mapDataRef)) {
            final String message = "cannot resolve assets for: " + selection;
            throw new IllegalStateException(message);
        }

        final int iconWidth = bitmap.getWidth();
        final int iconHeight = bitmap.getHeight();

        if (iconPixels != iconWidth)
            bitmap = Bitmap.createScaledBitmap(bitmap, iconPixels, iconPixels, true);

        final ImageView iconView = (ImageView) findViewById(R.id.icon_image);
        iconView.setImageBitmap(bitmap);

        final WidgetIcon.Builder builder = new WidgetIcon.Builder();
        widgetIcon = builder
                .setAnchor(iconWidth / 2, iconHeight /2)
                .setSize(iconWidth, iconHeight)
                .setImageRef(iconState, mapDataRef)
                .build();
    }

    @Override
    public void onNothingSelected(AdapterView<?> adapterView) {
        widgetIcon = null;
    }

    public WidgetIcon get() {
        return widgetIcon;
    }

    public void set(WidgetIcon widgetIcon) {

        this.widgetIcon = widgetIcon;
        this.defaultIconUri = widgetIcon.getIconRef(0).toUri();

        int position = resources.indexOf(defaultEntry);
        if (0 > position) {
            resources.add(defaultEntry);
            adapter.sort(String.CASE_INSENSITIVE_ORDER);
            position = resources.indexOf(defaultEntry);
        }
        spinner.setSelection(position);
    }
}
