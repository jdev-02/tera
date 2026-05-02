# PRD Review — Read This Before Kickoff

> **Deadline:** Sat 1145 kickoff. Anything you don't push back on by then is locked.
> **Time required:** 10 minutes. Read your assigned sections + the shared sections. Reply in Signal `#wayfinder` thread with `+1` or specific concerns.

The full PRD is **here:** `<gist-url-goes-here-after-jon-runs-gh-gist-create>` (or `docs/PRD.md` after the repo lands).

---

## SHARED — everyone reads (5 min)

These four sections are the spine. Read them; everything else is downstream.

| Section | What to confirm |
|---|---|
| [§1 Hackathon Anchor](PRD.md#1-hackathon-anchor) | We're targeting **PS2 primary, PS3 secondary, PS4 tertiary**. Judging weights are **35% Tech / 30% Impact / 25% Creativity / 10% Pitch** — meaning we over-rotate on demo, under-rotate on slides. **Agree?** |
| [§2 Executive Summary (the hook)](PRD.md#2-executive-summary-the-emotional-hook) | The Marine-recon-team-needs-water hook. Read it once; it gets read verbatim on stage. **Lands? Or revise tone?** |
| [§4 Solution Overview + §6 Demo Construct](PRD.md#4-solution-overview) | **Dual-modality demo: SF Ferry Building → austere AO flip.** *"Same software. Same battery. Different planet."* **Buy-in?** |
| [§13 Team Lane Split](PRD.md#13-team-responsibilities--tech-stack-split) | Directory ownership table. **Your name + lane look right?** |

## JON (P1) — read these too (3 min)

| Section | What to confirm |
|---|---|
| [§7.2 Component table — agent rows](PRD.md#7-technical-architecture) | LLM = Gemma via ollama (Phase 3) + frontier API (Phase 1/2). Tool-calling via JSON schema. Voice via Whisper-tiny. **Stack OK or push back?** |
| [§13.0 Pre-kickoff handoff (your paper to Satriyo)](PRD.md#13-team-responsibilities--tech-stack-split) | **Confirm sent.** |
| §15.2 Palantir AIP as Phase 1 sandbox | **You evaluate by Sat 1500.** Ready to make the call? |
| §16 Open items | **kepler.gl vs Leaflet** — your call at Sat 1400 after first benchmark. |

## SATRIYO (P2) — read these too (3 min)

| Section | What to confirm |
|---|---|
| [§8 Threat Model — featured](PRD.md#8-security-considerations--featured-threat-model) | **Headline threat = TAK track injection.** Mitigation = ML-DSA-65 (Dilithium) signed CoT, optional ML-KEM-768 for encryption. **Endorsable, or do you see a sharper attack we should feature instead?** |
| §8.4 Demo proof points | `tcpdump` on stage, hash-verify printed, audit log scrolling, signature inject demo (stretch). **You own these. Achievable?** |
| §13.0 Jon's parsing-verification paper | **Read before kickoff** if you haven't yet. |
| §14 Codex/AGENTS.md/CI gate | You own the gate. **Anything missing?** |

## KYLE (P3) — read these too (3 min)

| Section | What to confirm |
|---|---|
| [§7.2 Component table — hardware rows](PRD.md#7-technical-architecture) | Jetson Orin Nano 8GB, ollama (CUDA build), faster-whisper, HDMI display, USB-C PD battery. **Hardware on hand matches?** |
| §7.3 Phased ladder + stretch | **Phase 3 hero target = Sun 1000.** Mesh stretch (phone + laptop + Nano) only if Sun 0700 go/no-go = GO. **Realistic with the gear you brought?** |
| §11.2 Perf metrics | < 30s voice→route p50, ≤15W power, < 5ms sign+verify. **Achievable on Orin Nano 8GB? Push back if no.** |
| §12.1 Pitch beats — you're Presenter B (driver) | **Demo runs from 0:20-2:10 of 3 min.** Comfortable? |

## BEN (P4) — read these too (3 min)

| Section | What to confirm |
|---|---|
| [§6 Scenarios + §12.1 Pitch beats](PRD.md#6-user-scenarios--journeys) | **You're Presenter A.** You author the 3 scenarios + score routes from your Mountain Warfare lens. **Hero scenario instinct: A (freshwater) / B (covered foot) / C (vehicle)?** |
| [§7.2 Component table — ATAK + routing rows](PRD.md#7-technical-architecture) | Valhalla + custom DEM cost (slope, ridgeline-prominence, cover). ATAK on Android EUD primary, WinTAK backup. CoT signed via Satriyo's signer. **Stack OK?** |
| §10 Business model + dual-use | SAR / wildland fire / expedition leader as the dual-use channel. **Resonate with your operator network?** |
| §12.2 Q&A prep — you lead | **Pre-rehearsed answers. Skim the table; flag any answer you'd word differently.** |
| §16 Open items | **Austere AO** (Donetsk / Luzon / DMZ / Hindu Kush / Sierra) — your operator gut: which one? |

---

## How to give feedback

**Format your reply as one of:**

- `+1 [name]` — I read my sections, I'm good. Lock it.
- `concern: <section>: <one-sentence concern>` — push back on a specific decision.
- `add: <section>: <missing thing we should include>` — gap in scope.
- `vote: <open item>: <choice>` — answer one of the §16 open items early.

Examples:
- `+1 ben`
- `concern: §11.2: 30s voice-to-route on Orin Nano 8GB might be tight with Gemma 2B. Suggest target ≤45s p50 and bench Sat 1400.`
- `add: §12.2: Q&A should include "what if a route goes through a minefield?" — add a tool-call-rejection answer.`
- `vote: austere AO: Donetsk steppe`

## What we lock at 1145

The §16 open items get a 90-second vote each. Anything in this review with `+1` from all 4 by 1145 is locked. Anything with a `concern:` gets discussed for 60 seconds, then voted.

Don't relitigate after 1145. There are 24 hours after that.

---

# LIVE DECISIONS LOG

> Scribe (Cursor agent) dumps everything below this line, in real time, as the team talks.
> At the end of the discussion, the relevant items get propagated into PRD.md, the kickoff-vote ADR (`docs/adrs/2026-05-02-002-kickoff-vote.md`), and any new ADRs.

## Round-robin sign-off

| Person | Status | Notes |
|---|---|---|
| Jon (P1) | **provisional +1** | Wants Figma reassigned from Ben to him; wants multimodal output (TTS) added |
| Satriyo (P2) | _pending_ | |
| Kyle (P3) | **+1** | Feels good with local-LLM lane focus. **Provisioned Cesium Ion token** (`NPS SF Hackathon`, khicks1724) for global terrain/imagery streaming. |
| Ben (P4) | _pending — affected by Figma reassignment_ | |

## Concerns raised

_none yet_

## Adds requested

- **Jon** §13 lane split: **Figma reassigns from Ben (P4) to Jon (P1)** — Jon owns UI/UX end-to-end. Ben writes scenario scripts; Jon mocks them up. → **ACCEPTED.** Updated PRD §13 ownership table, §13.2 folder layout, scaffold `team.yml`, `CODEOWNERS`, `.agents/21-agent.md`, `.agents/22-atak.md`, `.agents/onboard/jon.md`, `.agents/onboard/ben.md`.
- **Jon** §4 / §6 / §7: **Multimodal output (TTS).** Reading text off ATAK is not viable when an operator is climbing or hands-on with another task. Voice in (Whisper-tiny) AND voice out (Piper TTS) for hands-free turn-by-turn. → **ACCEPTED.** Updated PRD §4 (solution overview + hero claim), §6 (Scenario A now has visual + audio channels), §7.1 (architecture diagram includes TTS layer), §7.2 (Piper added to component table), §11.2 (TTS latency targets added), §16 (TTS engine choice as kickoff vote). Scaffold: `21-agent.md` lane file updated, `voice/` folder layout adds `piper_client.py` + `rationale.py`, new TASK #26 added to TASKS.md and seed-issues.sh, `pyproject.toml` adds `piper-tts` dep, onboard prompt for Jon updated.
- **Kyle** §7.2 / §16: **Cesium Ion token provisioned** (`NPS SF Hackathon`, account khicks1724) for global imagery + 3D terrain streaming. → **ACCEPTED.** Token stored in `/Users/bzadmin/hackathon-scaffold/.env` under `CESIUM_ION_TOKEN` (gitignored, never committed). Updated PRD §7.2 (Cesium row in component table), §16 (resolved + open items mention CesiumJS as the leading Phase 1 viz candidate). Scaffold: `.env` written with token + comments, `.env.example` extended with the slot, `team.yml` records Kyle as resource owner, two new TASKs (#27 CesiumJS frontend for Jon, #28 pre-cache Cesium tiles for Ben) added to TASKS.md + seed-issues.sh, lane files (`21-agent.md`, `22-atak.md`) updated with stack notes. **Constraint:** Cesium is online-only — pre-cache before WiFi off; never called from Phase 3 runtime.

## Votes on §16 open items

<!-- Locked decisions go here AND into ADR-002. -->

| Item | Vote | Result |
|---|---|---|
| Codename | | |
| Austere AO | | |
| Hero scenario | | |
| OSM extract size (SF) | | |
| Palantir AIP yes/no (Jon decides 1500) | | |

## Action items leaving the discussion

- [ ] **Ben** confirms he's good with Figma moving to Jon (silence = consent until 1145). Ben's lane is now `atak/` + `routing/` + `data/` + scenario authoring + operator-cadence consult on TTS rationale + Cesium tile pre-caching.
- [ ] **Jon** picks TTS engine (Piper vs Coqui vs eSpeak) at Sat 1400 — default Piper.
- [ ] **Jon** picks Phase 1 viz (CesiumJS vs kepler.gl vs Leaflet) at Sat 1400 — CesiumJS now leading thanks to Kyle's Ion token.
- [ ] **Jon** + **Ben** pair on TTS rationale phrasing (military number-reading, bearing format) at Sat 1500 checkpoint.
- [ ] **Kyle** adds Piper voice model entry to `models/manifest.sha256` after Jon picks the voice.
- [ ] **Ben** runs `data/scripts/cache_cesium.sh` for both AOIs before WiFi-off testing on Sun 0700.
- [ ] **Satriyo** still pending review — round-robin not complete.
