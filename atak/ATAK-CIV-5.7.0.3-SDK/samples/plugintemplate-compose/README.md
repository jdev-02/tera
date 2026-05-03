# Using (Jetpack) Compose in ATAK

*NOTE*: Consider this experimental, there isn't official ATAK support for compose, and while I was able to get it to work, you may run into issues and crashes.

I'm starting from PluinTemplateLegacy, these are the steps/changes I made to get Compose to work.

### steps
0. my system has Java 17 installed, which doesn't support gradle $< 6.9$ so I let android studio upgrade gradle to 7.x
0. `Plugin with id 'atak-takdev-plugin' not found` - you get this error if your tak credentials aren't set (set them in `local.properties`)
0. upgrade the android gradle plugin to 7.x (i did 7.4.2)
    * the old version used (4.x) is too old, and if you try to use it you'll probably get an error like: `Unable to make field private final java.lang.String java.io.File.path accessible: module java.base does not "opens java.io" to unnamed module @27624b5b`
0. remove `android.enableR8=false` from `gradle.properties`, the option has been removed from newer AGP
0. change `compileSdkVersion` and `targetSdkVersion` to 33, which is the min required for the compose libraries (the versions i used)
0. go to `Tools > Kotlin > Configure Kotlin in Project`, choose `Android with Gradle`, and `All modudles`.  I chose version `1.8.20`
0. add the following to `build.gradle` in project root (the auto conversion misses it, so the kotlin plugin can't be found):
    ```
    buildScript {
        ext.kotlin_version = '1.8.20'
        ...
        
        dependencies {
            ...
            classpath "org.jetbrains.kotlin:kotlin-gradle-plugin:$kotlin_version"
            ...
        }
    ```
0. add the following config lines to the app module's `build.gradle`:
    ```
    android {
        ...
        
        kotlinOptions {
            jvmTarget = JavaVersion.VERSION_1_8.toString()
        }

        buildFeatures.compose = true
        composeOptions.kotlinCompilerExtensionVersion = "1.4.4"
    }
    ```
    * if you get the following error, you probably forgot this: `NoSuchMethodError: No virtual method setContent(Lkotlin/jvm/functions/Function0;)V in class Landroidx/compose/ui/platform/ComposeView;`
0. the Kotlin auto conversion adds the line `implementation 'androidx.core:core-ktx:+'` to the app's `build.gradle`.  This can cause version issues, either switch it to a compatible version (like `1.8.0` to match atak's core) or just remove this line if you don't need the provided extension functions
0. convert (at least) `PluginTemplateDropDownReceiver` to Kotlin (`ctrl+alt+shift+k`)
0. convert `templateView` from an xml layout inflation to a `ComposeView` (see blow) (it's also better to do this lazily in `onReceive`)

### `ComposeView`

`ComposeView` is a special view provided for interoperability between Compose and old style Views: https://developer.android.com/jetpack/compose/migrate/interoperability-apis

Create a `ComposeView` object, use `setContent {}` to set the Compose content, and then pass the view object to ATAK as you would a normally infalted view.

A `ComposeView` can also be nested inside a container or layout view if desired.

#### **IMPORTANT**:
You must change the default composition strategy of the `ComposeView`.  The current default causes it to check if the view is part of a "pooling" container, which calls a method that doesn't exist in ATAK's core `ViewKt` class, which will crash atak with a `NoSuchMethod` exception when the back button is pressed.

This can be done by calling the following on the `ComposeView`:
```
setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnDetachedFromWindow)
```

**NOTE**: most strategies will dispose your view when the panel is closed, so you don't want to cache your view but re-create it every time

#### A note on `Context`s

If you don't use any local resources, you can use atak's host context to create the `ComposeView`:
```
    templateView =
        ComposeView(mapView.context).apply {
            ...
        }
```

If you need compose to load resources (like with `painterResource`), you need to pass your plugin's context to `ComposeView`.  The issue is that compose will try and get the application context from the context that is passed to it, which is null on the plugin's context.

The easiest workaround for this is to use `ContextWrapper` to add this particular functionality to your plugin's context:

```
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

...

    templateView =
        ComposeView(ComposeContext(mapView.context, pluginContext)).apply {
            ...
        }

```

