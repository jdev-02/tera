# KICKOFF.md - Historical Hackathon Runbook

> This file is preserved as an internal kickoff record from the first build day.
> It is not the current product description, demo contract, or setup guide.
> Use [`README.md`](README.md), [`AGENTS.md`](AGENTS.md), and [`docs/PRD.md`](docs/PRD.md) for current project truth.

---

## Pre-walk-over (now → 0900)

- [ ] Confirm Codex workspace invites for Jon, Satriyo, Kyle, Ben. Form filled — waiting on Cerebral Valley to provision.
- [ ] If Codex doesn't land in time: AGENTS.md is tool-agnostic. Cursor / Claude Code / Copilot all work. Tell teammates at the venue.
- [ ] Confirm Danti account requests for all 4.
- [ ] Hand Satriyo the parsing-verification paper (Signal'd).
- [ ] Pack: laptop charger, Jetson rig (Kyle owns), Android EUD (Kyle owns), WinTAK laptop (Kyle's backup), HDMI/USB-C cables.
- [ ] Bring this scaffold on a USB stick or in iCloud — backup if home network fails at venue.

---

## At the venue (0900-1100)

Use this time:
- Get all 4 onto Codex if invites arrive (Palantir folks help).
- Get all 4 onto Danti.
- Find a table near power. Avoid the door.
- Eat. Not eating again until 1300.

---

## 1100 — welcome session

Take notes on:
- Mentors whose backgrounds match PS2 / PS4. Pull them aside later.
- Palantir AIP onsite contacts.
- Any rule clarifications (especially around scaffolding/AGENTS.md as "tooling not work").

---

## 1145 — HACKING STARTS — execute in order

### Phase A: 1145-1155 (10 min) — kickoff vote, no laptops

Read aloud: *"24 hours. PRD locks 95% of decisions. We vote on 5 things in 90 sec each. Then we never relitigate."*

| # | Item | Default | Alternatives |
|---|---|---|---|
| 1 | Codename | WAYFINDER | LODESTAR, PATHFNDR, BLACKMAP, COMPASS ROSE |
| 2 | Austere AO | Donetsk steppe | N. Luzon, Korean DMZ, Hindu Kush, Sierra Nevada proxy |
| 3 | Hero scenario | A: freshwater | B: covered foot, C: vehicle |
| 4 | OSM extract size | County (SF) | State, city-only |
| 5 | Palantir AIP | Yes (Phase 1 only) | No |

Defer: ollama vs llama.cpp (Kyle picks at 1400 post-bench); Danti yes/no (Ben picks Sat afternoon); kepler.gl vs Leaflet (Jon picks at 1400).

Photograph the votes on paper. Post to team Signal. Done.

### Phase B: 1155-1215 (20 min) — Jon spawns the repo

You execute these. **No one else codes yet.**

```bash
cd ~/hackathon-scaffold

# 1. team.yml + CODEOWNERS already have real handles wired in pre-kickoff:
#      @jdev-02       Jon
#      @aleens-labs   Satriyo
#      @khicks1724 + @kylemhicks  Kyle (dual: laptop/Codex + Jetson)
#      @benschwierking  Ben
# Just verify before pushing:
grep -c "TODO_" CODEOWNERS    # should print 0

# 3. Create the public repo under Jon's account (codename: TruePoint — locked pre-kickoff)
gh repo create jdev-02/truepoint --public --source=. --remote=origin --description="National Security Hackathon 2026 — TruePoint: Tactical Edge Route Agent (offline AI route planning for ATAK)"

# 4. First commit (do NOT commit KICKOFF.md — add to .gitignore first)
echo "KICKOFF.md" >> .gitignore
git init
git add -A
git commit -m "chore: initial scaffold with AGENTS.md, PRD, contracts, CI, onboarding"
git branch -M main
git push -u origin main

# 5. Branch protection (empty bypass list)
gh api -X PUT "repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/branches/main/protection" \
  -f required_status_checks='{"strict":true,"contexts":["ci"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":0}' \
  -f restrictions=null 2>&1 || echo "branch protection: configure via UI if API failed"

# 6. Add teammates as collaborators (Kyle gets both his handles)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
for h in aleens-labs khicks1724 kylemhicks benschwierking; do
  gh api -X PUT "repos/$REPO/collaborators/$h" -F permission=push
done

# 7. Seed the issue board
bash scripts/seed-issues.sh

# 8. Verify CI ran
gh run list --limit 1
```

### Phase C: 1215-1230 (15 min) — onboard the team

Gather everyone. **Show, don't email.**

Read aloud: *"Repo: <URL>. Clone now. Then `make onboard`. It asks who you are, checks your env, pulls your issues, and writes a Codex prompt to `/tmp/codex-<name>.md`. Paste that prompt into your agent. The agent reads AGENTS.md, your lane file, and starts pair-coding you through your first issue."*

Each teammate runs (in parallel — they don't block each other):

```bash
git clone <repo-url> <codename> && cd <codename>
make install        # venv + deps (~2 min)
lefthook install    # pre-push hook
cp .env.example .env  # set OPENAI_API_KEY (Codex provides this)
make onboard        # interactive: who are you?
```

The script:
1. Asks: jon / satriyo / kyle / ben.
2. Checks: python3.11, gh authed, lefthook present, .venv, .env.
3. Pulls their issues from GitHub by lane labels.
4. Writes their tailored prompt at `/tmp/codex-<name>.md` and copies to clipboard.
5. Prints next steps.

The teammate then:
1. Opens Codex (or Cursor / Claude Code).
2. Pastes the prompt.
3. Agent confirms it understood the constraints.
4. Agent suggests the highest-priority issue.
5. Agent asks: "comfort? confident / need-walkthrough / never-done?"
6. Pair-coding begins.

### Phase D: 1230-1500 — heads-down parallel work

Per PRD §13.1.

| Lane | Owner | First issues |
|---|---|---|
| Phase 1 web MVP | **Jon** | #4 → #5 → #10 |
| Jetson bring-up + models | **Kyle** | #11 → #16 |
| Data + Valhalla | **Ben** | #8 → #7 |
| Branch protection + ML-DSA | **Satriyo** | #2 → #3 → #12 |

---

## Smoke-test cadence (PRD §13.4)

Phone alarm every 30 min: run `make run` in your lane, ping your endpoint. If a lane is silent 90+ min, integrator pings.

By **Sun 0500**, `make demo` runs the full hero scenario E2E. After that, anything that breaks `make demo` is reverted.

---

## Sync cadence

| Time | What | Min |
|---|---|---|
| Sat 1500 | Contract freeze; Jon demos web MVP | 10 |
| Sat 1900 | Dinner sync; Kyle demos Jetson + frontier | 15 |
| Sun 0700 | Go/no-go on Phase 3 + mesh stretch | 10 |
| Sun 1000 | Demo lockdown; pitch rehearsal #1 | — |
| Sun 1130 | Submission packaging | — |
| Sun 1340 | Pre-flight (PRD §12.4) | — |

---

## If something breaks

- **CI red** → `git revert HEAD && git push`. Don't fix forward.
- **Someone pushed to main** → branch protection should have blocked. If not, fix it FIRST.
- **Jetson fights Kyle** → Kyle + Ben pair on it. Jon + Satriyo keep building independently.
- **Two people on same file** → CODEOWNERS catches at PR. Lane owner wins; other rebases.
- **Demo path breaks at 0500** → revert. Don't ship a broken hero.
- **Codex unavailable for someone** → Cursor / Claude Code / Copilot. AGENTS.md is tool-agnostic.

---

## Post-kickoff cleanup

After the team is parallel-coding (1230+), delete this file or move it to `~/notes/` so it stays out of the public repo.
