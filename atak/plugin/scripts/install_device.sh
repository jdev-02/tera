#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")/.."

APK="$(find app/build/outputs/apk/civ/release -maxdepth 1 -name '*.apk' -print 2>/dev/null | sort | tail -n 1)"

if [[ -z "$APK" || ! -f "$APK" ]]; then
  ./scripts/build_release.sh
  APK="$(find app/build/outputs/apk/civ/release -maxdepth 1 -name '*.apk' -print | sort | tail -n 1)"
fi

adb install -r "$APK"
