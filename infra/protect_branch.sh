#!/usr/bin/env bash
# Set branch protection on main. Issue #2.
#
# Requires a GitHub personal access token with repo scope.
# Set GITHUB_TOKEN env var before running:
#
#   export GITHUB_TOKEN="ghp_..."
#   bash infra/protect_branch.sh
#
# Or use gh CLI (preferred when installed):
#   gh api -X PUT "repos/jdev-02/tera/branches/main/protection" \
#     -f required_status_checks='{"strict":true,"contexts":["ci"]}' \
#     -f enforce_admins=true \
#     -f required_pull_request_reviews='{"required_approving_review_count":0}' \
#     -f restrictions=null
#
# Web UI fallback (Settings -> Branches -> Add rule for "main"):
#   ☑ Require pull request before merging
#   ☑ Require status checks to pass  -> select "ci"
#   ☑ Do not allow bypassing above settings
#   ☑ Include administrators

set -euo pipefail

REPO="jdev-02/tera"
BRANCH="main"

if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "ERROR: GITHUB_TOKEN is not set."
    echo ""
    echo "Set it with:"
    echo "  export GITHUB_TOKEN=ghp_..."
    echo "  bash infra/protect_branch.sh"
    exit 1
fi

PAYLOAD='{"required_status_checks":{"strict":true,"contexts":["ci"]},"enforce_admins":true,"required_pull_request_reviews":{"required_approving_review_count":0},"restrictions":null}'

echo "[protect_branch] Setting protection on ${REPO}:${BRANCH}..."

STATUS=$(curl -s -o /tmp/protect_branch_response.json -w "%{http_code}" \
    -X PUT \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${REPO}/branches/${BRANCH}/protection" \
    -d "$PAYLOAD")

if [ "$STATUS" -eq 200 ] || [ "$STATUS" -eq 201 ]; then
    echo "[protect_branch] OK — branch protection enabled on ${REPO}:${BRANCH}"
    echo "[protect_branch] Required checks: ci"
    echo "[protect_branch] Enforce admins: true"
    echo "[protect_branch] Direct push to main: BLOCKED"
else
    echo "[protect_branch] ERROR — HTTP $STATUS"
    cat /tmp/protect_branch_response.json 2>/dev/null || true
    exit 1
fi
