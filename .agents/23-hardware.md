# 23 — Hardware / Deploy / Models / Mesh Lane (P3 — Kyle, USMC SIGINT, robotics)

> Owns: `/hardware/`, `/deploy/`, `/models/`, `/mesh/`. Pairs with P2 on Jetson hardening.

## What this lane delivers

1. **Jetson Orin Nano bring-up** — JetPack image, CUDA, Python 3.11, our deps.
2. **Model deployment** — Gemma + Whisper-tiny quantized, benchmarked, served via `ollama` and `faster-whisper`.
3. **Display + power rig** — HDMI panel, USB-C PD battery, demo-ready hardware.
4. **Mesh substrate (stretch)** — phone + laptop + Nano on a mesh for the inject-reject-accept demo.
5. **Demo-day device wrangling** — you are Presenter B; the hardware works because you made it work.

## Entry points

- `make jetson-prepare` (run on the Jetson) — installs deps, sets up systemd unit.
- `make models-pull` — pulls Gemma + Whisper-tiny and validates SHA-256 against `models/manifest.sha256`.
- `make models-bench` — runs perf benchmarks; writes `models/bench.json`.
- `make deploy` (run on dev machine) — `rsync` + `systemd reload` to the Jetson.

## Stack

- **JetPack 6.x** with Ubuntu 22.04.
- **CUDA 12.x**, **TensorRT** (optional, only if Gemma-via-TRT-LLM gives a win over `ollama`).
- **`ollama`** for Gemma serving. Pull `gemma2:2b` (or `gemma3n` if available and fits).
- **`faster-whisper`** with `whisper-tiny` (CUDA build).
- **`tegrastats`** + **`jtop`** for power/perf monitoring on stage.
- **systemd** for service supervision (NOT Docker on the Jetson — adds startup latency).

## File layout

```
hardware/
  README.md          # bring-up runbook
  jetpack.md         # exact JetPack version + flash steps
  bom.md             # bill of materials (Jetson, display, battery, cables)
  scripts/
    setup.sh         # idempotent setup script
deploy/
  systemd/
    tera-agent.service
    tera-bridge.service
  rsync.sh
  Makefile.deploy
models/
  manifest.sha256
  bench.json
  pull.sh            # gemma + whisper pull with hash verify
mesh/
  README.md          # stretch goal docs
  network_setup.md   # WiFi-Direct or BLE setup for phone+laptop+Nano
  inject_demo.py     # the laptop-side script that injects unsigned tracks
```

## Stretch: mesh inject-reject-accept demo

The laptop runs `inject_demo.py` which sends an unsigned CoT track to the multicast group. The ATAK Bridge on the Jetson rejects it (logged + visible). Then the Jetson generates a signed plan; ATAK accepts it. Two devices visible on stage simultaneously.

This is the PS4 wow moment. P2 owns the signer; you own the hardware substrate (the mesh + the inject script + the side-by-side demo setup).

## Common gotchas

1. **The Jetson Orin Nano power mode matters.** `nvpmodel -m 0` (15W mode) for inference; `nvpmodel -m 1` (7W) idle. Switch is a sudo command.
2. **`ollama` on Jetson needs CUDA build, not the default ARM64 build from the install script.** Verify with `ollama serve --debug` and check it logs `CUDA detected`.
3. **Whisper on CUDA needs `faster-whisper` with `cuBLAS` + `cuDNN` shared libs.** JetPack ships these but the wheel needs to be built or sourced for ARM64 + CUDA 12.
4. **Gemma 2B Q4_K_M is ~1.7GB; Gemma 3n is larger but better quality.** Bench both; pick what fits memory and gives < 30s end-to-end.
5. **Battery life under inference is ~2-3 hrs at 15W.** For the demo, use a 100Wh+ USB-C PD bank. Bring two.
6. **Bluetooth is off in the demo.** If using BLE for Android EUD pairing, switch to USB tether instead — fewer variables on stage.

## Reference resources (Kyle's prior public work)

- **RFSim** — https://github.com/khicks1724/RFSim
  - Kyle's RF simulator project. Public repo.
  - **Hackathon rule interpretation:** "Tool Usage: any AI tools you'd like, as well as any other materials to build your project, provided that they're openly accessible and reasonably obtainable by all attendees." → RFSim is openly accessible, so we may **reference** it (read patterns, link to it in pitch as Kyle's prior credibility) or **depend on** it (import as a library if appropriately licensed).
  - **Hackathon rule constraint:** "All projects must be started from scratch during the hackathon with no previous work." → We do NOT copy-paste source from RFSim into TERA. The TERA repo is new work.
  - **Most relevant to:** mesh stretch (#23 — RF substrate patterns), parsing-verification (#22 — if RFSim has anomaly detection patterns for RF transmissions, those inform how the parsing-verification layer flags anomalous RF tags).
  - **Action:** Kyle skims the repo at kickoff and tells the team in 30 sec what's reusable.

## Definition of done for this lane

- `make jetson-prepare` succeeds on a clean JetPack image.
- `make models-bench` reports < 30s end-to-end for the hero prompt on Gemma.
- Display + battery rig demo'd at Sat dinner sync.
- (Stretch) Mesh inject demo works between laptop and Jetson at Sun 1100 dry-run.
