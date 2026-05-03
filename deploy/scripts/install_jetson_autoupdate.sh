#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
UPDATE_INTERVAL="${UPDATE_INTERVAL:-1min}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl not found; this installer requires systemd"
  exit 1
fi

if [[ ! -f "$REPO_DIR/deploy/systemd/tera-planner.service" ]]; then
  echo "missing template: $REPO_DIR/deploy/systemd/tera-planner.service"
  exit 1
fi

render() {
  local src="$1"
  sed \
    -e "s|__REPO_DIR__|$REPO_DIR|g" \
    -e "s|__RUN_USER__|$RUN_USER|g" \
    -e "s|__UPDATE_INTERVAL__|$UPDATE_INTERVAL|g" \
    "$src"
}

install -m 0755 "$REPO_DIR/deploy/scripts/run_tera_planner.sh" "$REPO_DIR/deploy/scripts/run_tera_planner.sh"
install -m 0755 "$REPO_DIR/deploy/scripts/jetson_update_and_restart.sh" "$REPO_DIR/deploy/scripts/jetson_update_and_restart.sh"

render "$REPO_DIR/deploy/systemd/tera-planner.service" | sudo tee /etc/systemd/system/tera-planner.service >/dev/null
render "$REPO_DIR/deploy/systemd/tera-planner-update.service" | sudo tee /etc/systemd/system/tera-planner-update.service >/dev/null
render "$REPO_DIR/deploy/systemd/tera-planner-update.timer" | sudo tee /etc/systemd/system/tera-planner-update.timer >/dev/null

sudo systemctl daemon-reload
sudo systemctl enable --now tera-planner.service
sudo systemctl enable --now tera-planner-update.timer

echo "Installed and enabled: tera-planner.service + tera-planner-update.timer"
echo "Run these to inspect:"
echo "  sudo systemctl status tera-planner.service --no-pager -l"
echo "  sudo systemctl status tera-planner-update.timer --no-pager -l"
echo "  journalctl -u tera-planner-update.service -n 50 --no-pager"
