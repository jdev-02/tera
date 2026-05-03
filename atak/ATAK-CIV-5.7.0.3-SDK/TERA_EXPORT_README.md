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
2. Copy `template.local.properties` to `local.properties`.
3. Set `sdk.dir` to your Android SDK path.
4. Put the ATAK SDK dev Gradle plugin at:

   `tools/atak-gradle-takdev.jar`

5. Put the ATAK SDK development keystore at:

   `tools/android_keystore`

These two `tools/` files are local SDK artifacts and should not be committed to a public repo unless you have confirmed you are allowed to redistribute them.

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
