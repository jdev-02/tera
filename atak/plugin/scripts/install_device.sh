#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")/.."

# Pick the newest APK by modification time so a freshly-rebuilt artifact is
# preferred over a stale-but-lexicographically-later leftover (e.g. v1.2.10
# would lex-sort before v1.2.2 with the previous `sort | tail` form). `ls -t`
# is portable across macOS (BSD) and Jetson (GNU).
pick_latest_apk() {
  ls -1t app/build/outputs/apk/civ/release/*.apk 2>/dev/null | head -n 1
}

APK="$(pick_latest_apk)"

if [[ -z "$APK" || ! -f "$APK" ]]; then
  ./scripts/build_release.sh
  APK="$(pick_latest_apk)"
fi

adb install -r "$APK"
