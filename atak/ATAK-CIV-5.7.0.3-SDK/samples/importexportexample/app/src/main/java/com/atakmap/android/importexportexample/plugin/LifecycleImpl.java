
package com.atakmap.android.importexportexample.plugin;

import android.content.Context;

import com.atak.plugins.impl.AbstractPlugin;
import com.atakmap.android.importexportexample.ImportExportExampleMapComponent;

import gov.tak.api.plugin.IServiceController;

public class LifecycleImpl extends AbstractPlugin {
    public LifecycleImpl(IServiceController serviceController) {
        super(serviceController, new ImportExportExampleMapComponent());
    }

}

