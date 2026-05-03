#!/usr/bin/env bash
# Run this on the Jetson to pull the newest code and restart the web app.
# Usage: ./jetson-update.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

echo "=== TERA Jetson Update ==="
echo "Pulling latest from origin/main..."
git fetch origin main
git rebase origin/main
echo "Up to date: $(git rev-parse --short HEAD)"

echo ""
echo "Rebuilding and restarting planner..."
docker compose -f docker-compose.yml down --remove-orphans
docker compose -f docker-compose.yml up -d --build --pull always

echo ""
echo "Container status:"
docker compose -f docker-compose.yml ps

echo ""
echo "Waiting for app to be ready..."
sleep 3
for i in $(seq 1 20); do
  if curl -sf http://127.0.0.1:8080/api/config >/dev/null 2>&1; then
    echo "App is ready!"
    echo ""
    echo "=== Access from Windows ==="
    echo "http://$(hostname -I | awk '{print $1}'):8080"
    echo ""
    echo "=== TERA ATAK Agent mode ==="
    echo "Click the [ATAK Local] button in the top bar to activate TERA agent mode."
    exit 0
  fi
  sleep 1
done

echo "App did not respond in time. Check logs:"
echo "  docker compose -f docker-compose.yml logs --tail=80"
exit 1
