package com.atakmap.android.radialmenudemo;

import android.app.AlertDialog;
import android.content.DialogInterface;

import com.atakmap.android.menu.MapMenuButtonWidget;

public class ButtonDialogHandler implements DialogInterface.OnClickListener {

    public interface CompletionHandler {
        void OnComplete(AlertButtonView buttonView,
                        MapMenuButtonWidget buttonWidget);
    }

    final AlertButtonView buttonView;
    final MapMenuButtonWidget buttonWidget;
    final CompletionHandler handler;

    public ButtonDialogHandler(AlertButtonView buttonView,
                               MapMenuButtonWidget buttonWidget,
                               CompletionHandler handler) {
        this.buttonView = buttonView;
        this.buttonWidget = buttonWidget;
        this.handler = handler;
    }

    public ButtonDialogHandler(AlertButtonView buttonView,
                               MapMenuButtonWidget buttonWidget) {
        this(buttonView, buttonWidget, null);
    }

    @Override
    public void onClick(DialogInterface dialogInterface, int which) {

        if (which == AlertDialog.BUTTON_POSITIVE) {
            buttonWidget.setIcon(buttonView.getWidgetIcon());
            buttonWidget.setDisabled(buttonView.getDisabled());
            buttonWidget.setOnButtonClickHandler(buttonView.getOnClick());
            buttonWidget.setSubmenu(buttonView.getSubmenu());

            final float width = buttonView.getButtonWidth();
            final float radius = buttonView.getButtonRadius();
            buttonWidget.setButtonSize(buttonWidget.getButtonSpan(), width);
            buttonWidget.setOrientation(buttonWidget.getOrientationAngle(), radius);
            buttonWidget.setLayoutWeight(buttonView.getButtonWeight());

            if (null != handler)
                handler.OnComplete(buttonView, buttonWidget);
        }
    }
}
