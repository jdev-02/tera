#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")/.."

APK="app/build/outputs/apk/civ/release/ATAK-Plugin-TERA-0.1--5.7.0-civ-release.apk"

if [[ ! -f "$APK" ]]; then
  ./scripts/build_release.sh
fi

adb install -r "$APK"
