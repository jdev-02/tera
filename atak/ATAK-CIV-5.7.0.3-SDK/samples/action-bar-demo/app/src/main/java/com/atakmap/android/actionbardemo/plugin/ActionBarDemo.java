
package com.atakmap.android.actionbardemo.plugin;

import android.content.Context;
import android.content.Intent;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

import com.atak.plugins.impl.PluginContextProvider;
import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.navigation.views.NavView;
import com.atakmap.android.navigation.views.buttons.NavButtonsVisibilityListener;

import gov.tak.api.plugin.IPlugin;
import gov.tak.api.plugin.IServiceController;
import gov.tak.api.ui.IHostUIService;
import gov.tak.api.ui.Pane;
import gov.tak.api.ui.PaneBuilder;
import gov.tak.api.ui.ToolbarItem;
import gov.tak.api.ui.ToolbarItemAdapter;
import gov.tak.platform.marshal.MarshalManager;

public class ActionBarDemo implements IPlugin {

    IServiceController serviceController;
    Context pluginContext;
    IHostUIService uiService;
    ToolbarItem toolbarItemHalf;
    ToolbarItem toolbarItemFull;
    Pane templatePaneHalf;
    Pane templatePaneFull;

    public ActionBarDemo(IServiceController serviceController) {
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
        toolbarItemHalf = new ToolbarItem.Builder(
                pluginContext.getString(R.string.app_name)  + " Half",
                MarshalManager.marshal(
                        pluginContext.getResources().getDrawable(R.drawable.ic_launcher),
                        android.graphics.drawable.Drawable.class,
                        gov.tak.api.commons.graphics.Bitmap.class))
                .setListener(new ToolbarItemAdapter() {
                    @Override
                    public void onClick(ToolbarItem item) {
                        templatePaneHalf = showPane(templatePaneHalf, 0.5D);
                    }
                })
                .build();
        toolbarItemFull = new ToolbarItem.Builder(
                pluginContext.getString(R.string.app_name)  + " Full",
                MarshalManager.marshal(
                        pluginContext.getResources().getDrawable(R.drawable.ic_launcher),
                        android.graphics.drawable.Drawable.class,
                        gov.tak.api.commons.graphics.Bitmap.class))
                .setListener(new ToolbarItemAdapter() {
                    @Override
                    public void onClick(ToolbarItem item) {
                        templatePaneFull = showPane(templatePaneFull, 1.0D);
                    }
                })
                .build();
    }

    @Override
    public void onStart() {
        // the plugin is starting, add the button to the toolbar
        if (uiService == null)
            return;

        uiService.addToolbarItem(toolbarItemHalf);
        uiService.addToolbarItem(toolbarItemFull);
    }

    @Override
    public void onStop() {
        // the plugin is stopping, remove the button from the toolbar
        if (uiService == null)
            return;

        uiService.removeToolbarItem(toolbarItemHalf);
        uiService.removeToolbarItem(toolbarItemFull);
    }

    private Pane showPane(Pane p, double ratio) {
        // instantiate the plugin view if necessary
        if(p == null) {
            // Remember to use the PluginLayoutInflator if you are actually inflating a custom view
            // In this case, using it is not necessary - but I am putting it here to remind
            // developers to look at this Inflator

            final NavView actionBar = NavView.getInstance();
            final boolean[] actionBarVisible = new boolean[] {actionBar.buttonsVisible()};
            final boolean[] actionBarEnabled = new boolean[] {!actionBar.buttonsLocked()};

            View mainLayout = PluginLayoutInflater.inflate(pluginContext,
                    R.layout.main_layout, null);
            p = new PaneBuilder(mainLayout)
                    // relative location is set to default; pane will switch location dependent on
                    // current orientation of device screen
                    .setMetaValue(Pane.RELATIVE_LOCATION, Pane.Location.Default)
                    // pane will take up ratio% of screen width in landscape mode
                    .setMetaValue(Pane.PREFERRED_WIDTH_RATIO, ratio)
                    // pane will take up ratio% of screen height in portrait mode
                    .setMetaValue(Pane.PREFERRED_HEIGHT_RATIO, ratio)
                    .build();

            final TextView actionBarVisibleTextView = mainLayout.findViewById(R.id.actionBarVisibilityTextView);
            actionBar.addButtonVisibilityListener(new NavButtonsVisibilityListener() {
                @Override
                public void onNavButtonsVisible(boolean b) {
                    actionBarVisibleTextView.setText("Action Bar Visibility: " +
                                (actionBar.buttonsVisible() ? "Visible" : "Not Visible"));
                }
            });
            actionBarVisibleTextView.setText("Action Bar Visibility: " +
                    (actionBar.buttonsVisible() ? "Visible" : "Not Visible"));

            final Button actionBarShow = mainLayout.findViewById(R.id.showActionBarButton);
            actionBarShow.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    // check if Action Bar already showing
                    if(actionBar.buttonsVisible()) return;

                    Intent showButtons = new Intent(NavView.TOGGLE_BUTTONS);
                    AtakBroadcast.getInstance().sendBroadcast(showButtons);
                }
            });

            final Button actionBarHide = mainLayout.findViewById(R.id.hideActionBarButton);
            actionBarHide.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    // check if Action Bar already showing
                    if(!actionBar.buttonsVisible()) return;

                    Intent hideButtons = new Intent(NavView.TOGGLE_BUTTONS);
                    AtakBroadcast.getInstance().sendBroadcast(hideButtons);
                }
            });

            final TextView actionBarButtonsEnabledTextView = mainLayout.findViewById(R.id.actionBarEnabledTextView);
            // NOTE: there is no callback method on buttons locked state changed.
            actionBarButtonsEnabledTextView.setText("ActionBar Buttons Enabled: " + !actionBar.buttonsLocked());

            final Button actionBarEnable = mainLayout.findViewById(R.id.enableActionBarButton);
            actionBarEnable.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    // check if Action Bar buttons disabled
                    if(!actionBar.buttonsLocked()) return;

                    Intent enableButtons = new Intent(NavView.LOCK_BUTTONS);
                    enableButtons.putExtra("lock", false);
                    AtakBroadcast.getInstance().sendBroadcast(enableButtons);

                    actionBarButtonsEnabledTextView.setText("Action Bar Buttons Enabled: " + true);
                }
            });

            final Button actionBarDisable = mainLayout.findViewById(R.id.disableActionBarButton);
            actionBarDisable.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    // check if Action Bar buttons disabled
                    if(actionBar.buttonsLocked()) return;

                    Intent disableButtons = new Intent(NavView.LOCK_BUTTONS);
                    disableButtons.putExtra("lock", true);
                    AtakBroadcast.getInstance().sendBroadcast(disableButtons);

                    actionBarButtonsEnabledTextView.setText("Action Bar Buttons Enabled: " + false);
                }
            });

            final TextView mapControlWidgetsVisibleTextView = mainLayout.findViewById(R.id.mapControlWidgetsVisibleTextView);
            // NOTE: there is no callback method on buttons locked state changed.
            mapControlWidgetsVisibleTextView.setText("Map Control Widgets Visible: " +
                    (actionBar.findViewById(com.atakmap.app.R.id.side_layout).getVisibility() == View.VISIBLE));

            final Button mapControlWidgetsShow = mainLayout.findViewById(R.id.showMapControlWidgetsButton);
            mapControlWidgetsShow.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    View widgets = actionBar.findViewById(com.atakmap.app.R.id.side_layout);
                    // check if widgets are visible
                    if(widgets.getVisibility() == View.VISIBLE) return;

                    widgets.setVisibility(View.VISIBLE);
                    mapControlWidgetsVisibleTextView.setText("Map Control Widgets Visible: " + true);
                }
            });

            final Button mapControlWidgetsHide = mainLayout.findViewById(R.id.hideMapControlWidgetsButton);
            mapControlWidgetsHide.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    View widgets = actionBar.findViewById(com.atakmap.app.R.id.side_layout);
                    // check if widgets are visible
                    if(widgets.getVisibility() == View.GONE) return;

                    widgets.setVisibility(View.GONE);
                    mapControlWidgetsVisibleTextView.setText("Map Control Widgets Visible: " + false);
                }
            });
        }

        // if the plugin pane is not visible, show it!
        if(!uiService.isPaneVisible(p)) {
            uiService.showPane(p, null);
        }

        return p;
    }
}
