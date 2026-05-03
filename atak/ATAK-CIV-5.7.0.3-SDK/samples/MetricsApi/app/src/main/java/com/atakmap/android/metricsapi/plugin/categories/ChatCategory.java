package com.atakmap.android.metricsapi.plugin.categories;

import android.os.Bundle;

import androidx.annotation.NonNull;

import com.atakmap.android.maps.MapView;
import com.atakmap.android.metrics.MetricsUtils;

public class ChatCategory extends Category {

    final public String clazz;
    final public String elementName;
    final public String actionType;
    final public String callsign;
    final public int keyEventAction;
    final public int keyEventKeyCode;
    final public int keyPressed;
    final public boolean hasFocus;
    final public String selected;
    final public String resultingMessage;
    final public String status;
    final public String reason;

    public ChatCategory(Bundle bundle) {
        clazz = bundle.getString(MetricsUtils.FIELD_CLASS);
        elementName = bundle.getString(MetricsUtils.FIELD_ELEMENT_NAME);
        actionType = bundle.getString(MetricsUtils.FIELD_ACTION_TYPE);
        callsign = bundle.getString(MetricsUtils.FIELD_CALLSIGN);
        keyEventAction = bundle.getInt(MetricsUtils.FIELD_KEYEVENT_ACTION, -1);
        keyEventKeyCode = bundle.getInt(MetricsUtils.FIELD_KEYEVENT_KEYCODE, -1);
        keyPressed = bundle.getInt(MetricsUtils.FIELD_KEYEVENT_KEYPRESSED, -1);
        hasFocus = bundle.getBoolean(MetricsUtils.FIELD_HAS_FOCUS);


            selected = bundle.getString(MetricsUtils.FIELD_SELECTED);
            resultingMessage = bundle.getString(MetricsUtils.FIELD_RESULTING_MESSAGE);
            status = bundle.getString(MetricsUtils.FIELD_STATUS);
            reason = bundle.getString("reason");

    }

    @NonNull
    @Override
    public String toString() {
        return "ChatCategory{" +
                "clazz='" + clazz + '\'' +
                ", elementName='" + elementName + '\'' +
                ", actionType='" + actionType + '\'' +
                ", callsign='" + callsign + '\'' +
                ", keyEventAction=" + keyEventAction +
                ", keyEventKeyCode=" + keyEventKeyCode +
                ", keyPressed=" + keyPressed +
                ", hasFocus=" + hasFocus +
                ", selected='" + selected + '\'' +
                ", resultingMessage='" + resultingMessage + '\'' +
                ", status='" + status + '\'' +
                ", reason='" + reason + '\'' +
                '}';
    }
}
