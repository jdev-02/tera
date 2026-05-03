#!/usr/bin/env bash
# Set branch protection on main. Issue #2.
#
# Requires either:
#   1. GITHUB_TOKEN env var with repo administration permission, or
#   2. an authenticated gh CLI session (`gh auth login`).
#
# Env-var path:
#
#   export GITHUB_TOKEN="<token-with-repo-admin-permission>"
#   bash infra/protect_branch.sh
#
# gh path:
#
#   gh auth login
#   bash infra/protect_branch.sh
#
# Web UI fallback (Settings -> Branches -> Add rule for "main"):
#   - Require pull request before merging
#   - Require status checks to pass -> select "ci"
#   - Do not allow bypassing above settings
#   - Include administrators

set -euo pipefail

REPO="jdev-02/tera"
BRANCH="main"

TOKEN="${GITHUB_TOKEN:-}"

if [ -z "$TOKEN" ] && command -v gh >/dev/null 2>&1; then
    echo "[protect_branch] GITHUB_TOKEN not set; trying gh auth token..."
    TOKEN="$(gh auth token 2>/dev/null || true)"
fi

if [ -z "$TOKEN" ]; then
    echo "ERROR: No GitHub token available."
    echo ""
    echo "Option 1:"
    echo "  export GITHUB_TOKEN=<token-with-repo-admin-permission>"
    echo "  bash infra/protect_branch.sh"
    echo ""
    echo "Option 2:"
    echo "  gh auth login"
    echo "  bash infra/protect_branch.sh"
    exit 1
fi

PAYLOAD='{"required_status_checks":{"strict":true,"contexts":["ci"]},"enforce_admins":true,"required_pull_request_reviews":{"required_approving_review_count":0},"restrictions":null}'

echo "[protect_branch] Setting protection on ${REPO}:${BRANCH}..."

RESPONSE_FILE="${TMPDIR:-/tmp}/protect_branch_response.json"

STATUS=$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" \
    -X PUT \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${REPO}/branches/${BRANCH}/protection" \
    -d "$PAYLOAD")

if [ "$STATUS" -eq 200 ] || [ "$STATUS" -eq 201 ]; then
    echo "[protect_branch] OK - branch protection enabled on ${REPO}:${BRANCH}"
    echo "[protect_branch] Required checks: ci"
    echo "[protect_branch] Enforce admins: true"
    echo "[protect_branch] Direct push to main: BLOCKED"
else
    echo "[protect_branch] ERROR - HTTP $STATUS"
    cat "$RESPONSE_FILE" 2>/dev/null || true
    exit 1
fi
