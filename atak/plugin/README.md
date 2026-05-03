# TERA.ai ATAK Plugin

Minimal Android/ATAK plugin project for TERA.ai.

## What is included

- `app/src`: plugin source, Android resources, and `plugin.xml`
- Gradle wrapper and project Gradle files
- ProGuard files required by the TAK dev plugin
- `tools/README.md`: local SDK tool notes
- `scripts/build_release.sh`: build the CIV release APK
- `scripts/install_device.sh`: install the built plugin to a connected ATAK device

Generated build output, IDE files, local SDK paths, and device-specific config are ignored.

## Local setup

1. Install Android Studio / Android SDK.
2. `cp template.local.properties local.properties` and set `sdk.dir` to your
   Android SDK path.
3. Download the ATAK-CIV SDK 5.7.0.3 from PAR Government's TAK Product Center.
   Extract it locally. Do not add it to this repo.
4. Copy the SDK developer Gradle plugin and compile API jar into `tools/`:
   `cp <sdk-root>/atak-gradle-takdev.jar tools/`
   `cp <sdk-root>/main.jar tools/`
5. Copy the SDK ProGuard mapping and development keystore into `tools/`:
   `cp <sdk-root>/mapping.txt tools/`
   `cp <sdk-root>/android_keystore tools/`
6. `tools/USGS_Topo_TERA.xml` is the custom map source shipped with this
   plugin.

`tools/` is gitignored except for documentation and map-source XML. The
keystore and SDK jars stay on your laptop. Production builds need a
production-trusted key.

## Build

```zsh
./scripts/build_release.sh
```

APK output:

```text
app/build/outputs/apk/civ/release/ATAK-Plugin-TERA-0.1--5.7.0-civ-release.apk
```

## Install to ATAK Device

Connect the Android device with USB debugging enabled, then run:

```zsh
./scripts/install_device.sh
```

This plugin is development-signed. It is expected to load in the ATAK SDK/developer build signed with the matching development key. Production ATAK builds may reject it unless the plugin is signed with a production-trusted key.
