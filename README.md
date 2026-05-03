# TERA — Tactical Edge Route Agent

> **By Team TruePoint** — competing as members of the **[Naval Postgraduate School Foundation](https://npsfoundation.org/) Entrepreneurship Club** · National Security Hackathon 2026 (Cerebral Valley × US Army xTech)
>
> A pocket-sized, fully-offline AI agent that turns natural language into trustworthy tactical routes inside ATAK, on a Jetson Orin Nano, with no cloud and no outbound packets. Voice in, voice and visual out — operators can navigate hands-free while climbing, fast-roping, or running another task.

**TERA / Terra / Terraform / Terrain** — the product's name carries the thesis: an operator with TERA can shape their own path across any terrain, anywhere on earth. The Figma design language leans on earth-tones, contour-line motifs, and terraforming-as-empowerment imagery (Jon owns).

**Hackathon:** 3rd Annual National Security Hackathon · San Francisco · May 2–3, 2026.
**Problem statements:** PS2 (Edge Deployments) · PS3 (Mission C2) · PS4 (Cybersecurity).
**Source of truth:** [`docs/PRD.md`](docs/PRD.md) — read this first.

---

## Read this before writing any code

1. [`AGENTS.md`](AGENTS.md) — agent guardrails. **AI agents must read this every task.**
2. [`docs/PRD.md`](docs/PRD.md) — product, architecture, security, demo plan.
3. [`.agents/00-team.md`](.agents/00-team.md) — stack + style + non-negotiables.
4. [`.agents/10-architecture.md`](.agents/10-architecture.md) — system design summary.
5. [`.agents/2X-<lane>.md`](.agents/) — your lane's specific conventions.
6. [`TASKS.md`](TASKS.md) — seed issues for the GitHub board.

## Quickstart for new teammates

After cloning, **run this and follow the prompts:**

```bash
make onboard
```

It asks who you are (Jon / Satriyo / Kyle / Ben), checks your environment, lists your assigned GitHub issues, and writes a tailored Codex/Cursor kickoff prompt to `/tmp/codex-<name>.md` (also copied to clipboard on macOS). Paste that prompt into your AI agent and start coding.

Non-interactive: `make onboard NAME=ben`.

## Quickstart for development

```bash
git clone https://github.com/jdev-02/tera.git tera && cd tera
make install                # venv + core deps (~2 min)
lefthook install            # pre-push hook (blocking)
cp .env.example .env        # set OPENAI_API_KEY for Phase 1
make run                    # stub service on :8000
make ci                     # the gate (must pass before push)
```

Lane-specific extras:
- **Jon** (voice work): `make install-voice`
- **Satriyo** (crypto work): `brew install liboqs && make install-crypto` (macOS) or `bash infra/install_liboqs.sh && make install-crypto` (Linux/Jetson)

Smoke check from another terminal:

```bash
curl -s -X POST http://localhost:8000/plan \
    -H 'Content-Type: application/json' \
    -d '{"prompt": "route to nearest freshwater within 5km", "current": {"lat": 37.7955, "lon": -122.3937}}' | jq .
```

## Repo layout (PRD §13.2)

```
agent/        # Jon (P1) — orchestrator, /plan endpoint
ontology/     # Jon (P1) — NL term -> OSM tag mapping
voice/        # Jon (P1) — Whisper-tiny (in) + Piper TTS (out)
eval/         # Jon (P1) — 20-prompt regression set
figma/        # Jon (P1) — UI/UX mockups (TERA / terra / terraform palette)
atak/         # Ben (P4) — CoT bridge (Android + WinTAK)
routing/      # Ben (P4) — Valhalla + custom cost
data/         # Ben (P4) — OSM PBF + DEM extracts + Cesium tile cache
hardware/     # Kyle (P3) — Jetson bring-up
deploy/       # Kyle (P3) — systemd, rsync
models/       # Kyle (P3) — Gemma + Whisper + Piper, manifest
mesh/         # Kyle (P3) — stretch (WiFi-Direct / BLE)
security/     # Satriyo (P2) — threat model, parse-verify
crypto/       # Satriyo (P2) — ML-DSA / ML-KEM
infra/        # Satriyo (P2) — Jetson hardening, liboqs install
.github/      # Satriyo (P2) — CI workflows
.agents/      # Satriyo (P2) maintains — agent rules per lane
docs/         # shared — PRD, contracts, ADRs
```

## Team TruePoint

| Member | Lane | Background | Pitch role |
|---|---|---|---|
| **P1 — Jon** (`@jdev-02`) | agent · ontology · voice (in+out) · eval · figma | Navy CWO, CS + AI (ontology), UI/UX | Floor support (AI questions) |
| **P2 — Satriyo** (`@aleens-labs`) | security · crypto · infra · CI | Indonesian Navy, cybersecurity | Floor support (security/PQC) |
| **P3 — Kyle** (`@khicks1724` / `@kylemhicks`) | hardware · deploy · models · mesh | USMC SIGINT, robotics. Brought the Jetson. Provided Cesium Ion token. | Presenter B (drives the demo) |
| **P4 — Ben** (`@benschwierking`) | atak · routing · data | USMC Combat Engineer, Mountain Warfare School | Presenter A (lead narrator) |

Source of truth: [`team.yml`](team.yml). See [`docs/PRD.md`](docs/PRD.md) §13 for the full lane split.

## Phased build

- **P1 — Web MVP** (Sat 1800): laptop + frontier API + CesiumJS (Cesium Ion).
- **P2 — Edge w/ frontier** (Sun 0200): Jetson + frontier API + signed CoT to ATAK.
- **P3 — Fully local HERO** (Sun 1000): Jetson + local Gemma + WiFi off + voice + signed CoT.
- **Stretch — Mesh + PQC reject**: phone + laptop + Nano on a mesh; inject-reject-accept demo.

## Demo

Hero scenario: *"Route me to the nearest freshwater source within 5km, on foot, covered terrain."* Voice prompt → Jetson → ATAK draws a signed blue line **and** Piper TTS speaks the rationale + waypoints in the operator's headset. WiFi off the entire time.

## License

MIT. (Per hackathon rules: open source at submission.)

---

**For everything else, read the PRD.**
