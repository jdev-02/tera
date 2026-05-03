package com.atakmap.android.plugintemplate

import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ProvideTextStyle
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.dp
import com.atakmap.android.dropdown.DropDown.OnStateListener
import com.atakmap.android.dropdown.DropDownReceiver
import com.atakmap.android.maps.MapView
import com.atakmap.android.plugintemplate.plugin.R
import com.atakmap.coremap.log.Log

class PluginTemplateDropDownReceiver(
    mapView: MapView?,
    private val pluginContext: Context
) : DropDownReceiver(mapView), OnStateListener {

    /**
     * This class is a workaround for the fact that [ComposeView] needs the [pluginContext] to load
     * resources, but the [hostContext]'s application context.
     */
    private class ComposeContext(val hostContext: Context, val pluginContext: Context) :
        ContextWrapper(pluginContext) {
        override fun getApplicationContext(): Context {
            return hostContext.applicationContext
        }
    }

    /**************************** PUBLIC METHODS  */
    public override fun disposeImpl() {}

    /**************************** INHERITED METHODS  */
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return

        val view =
            ComposeView(ComposeContext(mapView.context, pluginContext)).apply {
                setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnDetachedFromWindow)
                setContent {
                    val colors = darkColorScheme()
                    MaterialTheme(colorScheme = colors) {
                        ProvideTextStyle(value = TextStyle(color = MaterialTheme.colorScheme.onBackground)) {
                            Row {
                                Icon(
                                    painter = painterResource(id = R.drawable.ic_launcher),
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.onBackground,
                                    modifier = Modifier.size(40.dp)
                                )
                                Text("PluginTemplate")
                            }
                        }
                    }
                }
            }

        if (action == SHOW_PLUGIN) {
            Log.d(TAG, "showing plugin drop down")
            showDropDown(
                view, HALF_WIDTH, FULL_HEIGHT, FULL_WIDTH,
                HALF_HEIGHT, false, this
            )
        }
    }

    override fun onDropDownSelectionRemoved() {}
    override fun onDropDownVisible(v: Boolean) {}
    override fun onDropDownSizeChanged(width: Double, height: Double) {}
    override fun onDropDownClose() {}

    companion object {
        val TAG = PluginTemplateDropDownReceiver::class.java.simpleName
        const val SHOW_PLUGIN = "com.atakmap.android.plugintemplate.SHOW_PLUGIN"
    }
}