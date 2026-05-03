# Demo Recording Plan

> **Why this document exists:** the `.gitignore` (line 91 onward) catches `*.mov`, `*.mp4`, `*.webm`, `*.mkv`, `*.m4a`, `*.mp3`, `*.flac`, `*.wav`. Demo binaries do not live in the repo. This file is the canonical index of what we recorded, where the binaries live, and how each clip maps to the §12 pitch flow.
>
> **Source of truth for the live demo:** PRD §12 (5-minute structure). This file plans the *recordings*; PRD §12 plans the *live show*. Recordings exist as fallbacks per the rules in the table below.

## Storage convention

Recordings stay off the public repo and out of the codebase, but during dev they live in a known project subdirectory so the team can find them without hunting `~/Desktop`. Team-wide approach:

1. **Local on the recorder's laptop:** `<repo>/docs/demo-clips/` (gitignored at the `*.mov`/`*.mp4`/`*.webm`/`*.mkv`/`*.m4a`/`*.mp3`/`*.flac`/`*.wav` patterns — directory tracked via `.gitkeep` + `README.md`, binaries never committed). See `docs/demo-clips/README.md` for filename conventions and per-clip workflow.
2. **Team backup:** shared Drive folder (link in team Signal channel, not committed here — Drive folder URL changes per quarter).
3. **Pitch-day distribution:** YouTube unlisted upload **before** Sun 1300 (cut-over from "team backup" to "publicly fetchable URL" so the submission packaging step can include direct links).

When uploading to YouTube, set:
- Visibility: **Unlisted** (not public, not searchable).
- License: Standard YouTube (so we retain rights).
- Comments / Like / Embedding: disabled.
- Title prefix: `TERA — `.

## Filename convention (recorder's laptop)

`HHMM-<lane>-<short-desc>.<ext>` so files are time-ordered and lane-attributed even when only locally present. Examples:
- `2254-security-cot-inject-demo.mov`
- `2300-crypto-sign-bench.mp4`
- `2330-atak-plugin-mvp-demo.mov`

Already on disk under different names? Rename in-place; nothing in this doc references the on-disk filename.

## Recording index — current

### Security lane (P2 — Satriyo)

| # | Recorded | Title | Length (rough) | Local filename | YouTube URL | Script that produced it |
|---|----------|-------|----------------|----------------|-------------|--------------------------|
| S1 | Sat 22:54 | CoT Track Injection Demo — 3 scenarios (unsigned reject / tampered reject / signed accept) | ~60-90s | `2254-security-cot-inject-demo.mp4` *(currently on Satriyo's laptop as `satriyo_demo_security_1.mp4` — rename when moving into `docs/demo-clips/`)* | TBD | `security/cot_inject_demo.py` ・ `make inject-demo` |
| S2 | Sat 22:59 | Attack-Vector Rejection — 5 regression tests (issue #25) | ~45-60s | `2259-security-attack-vector-rejection.mp4` *(was `satriyo_security_demo_2.mp4`)* | TBD | `security/test_security_regressions.py` ・ `pytest security/test_security_regressions.py -v` |
| S3 | Sat 23:00 | Sign Benchmark — 1000 ML-DSA-65 round-trips, 0.128 ms avg (39× under PRD §11.2 target) | ~30-45s | `2300-crypto-sign-bench.mp4` *(was `satriyo_security_demo_3.mp4`)* | TBD | `crypto/sign_bench.py` ・ `make sign-bench` |
| S4 | Sat 23:02 | Security Scan — Bandit + pip-audit clean across all lanes | ~30-45s | `2302-security-scan.mp4` *(was `satriyo_security_demo_4.mp4`)* | TBD | `make security` |
| S5 | Sat 23:04 | Structured Query Validator — live blocking of 3 attack types (injection / privesc / exfil) | ~30-45s | `2304-security-structured-query-validator.mp4` *(was `satriyo_security_demo_5.mp4`)* | TBD | `security/structured_query_validator.py` |

### ATAK lane (P4 — Ben)

| # | Recorded | Title | Length | Local filename | YouTube URL | Script / scenario |
|---|----------|-------|--------|----------------|-------------|-------------------|
| B1 | Sat 22:30 | ATAK plugin MVP — no-model hookup demo | ~30-60s | `2230-atak-plugin-mvp-demo.mov` (in `docs/demo-clips/`, gitignored, ~84 MB) | TBD | Manual ATAK plugin walkthrough |

### Voice / agent lane (P1 — Jon)

| # | Recorded | Title | Length | Local filename | YouTube URL | Script that produced it |
|---|----------|-------|--------|----------------|-------------|--------------------------|
| J1 | Sat 23:46 | Severity demo — audio test capture (first OBS recording, sanity check) | ~30s | `2346-voice-severity-audio-test.mov` (in `docs/demo-clips/`, gitignored, ~2.7 MB) | TBD | `scripts/demo_voice.py --severity-demo` |
| J2 | TBD | Severity demo — judge-facing pitch capture (with narration) | ~30-45s | `<HHMM>-voice-severity-pitch.mov` | TBD | `scripts/demo_voice.py --severity-demo` |

### Hardware / Jetson lane (P3 — Kyle)

| # | Title | Status |
|---|-------|--------|
| K1 | Jetson + Gemma 3 4B + Cesium UI walkthrough | Not yet recorded. Plan: capture Sun 0700-0900 alongside the integration smoke-test (issue #82). |

## Pitch-day fallback rules

The 5-minute pitch (PRD §12) is the live show. **Recordings are insurance, not content.** If a beat fails live, presenter B switches the screen to the matching recording and presenter A keeps narrating.

| Pitch beat (PRD §12) | Live primary | Recording fallback | Cut decision rule |
|----------------------|--------------|---------------------|-------------------|
| 0:00–0:30 hook | None — read §2 verbatim | n/a | Hook is text; no fallback needed. |
| 0:30–1:30 problem + persona | None | n/a | Same. |
| 1:30–2:15 SF live demo | Live `/plan` from ATAK plugin (#79 + #80) → blue line | **B1** if plugin chat doesn't show a response within 30s | Presenter B watches the chat scroll. No agent response by 0:30 elapsed → switch to B1, narrator says "the plugin is mid-build, here's the same demo from earlier tonight." |
| 2:15–3:00 austere AO flip | Same plugin, different AOI | **B1** | Same rule. |
| 3:00–3:30 PS4 wow moment | `make inject-demo` live | **S1** | If terminal hangs > 5s, presenter B Cmd-Tabs to S1 (already loaded in a media player). One-second cut, no apology. |
| 3:30–4:00 wow + offline proof | `tcpdump` window + airplane-mode toggle visible | **S3** + **S4** for evidence sound bites | If the `tcpdump` capture stalls, S3 + S4 cover the "we measured this and it's clean" beat. |
| 4:00–4:30 novelty + competitive table | Single slide | **S2** for live evidence of the "5 attack vectors blocked" claim if asked | Q&A driven; not a switch, just have it loaded. |
| 4:30–4:50 business model | Single slide | n/a | |
| 4:50–5:00 ask | Speaker | n/a | |

**Pre-flight check (Sun 1340, per PRD §12.4):**
- All recordings open in QuickTime / VLC, full-screen ready, on the laptop NOT driving the live demo.
- YouTube URLs printed on a notecard (in case laptop dies and judge wants to rewatch from the panel iPad).
- Presenter B has a finger on the alt-tab key. One-second cut.

## Submission video plan (issue #28)

The hackathon submission asks for a **1-minute YouTube video**. That's a *cut*, not a record-from-scratch:

1. Pick the 60 seconds of source material with the highest information density. Current best candidates:
   - 0:00–0:15 — operator's voice prompt + ATAK draws blue line (B1 once it has /plan integration)
   - 0:15–0:30 — `make inject-demo` rejecting unsigned, accepting signed (S1)
   - 0:30–0:45 — `tcpdump` window + airplane-mode toggle (live capture or S4)
   - 0:45–1:00 — closing line + URL to public repo
2. Cut in iMovie / DaVinci / `ffmpeg`. No fancy effects.
3. Title: `TERA — Tactical Edge Route Agent (60s overview)`.
4. Upload unlisted, link in submission form + repo `README.md`.

## After-event archive

- Sun 1700 (post-winners): all recordings move from `<repo>/docs/demo-clips/` to the team's permanent Drive folder. The local repo directory stays empty so future devs see the README without 100+ MB of stale clips.
- Sun 1700: anyone who wants to retain a personal copy makes a personal Drive backup before the shared folder is cleaned up.
- Mon: any recordings we want public become public-on-YouTube + linked from the post-mortem README. Anything sensitive stays unlisted forever.

## Cross-references

- PRD §12 (live pitch flow) — primary source for which beats need fallbacks.
- PRD §11.2 (success metrics) — S3 + S4 are the on-stage evidence for these.
- `docs/cyber_demo_script.md` (Satriyo's pitch script) — text version of S1, S2, S5; should reference the YouTube URLs once those land so the script is self-contained.
- `.gitignore` line 91+ — the rule that keeps binaries out of the repo.
- Issue #28 — 1-minute submission video tracking.
