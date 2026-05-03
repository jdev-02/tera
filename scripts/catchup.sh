#!/usr/bin/env bash
# catchup.sh -- "I'm back from a break. What changed? What do I need?"
#
# Run this before resuming work after any sync break (lunch, sleep, demo dry-run).
# It pulls main, refreshes deps if pyproject changed, summarizes commits since
# you last fetched, and lists your lane's open issues.
#
# Output is intentionally agent-friendly: paste it into Codex/Cursor and ask
# "anything I should know before I keep coding?" -- the agent reads the
# summary and the relevant git diffs, then warns you about contract changes,
# new conventions, etc.
#
# Usage:  make catchup    OR    bash scripts/catchup.sh

set -euo pipefail

BOLD=$'\033[1m'; DIM=$'\033[2m'; CYAN=$'\033[36m'; GREEN=$'\033[32m'
YELLOW=$'\033[33m'; RESET=$'\033[0m'
title() { printf "\n${BOLD}${CYAN}== %s ==${RESET}\n" "$*"; }
say()   { printf "%s\n" "$*"; }
warn()  { printf "  ${YELLOW}!${RESET} %s\n" "$*"; }
ok()    { printf "  ${GREEN}+${RESET} %s\n" "$*"; }

if [[ ! -f team.yml ]]; then
    warn "Run from repo root."; exit 1
fi

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "(none)")
title "Catchup -- branch: ${CURRENT_BRANCH}"

# --- 1. Detect uncommitted changes ------------------------------------------
if ! git diff --quiet || ! git diff --cached --quiet; then
    warn "You have uncommitted changes. Stash or commit before catching up:"
    git status --short | sed 's/^/    /'
    say ""
    warn "Suggested:  git stash push -m \"WIP catchup $(date +%H%M)\""
    exit 1
fi

# --- 2. Fetch latest --------------------------------------------------------
title "Fetching origin"
git fetch --all --prune --quiet
ok "fetch complete"

# --- 3. Show divergence -----------------------------------------------------
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    AHEAD=$(git rev-list --count "main..origin/main" 2>/dev/null || echo "?")
    say "  main is ${AHEAD} commits ahead of your last sync"
    say "  (you are on '${CURRENT_BRANCH}', not main -- consider rebasing if you want those commits)"
fi

# --- 4. Pull main if we're on main -----------------------------------------
if [[ "$CURRENT_BRANCH" == "main" ]]; then
    title "Pulling main (fast-forward only)"
    if git merge-base --is-ancestor HEAD origin/main; then
        git pull --ff-only --quiet
        ok "main is up to date"
    else
        warn "Local main has diverged from origin/main. Resolve manually:"
        warn "  git log --oneline --graph --decorate main origin/main"
        exit 1
    fi
fi

# --- 5. Summarize commits since "yesterday" or last reflog --------------
title "Recent commits on origin/main (last 10)"
git log origin/main --oneline --decorate -10 | sed 's/^/  /'

# --- 6. Detect dependency changes ----------------------------------------
title "Dep / config changes since your last fetch"
CHANGED_FILES=$(git log origin/main --since="6 hours ago" --name-only --pretty=format: 2>/dev/null | sort -u | grep -v '^$' || echo "")

DEP_CHANGE=0
if echo "$CHANGED_FILES" | grep -qE '(^pyproject\.toml$|^Makefile$|^lefthook\.yml$|^\.github/)'; then
    warn "build/CI config changed in last 6h. Refreshing deps:"
    if [[ -d .venv ]]; then
        .venv/bin/pip install -e ".[dev]" -q 2>&1 | tail -3 || warn "pip install failed; you may need to investigate"
        ok ".venv refreshed"
    else
        warn ".venv missing -- run: make install"
    fi
    DEP_CHANGE=1
fi

# --- 7. Detect contract changes ----------------------------------------
if echo "$CHANGED_FILES" | grep -qE '^docs/contracts/'; then
    warn "CONTRACT CHANGED -- read carefully before continuing:"
    echo "$CHANGED_FILES" | grep -E '^docs/contracts/' | sed 's/^/      /'
    warn "If you are mid-task on something that touches a changed contract,"
    warn "STOP and re-read the contract before more code. Tell your agent."
fi

# --- 8. Detect agent rule changes -------------------------------------
if echo "$CHANGED_FILES" | grep -qE '^(AGENTS\.md|\.agents/)'; then
    warn "agent rules changed -- your AI agent should re-read AGENTS.md and your lane file"
    echo "$CHANGED_FILES" | grep -E '^(AGENTS\.md|\.agents/)' | sed 's/^/      /'
fi

# --- 9. Show your open issues ----------------------------------------
# Bug fix (issue from 17:50 catchup output): the previous version queried
# `gh issue list --label "lane:a,lane:b,lane:c"` which means AND, not OR --
# returns ~0 issues for anyone whose lanes don't all overlap on a single
# ticket. The right question is 'what is assigned to ME', so query
# --assignee @me. If that's empty, fall back to lane-tagged issues using
# Python set-intersection (true OR semantics).
title "Your open issues"
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
    PY="${PY_CMD:-python3}"

    # Pass 1: issues directly assigned to the current user.
    ASSIGNED_JSON=$(gh issue list --assignee @me --state open \
        --json number,title,labels --limit 30 2>/dev/null || echo "[]")

    # Pass 2: issues tagged with this teammate's lane labels (OR semantics).
    # Only used as a fallback display when assigned is empty, OR appended
    # when there are unassigned lane issues that might be next-up pickups.
    NAME=""
    if [[ -f .git/tera-name || -f .git/wayfinder-name ]]; then
        NAME=$(cat .git/tera-name 2>/dev/null || cat .git/wayfinder-name 2>/dev/null)
    fi
    if [[ -z "$NAME" ]]; then
        FN=$(git config user.name 2>/dev/null | awk '{print tolower($1)}' || echo "")
        case "$FN" in
            jon|satriyo|kyle|ben) NAME="$FN" ;;
        esac
    fi
    LANES_JSON="[]"
    case "$NAME" in
        jon)     LANES='["lane:agent","lane:ontology","lane:voice","lane:eval"]' ;;
        satriyo) LANES='["lane:security","lane:crypto","lane:infra","lane:ci"]' ;;
        kyle)    LANES='["lane:hardware","lane:deploy","lane:models","lane:mesh"]' ;;
        ben)     LANES='["lane:atak","lane:routing","lane:data"]' ;;
        *)       LANES='[]' ;;
    esac
    if [[ "$LANES" != "[]" ]]; then
        # Fetch all open issues once; filter in Python for OR semantics.
        LANES_JSON=$(gh issue list --state open \
            --json number,title,labels,assignees --limit 100 2>/dev/null || echo "[]")
    fi

    ASSIGNED_JSON="$ASSIGNED_JSON" LANES_JSON="$LANES_JSON" LANES="$LANES" \
        "$PY" -c "
import json, os
def fmt(i):
    labels = [l['name'] for l in i.get('labels', [])]
    pri = next((l for l in labels if l.startswith('priority:')), 'priority:?')
    return f\"  #{i['number']:>3}  [{pri:<12}] {i['title']}\"

assigned = json.loads(os.environ.get('ASSIGNED_JSON') or '[]')
lanes_all = json.loads(os.environ.get('LANES_JSON') or '[]')
lane_set = set(json.loads(os.environ.get('LANES') or '[]'))

if assigned:
    print('Assigned to you:')
    for i in assigned:
        print(fmt(i))
else:
    print('  (nothing currently assigned to you)')

if lane_set:
    assigned_nums = {i['number'] for i in assigned}
    pickups = []
    for i in lanes_all:
        nums_match = any((l['name'] in lane_set) for l in i.get('labels', []))
        if not nums_match:
            continue
        if i['number'] in assigned_nums:
            continue
        if i.get('assignees'):
            continue
        pickups.append(i)
    if pickups:
        print('')
        print('Unassigned in your lane(s) -- candidates to pick up:')
        for i in pickups[:10]:
            print(fmt(i))
" || warn "couldn't fetch issues"
else
    warn "gh not authed; skipping issue summary"
fi

# --- 10. Final note ------------------------------------------------------
title "Done"
say "Suggested next step (paste into Codex/Cursor):"
say ""
say "${DIM}\"I just ran make catchup. main moved forward. Tell me anything I should${RESET}"
say "${DIM}know before resuming work on my current branch -- contract changes,${RESET}"
say "${DIM}agent rule changes, or convention drift. Then suggest the next issue.\"${RESET}"
say ""
[[ $DEP_CHANGE -eq 1 ]] && say "(deps were refreshed -- restart any running 'make run' processes)"
exit 0
