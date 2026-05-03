
package com.atakmap.android.cotinjector.plugin;

import android.content.Context;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.Toast;

import com.atak.plugins.impl.PluginContextProvider;
import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.cotinjector.CotInjector;

import gov.tak.api.plugin.IPlugin;
import gov.tak.api.plugin.IServiceController;
import gov.tak.api.ui.IHostUIService;
import gov.tak.api.ui.Pane;
import gov.tak.api.ui.PaneBuilder;
import gov.tak.api.ui.ToolbarItem;
import gov.tak.api.ui.ToolbarItemAdapter;
import gov.tak.platform.marshal.MarshalManager;

/**
 * This plugin can be used to generate random CoT tracks in a region of interest for performance testing
 */
public class CotInjectorPlugin implements IPlugin {

    private final double LAT1 = 30;
    private final double LON1 = 50;
    private final double LAT2 = 40;
    private final double LON2 = 60;
    private final int COUNT = 1500;
    private final int INTERVAL = 0;
    private final int THREADS = 1;
    private final boolean UPDATES = false;

    IServiceController serviceController;
    Context pluginContext;
    IHostUIService uiService;
    ToolbarItem toolbarItem;
    Pane templatePane;
    CotInjector cotInjector = new CotInjector(LAT1, LON1, LAT2, LON2, COUNT, INTERVAL, THREADS, UPDATES);

    public CotInjectorPlugin(IServiceController serviceController) {
        this.serviceController = serviceController;
        final PluginContextProvider ctxProvider = serviceController
                .getService(PluginContextProvider.class);
        if (ctxProvider != null) {
            pluginContext = ctxProvider.getPluginContext();
            pluginContext.setTheme(R.style.ATAKPluginTheme);
        }

        // obtain the UI service
        uiService = serviceController.getService(IHostUIService.class);

        // initialize the toolbar button for the plugin

        // create the button
        toolbarItem = new ToolbarItem.Builder(
                pluginContext.getString(R.string.app_name),
                MarshalManager.marshal(
                        pluginContext.getResources().getDrawable(R.drawable.ic_launcher),
                        android.graphics.drawable.Drawable.class,
                        gov.tak.api.commons.graphics.Bitmap.class))
                .setListener(new ToolbarItemAdapter() {
                    @Override
                    public void onClick(ToolbarItem item) {
                        showPane();
                    }
                })
                .build();
    }

    @Override
    public void onStart() {
        // the plugin is starting, add the button to the toolbar
        if (uiService == null)
            return;

        uiService.addToolbarItem(toolbarItem);
    }

    @Override
    public void onStop() {
        // the plugin is stopping, remove the button from the toolbar
        if (uiService == null)
            return;

        uiService.removeToolbarItem(toolbarItem);
    }

    private void showPane() {
        // instantiate the plugin view if necessary
        if(templatePane == null) {
            // Remember to use the PluginLayoutInflator if you are actually inflating a custom view
            // In this case, using it is not necessary - but I am putting it here to remind
            // developers to look at this Inflator

            templatePane = new PaneBuilder(PluginLayoutInflater.inflate(pluginContext,
                    R.layout.main_layout, null))
                    // relative location is set to default; pane will switch location dependent on
                    // current orientation of device screen
                    .setMetaValue(Pane.RELATIVE_LOCATION, Pane.Location.Default)
                    // pane will take up 50% of screen width in landscape mode
                    .setMetaValue(Pane.PREFERRED_WIDTH_RATIO, 0.5D)
                    // pane will take up 50% of screen height in portrait mode
                    .setMetaValue(Pane.PREFERRED_HEIGHT_RATIO, 0.5D)
                    .build();
        }

        // if the plugin pane is not visible, show it!
        if(!uiService.isPaneVisible(templatePane)) {
            uiService.showPane(templatePane, null);
        }

        View mainView = MarshalManager.marshal(templatePane, Pane.class, View.class);
        final EditText lat1Entry = mainView.findViewById(R.id.lat1Entry);
        final EditText lon1Entry = mainView.findViewById(R.id.lon1Entry);
        final EditText lat2Entry = mainView.findViewById(R.id.lat2Entry);
        final EditText lon2Entry = mainView.findViewById(R.id.lon2Entry);
        final EditText countEntry = mainView.findViewById(R.id.countEntry);
        final EditText intervalEntry = mainView.findViewById(R.id.intervalEntry);
        final EditText threadsEntry = mainView.findViewById(R.id.threadsEntry);
        final Button controlButton = mainView.findViewById(R.id.controlButton);
        final Button resetButton = mainView.findViewById(R.id.resetButton);
        final CheckBox updatesCheck = mainView.findViewById(R.id.updateCheck);

        Runnable resetAction = new Runnable() {
            @Override
            public void run() {
                lat1Entry.setText(Double.toString(LAT1));
                lat2Entry.setText(Double.toString(LAT2));
                lon1Entry.setText(Double.toString(LON1));
                lon2Entry.setText(Double.toString(LON2));
                countEntry.setText(Integer.toString(COUNT));
                intervalEntry.setText(Integer.toString(INTERVAL));
                threadsEntry.setText(Integer.toString(THREADS));
                updatesCheck.setChecked(UPDATES);
            }
        };

        resetAction.run();

        controlButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                Button button = (Button) view;
                if (button.getText().equals(pluginContext.getString(R.string.start))) {
                    try {
                        final int count = Integer.parseInt(String.valueOf(countEntry.getEditableText()));
                        final int interval = Integer.parseInt(String.valueOf(intervalEntry.getEditableText()));
                        final double lat1 = Double.parseDouble(String.valueOf(lat1Entry.getEditableText()));
                        final double lon1 = Double.parseDouble(String.valueOf(lon1Entry.getEditableText()));
                        final double lat2 = Double.parseDouble(String.valueOf(lat2Entry.getEditableText()));
                        final double lon2 = Double.parseDouble(String.valueOf(lon2Entry.getEditableText()));
                        final int threads = Integer.parseInt(String.valueOf(threadsEntry.getEditableText()));
                        final boolean updates = updatesCheck.isChecked();
                        if (threads < 1)
                            throw new IllegalStateException("threads must be >= 1");
                        lat1Entry.setEnabled(false);
                        lon1Entry.setEnabled(false);
                        lat2Entry.setEnabled(false);
                        lon2Entry.setEnabled(false);
                        countEntry.setEnabled(false);
                        intervalEntry.setEnabled(false);
                        threadsEntry.setEnabled(false);
                        resetButton.setEnabled(false);
                        updatesCheck.setEnabled(false);
                        button.setText(pluginContext.getString(R.string.stop));
                        cotInjector.setBounds(lat1, lon1, lat2, lon2);
                        cotInjector.setCount(count);
                        cotInjector.setInterval(interval);
                        cotInjector.setThreads(threads);
                        cotInjector.setUpdates(updates);
                        cotInjector.start();
                    } catch (Exception ex) {
                        Toast.makeText(pluginContext, "Invalid entry(s)", Toast.LENGTH_SHORT).show();
                    }
                } else {
                    button.setText(pluginContext.getString(R.string.start));
                    cotInjector.stop();
                    lat1Entry.setEnabled(true);
                    lon1Entry.setEnabled(true);
                    lat2Entry.setEnabled(true);
                    lon2Entry.setEnabled(true);
                    countEntry.setEnabled(true);
                    countEntry.setText(Integer.toString(cotInjector.getCount()));
                    intervalEntry.setEnabled(true);
                    threadsEntry.setEnabled(true);
                    resetButton.setEnabled(true);
                    updatesCheck.setEnabled(true);
                }
            }
        });

        resetButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                resetAction.run();
            }
        });

    }
}
