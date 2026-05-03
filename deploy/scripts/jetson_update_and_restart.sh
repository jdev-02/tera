#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/digitaltrident1/Documents/tera_folder/tera}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-main}"
SERVICE_NAME="${SERVICE_NAME:-tera-planner.service}"

cd "$REPO_DIR"

if [[ ! -d .git ]]; then
  echo "[update] not a git repo: $REPO_DIR"
  exit 1
fi

git fetch --quiet "$REMOTE" "$BRANCH"

local_head="$(git rev-parse HEAD)"
remote_head="$(git rev-parse "$REMOTE/$BRANCH")"

if [[ "$local_head" == "$remote_head" ]]; then
  echo "[update] already up to date ($local_head)"
  exit 0
fi

if ! git merge-base --is-ancestor "$local_head" "$remote_head"; then
  echo "[update] local branch diverged; skipping update to avoid overwriting local commits"
  exit 0
fi

git pull --ff-only "$REMOTE" "$BRANCH"
new_head="$(git rev-parse HEAD)"
echo "[update] updated $local_head -> $new_head"

changed_files="$(git diff --name-only "$local_head" "$new_head" || true)"
if grep -Eq '^(llm_dev_kmh/requirements\.txt|requirements-ci\.txt|pyproject\.toml)$' <<<"$changed_files"; then
  echo "[update] dependency files changed, refreshing venv"
  "$REPO_DIR/.venv/bin/python" -m pip install -r "$REPO_DIR/llm_dev_kmh/requirements.txt"
fi

systemctl restart "$SERVICE_NAME"
echo "[update] restarted $SERVICE_NAME"
