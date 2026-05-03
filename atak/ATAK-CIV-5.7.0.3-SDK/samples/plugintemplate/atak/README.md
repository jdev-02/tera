# ATAK Lane

Owner: P4.

The Android plugin in `app/` is the first native ATAK surface for TERA. It currently provides a toolbar pane that posts an operator prompt to a configurable `/plan` endpoint and displays the response.

## Near-Term Tasks

1. Wire successful `/plan` responses into CoT route rendering.
2. Add verifier gate once P2 ships ML-DSA signer/verifier.
3. Support WinTAK fallback through the same GeoJSON/KML/CoT output contract.
4. Keep RFSim interoperability through GeoJSON/KML exports.
5. Keep Cesium-specific terrain preview outside the plugin; the plugin consumes `/plan` responses and renders ATAK route artifacts.

## Build

```sh
./gradlew assembleCivDebug
```

The CIV debug APK is emitted under `app/build/outputs/apk/civ/debug/`.
