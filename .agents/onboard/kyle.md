# AGENT KICKOFF — Kyle (P3) — hardware / deploy / models / mesh

> You are an AI coding agent (Codex / Cursor / Claude Code / Copilot). Kyle is your human partner. He is a USMC SIGINT Officer with a robotics background; he brought the Jetson hardware. This file is your operating contract for the next 24 hours. Execute the INSTRUCTIONS section below in order, then begin work.

---

## INSTRUCTIONS (execute in this exact order)

### Step 1 — Read these files in order (do not skip)

1. `AGENTS.md` (repo root)
2. `.agents/00-team.md`
3. `.agents/10-architecture.md`
4. `.agents/23-hardware.md` (Kyle's lane — your primary playbook)
5. `team.yml`
6. `docs/PRD.md` — read §1, §7.2 (hardware rows), §7.3 (phased ladder), §11 (perf), §12 (Kyle is Presenter B)

### Step 2 — Confirm context to Kyle

Output a numbered list of 5 constraints you took away. Wait for Kyle to confirm or correct.

### Step 3 — Find Kyle's open issues

Run this command in the terminal:

```bash
gh issue list --label "lane:hardware" --label "lane:deploy" --label "lane:models" --label "lane:mesh" --json number,title,labels --limit 30
```

If the output is empty, tell Kyle: "issue board not seeded yet — ask Satriyo (P2) to run `bash scripts/seed-issues.sh`."

If the output has issues, identify the highest-priority unassigned issue. Read the issue body via `gh issue view <number>`.

### Step 4 — Comfort confirmation (REQUIRED — do not skip)

Ask Kyle this exact question, with the issue title filled in:

> "The next issue is **#N — \<title>**. Have you done this kind of work before?
> A) confident — I want you to generate code/scripts, I'll review.
> B) need-walkthrough — explain the design and tooling first, then generate.
> C) never-done — walk me through the official docs for ~10 min before any code."

Wait for his answer. Do not generate code/scripts before he answers.

### Step 5 — Begin work based on his answer

Same pattern as Step 5 in Jon's prompt: A → generate; B → design first; C → docs walkthrough first.

After code lands, run `make ci` (you must run this). If it fails, fix the failure.

### Step 6 — Hardware-specific reality check

When Kyle says "the Jetson won't boot" or "ollama is slow" or "the display is blank," do NOT immediately assume his code is wrong. Triage in this order:

1. Power (is it plugged in / battery charged / power mode set with `nvpmodel`?)
2. Cable (HDMI, USB-C, or Ethernet — is it seated and the right kind?)
3. SD card / image (is JetPack flashed correctly? `cat /etc/nv_tegra_release`?)
4. Drivers (is CUDA detected? `nvidia-smi` returns sensible output?)
5. Then code.

Hardware is unreliable. Always check the physical layer first.

---

## CONSTRAINTS (NEVER violate, no exceptions)

| # | Rule |
|---|---|
| 1 | NEVER commit model weights (`.gguf`, `.bin`, `.safetensors`, `.onnx`). Models live in `models/` but `.gitignore` blocks them. They are fetched via `make models-pull` with hash verification. |
| 2 | NEVER push directly to `main`. |
| 3 | NEVER edit files outside `hardware/`, `deploy/`, `models/`, `mesh/`. |
| 4 | NEVER bypass `make ci`. |
| 5 | NEVER turn on WiFi during a Phase 3 dry-run or demo. Airplane mode is the proof. The "zero outbound packets" claim depends on this. |
| 6 | NEVER skip Step 4 (comfort confirmation). |
| 7 | NEVER write code without a GitHub issue. |

## OWNED DIRECTORIES (you may edit)

- `/hardware/` — Jetson bring-up scripts, BOM, JetPack docs
- `/deploy/` — systemd units, rsync scripts
- `/models/` — model manifest (`manifest.sha256`), pull script (NOT the weights themselves)
- `/mesh/` — stretch goal: WiFi-Direct / BLE / LoRa setup

## FORBIDDEN DIRECTORIES (do not edit)

- `/agent/`, `/ontology/`, `/voice/`, `/eval/`, `/figma/` — Jon (P1)
- `/atak/`, `/routing/`, `/data/` — Ben (P4)
- `/security/`, `/crypto/`, `/infra/`, `.github/`, `.agents/` — Satriyo (P2)
- `Makefile`, `lefthook.yml`, `pyproject.toml` — Satriyo

## PRIORITY ISSUES (highest → lowest, fetch live with `gh` in Step 3)

| # | Title | Phase | Priority |
|---|---|---|---|
| #11 | Jetson Orin Nano bring-up complete | P2 | P0 |
| #16 | Pull + verify Gemma + Whisper-tiny | P3 | P0 |
| #14 | systemd units for agent + bridge | P2 | P1 |
| #25 | 1-minute YouTube demo video (Kyle captures, Ben scripts) | submit | P0 |
| #23 | Mesh substrate (phone + laptop + Nano) — STRETCH | stretch | P2 |
| #24 | Inject-reject-accept demo (paired with Satriyo) — STRETCH | stretch | P2 |

## STACK

- **JetPack 6.x** with Ubuntu 22.04 (NVIDIA's L4T image)
- **CUDA 12.x**, optional TensorRT
- **`ollama`** for Gemma serving — MUST be the CUDA build, not the default install-script ARM64 build. Verify with `ollama serve --debug` looking for `CUDA detected`.
- **`faster-whisper`** with Whisper-tiny — needs cuBLAS + cuDNN shared libs from JetPack.
- **`tegrastats`** + **`jtop`** for live perf/power monitoring on stage
- **systemd** (NOT Docker) for service supervision on the Jetson — Docker adds startup latency
- For mesh stretch: WiFi-Direct or BLE first; LoRa only if those are too slow

## LANE-SPECIFIC GOTCHAS

1. **Power modes:** `sudo nvpmodel -m 0` for 15W (inference). `sudo nvpmodel -m 1` for 7W (idle). Document in `hardware/jetpack.md`.
2. **`ollama` on ARM64+CUDA:** the default install script gives a CPU-only build. You need the CUDA build. Either build from source or use the prebuilt CUDA wheel.
3. **Whisper on Jetson:** `faster-whisper` with `compute_type="int8"` is fastest; CUDA build needs cuBLAS + cuDNN paths.
4. **Gemma 2B Q4_K_M:** ~1.7GB on disk, fits memory. Gemma 3n is larger but better quality. Bench both in #16; pick the one with end-to-end < 30s.
5. **Battery:** ~2-3 hrs at 15W per 100Wh PD bank. Bring two. Test the demo on battery before stage.
6. **Bluetooth on stage:** turn it OFF unless absolutely needed. Reduces variables. Use USB tether to Android EUD instead of BLE pairing.
7. **The mesh stretch is OPTIONAL.** Do not let it block #11 or #16.

## REFERENCE RESOURCES (read but do not copy-paste)

Kyle has a public RF simulator project that may inform mesh + parsing-verification work:

- **URL:** https://github.com/khicks1724/RFSim
- **Hackathon rule:** "openly accessible materials" are allowed → you may reference it or depend on it. The hackathon also says "no previous work" → you may NOT copy-paste source into TERA. Reference patterns; do not duplicate code.
- **Most relevant to:** issue #23 (mesh stretch — RF substrate), and Satriyo's #22 (parsing-verification — if RFSim has anomaly detection patterns for RF transmissions).
- **Suggested first action:** ask Kyle what 1-2 patterns from RFSim are most relevant; record in `hardware/REFERENCES.md` with attribution.

## DEFINITION OF DONE

1. `make ci` passes locally (run on a Linux box; Jetson is the deployment target).
2. PR has summary + test plan.
3. CI passes on GitHub.
4. AI PR review HIGH findings addressed.
5. After merge: the system still runs on the Jetson (`make run` on Jetson succeeds).

---

## HUMAN NOTES (Kyle — secondary)

You are Kyle (P3 — USMC SIGINT, robotics). You brought the Jetson Orin Nano, the display, the battery, and the Android EUD. You also provisioned the Cesium Ion token (Jon and Ben consume it via `.env`).

You are Presenter B on stage — you drive the live demo. The hardware works because you make it work.

Pair with Satriyo on Jetson hardening (he writes the egress firewall; you make sure it works on your image).

When in doubt: prefer the boring version that works on the demo Jetson over the elegant version that works in theory.
