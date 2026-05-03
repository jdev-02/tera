package com.atakmap.android.radialmenudemo;

import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.util.AttributeSet;
import android.view.View;
import android.widget.ImageButton;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TableRow;
import android.widget.TextView;

import com.atakmap.android.ipc.AtakBroadcast;
import com.atakmap.android.maps.MapDataRef;
import com.atakmap.android.maps.MapItem;
import com.atakmap.android.menu.MapMenuButtonWidget;
import com.atakmap.android.menu.MapMenuWidget;
import com.atakmap.android.radialmenudemo.plugin.R;
import com.atakmap.android.util.ATAKUtilities;
import com.atakmap.android.widgets.WidgetIcon;

import gov.tak.api.widgets.IMapMenuWidget;


public class DropdownMenuView extends LinearLayout {

    public DropdownMenuView(Context context) {
        super(context);
    }

    public DropdownMenuView(Context context, AttributeSet attrs) {
        super(context, attrs);
    }

    public DropdownMenuView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
    }

    public void populateLayout(final IMapMenuWidget menuWidget, MapItem mapItem,
                               final MapMenuButtonWidget parentButton) {
        TextView titleView = (TextView) findViewById(R.id.menu_title);
        TextView typeView = (TextView) findViewById(R.id.menu_type);
        if (null == mapItem) {
            titleView.setText("OpenOnMap");
            typeView.setText("GeoPoint");
        } else {
            titleView.setText(mapItem.getTitle());
            typeView.setText(mapItem.getType());
        }

        ImageButton revertView = (ImageButton) findViewById(R.id.parent_menu);
        TableRow submenuRow = (TableRow) findViewById(R.id.submenu_header);

        if (null == parentButton) {
            revertView.setVisibility(View.INVISIBLE);
            submenuRow.setVisibility(View.INVISIBLE);
        } else {
            submenuRow.setVisibility(View.VISIBLE);
            final int iconState = 0;
            final int bitmapPixels = 64;
            final int iconColor = -1;

            final WidgetIcon icon = parentButton.getIcon();
            final MapDataRef iconMapDataRef = icon.getIconRef(iconState);
            final String iconUri = iconMapDataRef.toUri();

            Bitmap bitmap = ATAKUtilities.getUriBitmap(iconUri);
            if (bitmapPixels != bitmap.getWidth())
                bitmap = Bitmap.createScaledBitmap(bitmap, bitmapPixels, bitmapPixels, true);
            ImageView imageView = (ImageView) findViewById(R.id.icon_view);
            imageView.setImageBitmap(bitmap);

            TextView submenuView = (TextView) findViewById(R.id.submenu_value);
            submenuView.setText(menuWidget.toString());

            revertView.setVisibility(View.VISIBLE);
            revertView.setOnClickListener(new OnClickListener() {
                @Override
                public void onClick(View view) {
                    Intent intent = new Intent(DropdownMenuReceiver.SHOW_PARENT);
                    intent.putExtra("buttonWidgetHash", parentButton.hashCode());
                    AtakBroadcast.getInstance().sendBroadcast(intent);
                }
            });
        }

        ImageButton editView = (ImageButton) findViewById(R.id.edit_menu);
        editView.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View view) {
                Intent intent = new Intent(MenuReceiver.EDIT_MENU);
                intent.putExtra("menuWidgetHash", menuWidget.hashCode());
                AtakBroadcast.getInstance().sendBroadcast(intent);
            }
        });

        ImageButton addView = (ImageButton) findViewById(R.id.add_button);
        addView.setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View view) {
                Intent intent = new Intent(MenuReceiver.ADD_BUTTON);
                intent.putExtra("menuWidgetHash", menuWidget.hashCode());
                AtakBroadcast.getInstance().sendBroadcast(intent);
            }
        });
    }

}
