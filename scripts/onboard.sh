#!/usr/bin/env bash
# onboard.sh -- "I am Ben, get me ready to party."
#
# Usage:
#   bash scripts/onboard.sh                    # interactive
#   bash scripts/onboard.sh ben                # non-interactive
#   make onboard NAME=ben                      # via make
#
# Output: prints next-step instructions and writes a Codex/Cursor kickoff prompt
#         to /tmp/codex-<name>.md that the teammate pastes into their AI agent.

set -euo pipefail

NAME="${1:-${NAME:-}}"

# --- Fancy output (no deps) -------------------------------------------------
BOLD=$'\033[1m'; DIM=$'\033[2m'; CYAN=$'\033[36m'; GREEN=$'\033[32m'
YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
say()   { printf "%s\n" "$*"; }
title() { printf "\n${BOLD}${CYAN}== %s ==${RESET}\n" "$*"; }
ok()    { printf "  ${GREEN}[ok]${RESET}   %s\n" "$*"; }
warn()  { printf "  ${YELLOW}[!!]${RESET}   %s\n" "$*"; }
err()   { printf "  ${RED}[xx]${RESET}   %s\n" "$*" >&2; }
ask()   { printf "${BOLD}%s${RESET} " "$*"; }

# --- Sanity ------------------------------------------------------------------
title "TERA onboarding"
say "${DIM}reads team.yml; finds your lane; prints next steps + Codex prompt.${RESET}"

if [[ ! -f team.yml ]]; then
    err "team.yml not found. Run from the repo root."
    exit 1
fi
if [[ ! -f AGENTS.md ]]; then
    err "AGENTS.md not found. Run from the repo root."
    exit 1
fi

# --- Pick name --------------------------------------------------------------
if [[ -z "$NAME" ]]; then
    say ""
    say "Who are you?"
    say "  ${BOLD}1${RESET}) Jon     (P1 -- agent / ontology / voice / eval)"
    say "  ${BOLD}2${RESET}) Satriyo (P2 -- security / crypto / infra / CI)"
    say "  ${BOLD}3${RESET}) Kyle    (P3 -- hardware / deploy / models / mesh)"
    say "  ${BOLD}4${RESET}) Ben     (P4 -- atak / routing / data / figma)"
    ask "[1-4 or name]:"
    read -r ANSWER
    case "$ANSWER" in
        1|jon|Jon|JON)              NAME="jon" ;;
        2|satriyo|Satriyo|SATRIYO)  NAME="satriyo" ;;
        3|kyle|Kyle|KYLE)           NAME="kyle" ;;
        4|ben|Ben|BEN)              NAME="ben" ;;
        *) err "unknown: '$ANSWER'"; exit 1 ;;
    esac
fi

NAME="$(echo "$NAME" | tr '[:upper:]' '[:lower:]')"
case "$NAME" in
    jon|satriyo|kyle|ben) ;;
    *) err "unknown name: '$NAME' (must be jon, satriyo, kyle, or ben)"; exit 1 ;;
esac

# --- Per-person facts -------------------------------------------------------
case "$NAME" in
    jon)
        FULL="Jon"; ROLE="P1"
        LANE="agent / ontology / voice / eval"
        DIRS="agent ontology voice eval"
        BACKGROUND="Navy Cyber Warfare Officer; CS + AI (ontology); UI/UX"
        LABELS="lane:agent,lane:ontology,lane:voice,lane:eval"
        PAIR="Ben (on agent <-> routing contract)"
        ;;
    satriyo)
        FULL="Satriyo"; ROLE="P2"
        LANE="security / crypto / infra / CI"
        DIRS="security crypto infra .github .agents"
        BACKGROUND="Indonesian Navy; cybersecurity"
        LABELS="lane:security,lane:crypto,lane:infra,lane:ci"
        PAIR="Ben (on signer integration into CoT bridge), Kyle (on Jetson hardening)"
        ;;
    kyle)
        FULL="Kyle"; ROLE="P3"
        LANE="hardware / deploy / models / mesh"
        DIRS="hardware deploy models mesh"
        BACKGROUND="USMC SIGINT Officer; robotics background; brought the Jetson"
        LABELS="lane:hardware,lane:deploy,lane:models,lane:mesh"
        PAIR="Satriyo (on Jetson hardening)"
        ;;
    ben)
        FULL="Ben"; ROLE="P4"
        LANE="atak / routing / data / figma"
        DIRS="atak routing data figma"
        BACKGROUND="USMC Combat Engineer; CS student; Marine Corps Mountain Warfare School"
        LABELS="lane:atak,lane:routing,lane:data"
        PAIR="Jon (on agent <-> routing contract), Satriyo (on signer integration)"
        ;;
esac

# --- Greet ------------------------------------------------------------------
title "Hi $FULL ($ROLE -- $LANE)"
say "Background on file: ${DIM}$BACKGROUND${RESET}"
say "Pair partners: ${DIM}$PAIR${RESET}"

# --- Environment check ------------------------------------------------------
title "Environment check"
PYOK=1; GHOK=1; HOOKOK=1

# Find a Python 3.11 binary (try several common names)
PY_CMD=""
for cand in python3.11 python3 python; do
    if command -v "$cand" >/dev/null && "$cand" -c 'import sys; sys.exit(0 if sys.version_info[:2]==(3,11) else 1)' 2>/dev/null; then
        PY_CMD="$cand"; break
    fi
done
if [[ -n "$PY_CMD" ]]; then ok "Python 3.11 found ($PY_CMD)"; else warn "Python 3.11 not found (try: brew install python@3.11)"; PYOK=0; fi

if command -v gh >/dev/null; then
    if gh auth status >/dev/null 2>&1; then ok "gh authed"
    else warn "gh installed but not authed (run: gh auth login)"; GHOK=0
    fi
else
    warn "gh not installed (brew install gh, then: gh auth login)"; GHOK=0
fi

if command -v lefthook >/dev/null; then
    if [[ -f .git/hooks/pre-push ]]; then ok "lefthook installed (pre-push hook present)"
    else warn "lefthook found but hooks not installed in this repo (run: lefthook install)"; HOOKOK=0
    fi
else
    warn "lefthook not installed (brew install lefthook && lefthook install)"; HOOKOK=0
fi

VENV_OK=1
if [[ -d .venv ]]; then
    if [[ -f .venv/bin/uvicorn ]]; then ok ".venv exists and looks healthy"
    else warn ".venv exists but seems incomplete (run: make install)"; VENV_OK=0
    fi
else
    warn ".venv missing. RUN THIS NOW: make install"
    VENV_OK=0
fi

if [[ -f .env ]]; then ok ".env exists"; else warn ".env missing. RUN THIS NOW: cp .env.example .env"; fi

# Lane-specific install hint
case "$NAME" in
    satriyo)
        if [[ -f .venv/bin/python ]] && .venv/bin/python -c "import oqs" 2>/dev/null; then
            ok "liboqs-python installed (you can run sign-bench)"
        else
            warn "liboqs-python NOT installed yet. When you start issue #12 (signer), RUN THESE:"
            warn "    1) brew install liboqs    (macOS)   OR   bash infra/install_liboqs.sh   (Linux)"
            warn "    2) make install-crypto"
            warn "(You do NOT need this for issues #2 or #3. Start with those.)"
        fi
        ;;
    jon)
        if [[ -f .venv/bin/python ]] && .venv/bin/python -c "import faster_whisper" 2>/dev/null; then
            ok "voice deps installed"
        else
            warn "voice deps NOT installed yet. When you start voice work (issues #18, #26), RUN: make install-voice"
        fi
        ;;
esac

# --- Pull issues ------------------------------------------------------------
title "Your assigned issues"
if [[ $GHOK -eq 1 ]]; then
    ISSUES=$(gh issue list --label "$LABELS" --json number,title,labels --limit 30 2>/dev/null | "${PY_CMD:-python3}" -c "
import json, sys
data = json.load(sys.stdin)
for i in data:
    labels = [l['name'] for l in i['labels']]
    pri = next((l for l in labels if l.startswith('priority:')), 'priority:?')
    phase = next((l for l in labels if l.startswith('phase:')), '')
    print(f\"  #{i['number']}  [{pri}] {phase}  {i['title']}\")
" 2>/dev/null || echo "")
    if [[ -n "$ISSUES" ]]; then
        echo "$ISSUES"
    else
        warn "no issues found with labels for your lane"
        warn "run 'bash scripts/seed-issues.sh' first (Jon / Satriyo do this once at kickoff)"
    fi
else
    warn "skipping issue pull (gh not authed)"
fi

# --- Generate Codex prompt --------------------------------------------------
PROMPT="/tmp/codex-${NAME}.md"
title "Generating your Codex / Cursor / Claude Code kickoff prompt"

cp ".agents/onboard/${NAME}.md" "$PROMPT"
ok "wrote $PROMPT"

# --- Next steps -------------------------------------------------------------
title "Next steps"
say "  ${BOLD}1.${RESET} If you haven't yet: ${CYAN}make install${RESET}  (creates venv, installs deps; ~2 min)"
say "  ${BOLD}2.${RESET} If you haven't yet: ${CYAN}lefthook install${RESET}  (installs the pre-push hook)"
say "  ${BOLD}3.${RESET} Open your AI coding agent (Codex / Cursor / Claude Code)."
say "  ${BOLD}4.${RESET} Paste the contents of ${BOLD}$PROMPT${RESET} into the agent's first message."
say "  ${BOLD}5.${RESET} The agent will ask you about comfort + suggest the first issue to grab."
say "  ${BOLD}6.${RESET} Pick an issue, branch as ${CYAN}${NAME}/<short-desc>${RESET}, code, ${CYAN}make ci${RESET}, push, PR."
say ""
say "${DIM}WIP cap: 2 issues 'Doing' at any time. Smoke-test cadence: every 30 min, ${CYAN}make run${RESET}.${RESET}"
say ""

# Try to copy to clipboard on macOS (best effort; harmless if no GUI clipboard)
if command -v pbcopy >/dev/null; then
    if pbcopy < "$PROMPT" 2>/dev/null; then
        ok "prompt copied to clipboard (paste with Cmd+V)"
    fi
fi

title "Go build."
say ""
exit 0
