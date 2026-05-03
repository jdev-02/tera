
package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.content.Intent;
import android.view.View;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.ListView;

import com.atak.plugins.impl.PluginLayoutInflater;
import com.atakmap.android.dropdown.DropDown;
import com.atakmap.android.dropdown.DropDownReceiver;
import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.ipc.DocumentedExtra;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.maps.MapView;
import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.menu.MapMenuEventListener;
import com.atakmap.android.menu.MapMenuReceiver;
import com.atakmap.android.menu.MapMenuWidget;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.coremap.log.Log;
import com.atakmap.coremap.maps.coords.GeoPoint;

import gov.tak.api.widgets.IMapMenuWidget;
import gov.tak.api.widgets.IMapWidget;
import gov.tak.api.widgets.IParentWidget;

public class DropdownMenuReceiver extends DropDownReceiver implements
        DropDown.OnStateListener,
        MapMenuEventListener,
        MenuWidgetFactoryObserver.MapMenuFactoryListener,
        IParentWidget.OnWidgetListChangedListener
{

    public static final String TAG = DropdownMenuReceiver.class
            .getSimpleName();

    public static final String SHOW_PLUGIN = "com.atakmap.android.radialmenudemo.SHOW_PLUGIN";
    public static final String SHOW_SUBMENU = "com.atakmap.android.radialmenudemo.SHOW_SUBMENU";
    public static final String SHOW_PARENT = "com.atakmap.android.radialmenudemo.SHOW_PARENT";
    private final ListView pluginView;

    private final DropdownMenuView menuView;
    private final DropdownButtonAdapter dropdownButtonAdapter;

    private final MenuWidgetFactoryObserver factoryObserver;

    private final MenuReceiver menuReceiver;
    private final ButtonReceiver buttonReceiver;

    private final ImageButton dropperButton;

    IMapMenuWidget currentMenuWidget;
    MapItem currentMapItem;

    public DropdownMenuReceiver(final MapView mapView,
                                final Context context) {
        super(mapView);

        pluginView = new ListView(context);

        LinearLayout titleView = (LinearLayout) PluginLayoutInflater.inflate(context,
                        R.layout.dropdown_title, null);

        menuView = (DropdownMenuView) PluginLayoutInflater.inflate(context,
                R.layout.dropdown_menu, null);
        menuView.setVisibility(View.INVISIBLE);

        dropdownButtonAdapter = new DropdownButtonAdapter(context, R.layout.dropdown_button);

        pluginView.setAdapter(dropdownButtonAdapter);
        pluginView.addHeaderView(titleView);
        pluginView.addHeaderView(menuView);
        pluginView.setHeaderDividersEnabled(false);

        menuReceiver = new MenuReceiver(mapView, context);
        buttonReceiver = new ButtonReceiver(mapView, context);

        factoryObserver = new MenuWidgetFactoryObserver();
        factoryObserver.registerMapMenuFactoryListener(this);

        currentMenuWidget = null;
        currentMapItem = null;

        AtakBroadcast.DocumentedIntentFilter submenuShowFilter =
                new AtakBroadcast.DocumentedIntentFilter();
        submenuShowFilter.addAction(SHOW_SUBMENU,
                "Show a Submenu MapMenuWidget",
                new DocumentedExtra[]{
                        new DocumentedExtra("buttonWidgetHash",
                                "Submenu parent MapMenuButtonWidget instance",
                                false, Integer.class)
                });
        AtakBroadcast.getInstance().registerReceiver(this, submenuShowFilter);

        AtakBroadcast.DocumentedIntentFilter parentShowFilter =
                new AtakBroadcast.DocumentedIntentFilter();
        parentShowFilter.addAction(SHOW_PARENT,
                "Show a parent MapMenuWidget",
                new DocumentedExtra[]{
                        new DocumentedExtra("buttonWidgetHash",
                                "Submenu parent MapMenuButtonWidget instance",
                                false, Integer.class)
                });
        AtakBroadcast.getInstance().registerReceiver(this, parentShowFilter);

        dropperButton = (ImageButton) titleView.findViewById(R.id.dropper_button);
        dropperButton.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                // FIXME - ATAK Radial Menu API should have
                // menu open / close eventing that is equal for
                // open on item and open on map. Current eventing
                // only applies to open on item.
                // FIXME - OpenOnMap has behavior where first click
                // opens menu and second click clears menu which is
                // different than the open on item semantic
                // FIXME - State hackery below should go away upon fixes
                // which relies on non zero length map button children
                if (dropdownButtonAdapter.isEmpty()) {
                    menuView.setVisibility(View.VISIBLE);
                }
                // the point of the click ...
                final GeoPoint geoPoint = mapView.getCenterPoint().get();
                Intent intent = new Intent(MapMenuReceiver.SHOW_MENU);
                intent.putExtra("point", geoPoint.toString());
                AtakBroadcast.getInstance().sendBroadcast(intent);
                // FIXME - More state hackery below should go away upon fixes
                // which relies on non zero length map button children
                if (!dropdownButtonAdapter.isEmpty()) {
                    menuView.setVisibility(View.INVISIBLE);
                    dropdownButtonAdapter.clear();
                    dropdownButtonAdapter.notifyDataSetChanged();
                    currentMenuWidget = null;
                    currentMapItem = null;
                }
            }
        });
    }

    @Override
    public void disposeImpl() {
        if (null != currentMenuWidget)
            currentMenuWidget.removeOnWidgetListChangedListener(this);
        factoryObserver.unregisterMapMenuFactoryListener(this);
        AtakBroadcast.getInstance().unregisterReceiver(buttonReceiver);
        AtakBroadcast.getInstance().unregisterReceiver(menuReceiver);
        // always called to be sure we unregister.
        MapMenuReceiver.getInstance().removeEventListener(this);
        MapMenuReceiver.getInstance().unregisterMapMenuFactory(factoryObserver);
    }

    @Override
    public void onReceive(Context context, Intent intent) {

        final String action = intent.getAction();
        if (action == null)
            return;

        switch (action) {
            case SHOW_PLUGIN: {
                Log.d(TAG, "showing plugin drop down");
                showDropDown(pluginView, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH,
                        HALF_HEIGHT, this);
            }
            break;
            case SHOW_SUBMENU: {
                final int buttonHash = intent.getIntExtra("buttonWidgetHash", 0);
                if (0 == buttonHash) {
                    Log.w(TAG, "Logic error; button hash not provided");
                } else {
                    MapMenuButtonWidget buttonWidget =
                            WidgetResolver.resolveButtonWidget(buttonHash, currentMenuWidget);
                    if (null == buttonWidget) {
                        Log.w(TAG, "Logic error; button widget cannot be resolved");
                    } else {
                        onMapMenu(buttonWidget);
                    }
                }
            }
            break;
            case SHOW_PARENT: {
                final int buttonHash = intent.getIntExtra("buttonWidgetHash", 0);
                if (0 == buttonHash) {
                    Log.w(TAG, "Logic error; button hash not provided");
                } else {
                    MapMenuWidget menuWidget =
                            WidgetResolver.resolveButtonParentWidget(buttonHash);
                    if (null == menuWidget) {
                        Log.w(TAG, "Logic error; button widget parent cannot be resolved");
                    } else {
                        onMapMenu(menuWidget);
                    }
                }
            }
            break;
            default: {
                Log.w(TAG, "Logic error; unexpected action: " + action);
            }
            break;
        }
    }

    @Override
    public boolean onShowMenu(MapItem item) {
        dropperButton.setVisibility(View.INVISIBLE);
        menuView.setVisibility(View.VISIBLE);
        // return true to stop processing by subsequent listeners
        return false;
    }

    @Override
    public void onHideMenu(MapItem item) {
        menuView.setVisibility(View.INVISIBLE);
        dropdownButtonAdapter.clear();
        dropdownButtonAdapter.notifyDataSetChanged();
        currentMenuWidget = null;
        currentMapItem = null;
        dropperButton.setVisibility(View.VISIBLE);
    }

    private void onMapMenu(IMapMenuWidget menuWidget,
                           MapMenuButtonWidget parentButton) {
        if (null != currentMenuWidget)
            currentMenuWidget.removeOnWidgetListChangedListener(this);
        currentMenuWidget = menuWidget;
        currentMenuWidget.addOnWidgetListChangedListener(this);
        menuView.populateLayout(currentMenuWidget, currentMapItem, parentButton);
        dropdownButtonAdapter.clear();
        dropdownButtonAdapter.addAll(currentMenuWidget.getChildren());
        dropdownButtonAdapter.notifyDataSetChanged();
    }

    private void onMapMenu(MapMenuWidget menuWidget) {
        onMapMenu(menuWidget, null);
    }

    private void onMapMenu(MapMenuButtonWidget buttonWidget) {
        onMapMenu(buttonWidget.getSubmenu(), buttonWidget);
    }

    @Override
    public boolean onMenuWidgetCreation(MapMenuWidget menuWidget, MapItem mapItem) {
        currentMapItem = mapItem;
        onMapMenu(menuWidget);
        return false;
    }

    private void onWidgetChild(IParentWidget abstractParentWidget) {
        if (currentMenuWidget == abstractParentWidget) {
            dropdownButtonAdapter.clear();
            dropdownButtonAdapter.addAll(currentMenuWidget.getChildren());
            dropdownButtonAdapter.notifyDataSetChanged();
        }
    }

    @Override
    public void onWidgetAdded(IParentWidget abstractParentWidget, int i, IMapWidget mapWidget) {
        onWidgetChild(abstractParentWidget);
    }

    @Override
    public void onWidgetRemoved(IParentWidget abstractParentWidget, int i, IMapWidget mapWidget) {
        onWidgetChild(abstractParentWidget);
    }

    @Override
    public void onDropDownSelectionRemoved() {
        // no-op
    }

    @Override
    public void onDropDownClose() {
        // no-op; covered already with visible callback below ...
    }

    @Override
    public void onDropDownSizeChanged(double v, double v1) {
        // no-op
    }

    @Override
    public void onDropDownVisible(boolean b) {
        if (b) {
            MapMenuReceiver.getInstance().registerMapMenuFactory(factoryObserver);
            MapMenuReceiver.getInstance().addEventListener(this);
        } else {
            MapMenuReceiver.getInstance().removeEventListener(this);
            MapMenuReceiver.getInstance().unregisterMapMenuFactory(factoryObserver);
        }
    }
}
