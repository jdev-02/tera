package com.atakmap.android.elevation.dsm;

import android.annotation.SuppressLint;
import android.content.Context;
import android.os.Bundle;
import android.preference.Preference;
import android.preference.PreferenceScreen;

import com.atakmap.android.preference.PluginPreferenceFragment;
import com.atakmap.android.elevation.dsm.plugin.R;
import com.atakmap.android.util.PdfHelper;
import com.atakmap.coremap.filesystem.FileSystemUtils;
import com.atakmap.coremap.log.Log;

import java.io.File;


public class DsmManagerPreferenceFragment extends PluginPreferenceFragment {

    private static Context pluginContext;

    public static final String USER_GUIDE = "usermanual.pdf";
    public static final String USER_GUIDE_FULL_PATH = FileSystemUtils.getRoot() + File.separator + "tools" + File.separator + "dsm" +
            File.separator + "ATAK_DSM User Guide.pdf";

    public DsmManagerPreferenceFragment() {
        super(pluginContext, R.xml.preferences);
    }

    @SuppressLint("ValidFragment")
    public DsmManagerPreferenceFragment(Context context) {
        super(context, R.xml.preferences);
        pluginContext = context;
    }

    @Override
    public String getSubTitle() {
        return getSubTitle("Tools Preferences",
                "DSM Manager Settings");
    }

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Preference manual = findPreference("manual");
        manual.setOnPreferenceClickListener(
                new Preference.OnPreferenceClickListener() {
                    @Override
                    public boolean onPreferenceClick(Preference preference) {
                        PdfHelper.extractAndShow(pluginContext,getActivity(),USER_GUIDE,USER_GUIDE_FULL_PATH,true);
                        return true;
                    }
                });

    }

}
