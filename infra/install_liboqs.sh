#!/usr/bin/env bash
# install_liboqs.sh -- Install liboqs system library on Linux / Ubuntu / Jetson.
#
# liboqs is a C library that provides post-quantum crypto primitives (ML-DSA, ML-KEM).
# liboqs-python wraps it. We need both.
#
# macOS users: don't run this. Run `brew install liboqs` instead.
#
# Run from the repo root:
#   bash infra/install_liboqs.sh
#
# After this completes, run:
#   make install-crypto

set -euo pipefail

echo "[install_liboqs] checking platform..."
case "$(uname)" in
    Darwin)
        echo "[install_liboqs] macOS detected. Use 'brew install liboqs' instead. Exiting."
        exit 1
        ;;
    Linux) ;;
    *) echo "[install_liboqs] unsupported OS: $(uname). Exiting."; exit 1 ;;
esac

echo "[install_liboqs] checking for liboqs already installed..."
if pkg-config --exists liboqs 2>/dev/null; then
    echo "[install_liboqs] liboqs already installed. Skipping."
    exit 0
fi

echo "[install_liboqs] installing build deps (sudo required)..."
sudo apt-get update -qq
sudo apt-get install -y -qq cmake ninja-build libssl-dev git pkg-config

LIBOQS_VERSION="0.10.0"
WORK_DIR="${TMPDIR:-/tmp}/liboqs-build"

echo "[install_liboqs] cloning liboqs ${LIBOQS_VERSION} into ${WORK_DIR}..."
rm -rf "$WORK_DIR"
git clone --depth=1 --branch "${LIBOQS_VERSION}" https://github.com/open-quantum-safe/liboqs.git "$WORK_DIR"

echo "[install_liboqs] configuring..."
cmake -S "$WORK_DIR" -B "$WORK_DIR/build" -GNinja \
    -DCMAKE_INSTALL_PREFIX=/usr/local \
    -DBUILD_SHARED_LIBS=ON \
    -DOQS_BUILD_ONLY_LIB=ON

echo "[install_liboqs] building (this takes 2-5 min)..."
cmake --build "$WORK_DIR/build" --parallel

echo "[install_liboqs] installing (sudo)..."
sudo cmake --install "$WORK_DIR/build"
sudo ldconfig

echo ""
echo "[install_liboqs] DONE. liboqs is installed at /usr/local/lib/."
echo ""
echo "Next: run 'make install-crypto' from the repo root."
