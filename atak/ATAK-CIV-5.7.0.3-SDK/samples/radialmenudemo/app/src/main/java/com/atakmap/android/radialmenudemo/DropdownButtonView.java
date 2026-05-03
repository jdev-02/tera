package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.util.AttributeSet;
import android.view.View;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.maps.MapDataRef;
import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.android.util.ATAKUtilities;
import com.atakmap.android.widgets.MapWidget;
import com.atakmap.android.widgets.WidgetIcon;

import gov.tak.api.widgets.IMapWidget;

public class DropdownButtonView extends LinearLayout {

    public DropdownButtonView(Context context) {
        super(context);
    }

    public DropdownButtonView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    void populateLayout(IMapWidget widget) {

        if (widget instanceof MapMenuButtonWidget) {
            final MapMenuButtonWidget buttonWidget = (MapMenuButtonWidget) widget;

            final int iconState = 0;
            final int bitmapPixels = 96;

            final WidgetIcon icon = buttonWidget.getIcon();
            final MapDataRef iconMapDataRef = icon.getIconRef(iconState);
            final String iconUri = iconMapDataRef.toUri();

            Bitmap bitmap = ATAKUtilities.getUriBitmap(iconUri);
            if (bitmapPixels != bitmap.getWidth())
                bitmap = Bitmap.createScaledBitmap(bitmap, bitmapPixels, bitmapPixels, true);
            ImageView imageView = (ImageView) findViewById(R.id.icon_view);
            imageView.setImageBitmap(bitmap);

            TextView onclickView = (TextView) findViewById(R.id.onclick_value);
            if (null == buttonWidget.getOnButtonClickHandler()) {
                onclickView.setText(null);
            } else {
                onclickView.setText(buttonWidget.getOnButtonClickHandler().toString());
            }

            TextView submenuView = (TextView) findViewById(R.id.submenu_value);
            ImageButton submenuButton = (ImageButton) findViewById(R.id.show_submenu);
            if (null == buttonWidget.getSubmenu()) {
                submenuView.setText(null);
                submenuButton.setVisibility(View.INVISIBLE);
            } else {
                submenuView.setText(buttonWidget.getSubmenu().toString());
                submenuButton.setVisibility(View.VISIBLE);
                submenuButton.setOnClickListener(new OnClickListener() {
                    @Override
                    public void onClick(View view) {
                        Intent intent = new Intent(DropdownMenuReceiver.SHOW_SUBMENU);
                        intent.putExtra("buttonWidgetHash",
                                buttonWidget.hashCode());
                        AtakBroadcast.getInstance().sendBroadcast(intent);
                    }
                });
            }

            ImageButton editButton = (ImageButton) findViewById(R.id.edit_menu);
            editButton.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View view) {
                    Intent intent = new Intent(ButtonReceiver.EDIT_BUTTON);
                    intent.putExtra("buttonWidgetHash", buttonWidget.hashCode());
                    AtakBroadcast.getInstance().sendBroadcast(intent);
                }
            });

            ImageButton propsButton = (ImageButton) findViewById(R.id.prefs_menu);
            propsButton.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View view) {
                    Intent intent = new Intent(ButtonReceiver.EDIT_PROPS);
                    intent.putExtra("buttonWidgetHash", buttonWidget.hashCode());
                    AtakBroadcast.getInstance().sendBroadcast(intent);
                }
            });

            ImageButton deleteButton = (ImageButton) findViewById(R.id.delete_button);
            deleteButton.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View view) {
                    Intent intent = new Intent(MenuReceiver.DELETE_BUTTON);
                    intent.putExtra("buttonWidgetHash", buttonWidget.hashCode());
                    AtakBroadcast.getInstance().sendBroadcast(intent);
                }
            });
        }
    }
}
