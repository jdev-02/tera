#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")/.."

# Pick the newest APK by modification time so a freshly-rebuilt artifact is
# always preferred over a stale-but-lexicographically-later leftover. ``ls -t``
# is portable across macOS (BSD) and Jetson (GNU) without relying on GNU-only
# ``find -printf '%T@'``.
pick_latest_apk() {
  local dir="app/build/outputs/apk/civ/release"
  if [[ ! -d "$dir" ]]; then
    return 0
  fi
  ls -1t "$dir"/*.apk 2>/dev/null | head -n 1
}

APK="$(pick_latest_apk)"

if [[ -z "$APK" || ! -f "$APK" ]]; then
  ./scripts/build_release.sh
  APK="$(pick_latest_apk)"
fi

adb install -r "$APK"
