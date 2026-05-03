#!/usr/bin/env zsh
set -euo pipefail

cd "$(dirname "$0")/.."

missing=()
[[ -f tools/atak-gradle-takdev.jar ]] || missing+=(tools/atak-gradle-takdev.jar)
[[ -f tools/main.jar ]] || missing+=(tools/main.jar)
[[ -f tools/mapping.txt ]] || missing+=(tools/mapping.txt)
[[ -f tools/android_keystore ]] || missing+=(tools/android_keystore)

if (( ${#missing[@]} > 0 )); then
  print -u2 "Missing local ATAK SDK artifact(s):"
  for path in "${missing[@]}"; do
    print -u2 "  - $path"
  done
  print -u2 "Copy them from your local ATAK-CIV SDK. They are intentionally gitignored."
  exit 1
fi

./gradlew assembleCivRelease
