# Demo Recording Plan

> **Why this document exists:** the `.gitignore` (line 91 onward) catches `*.mov`, `*.mp4`, `*.webm`, `*.mkv`, `*.m4a`, `*.mp3`, `*.flac`, `*.wav`. Demo binaries do not live in the repo. This file is the canonical index of what we recorded, where the binaries live, and how each clip maps to the §12 pitch flow.
>
> **Source of truth for the live demo:** PRD §12 (5-minute structure). This file plans the *recordings*; PRD §12 plans the *live show*. Recordings exist as fallbacks per the rules in the table below.

## Storage convention

Recordings live in **`<repo>/docs/demo-clips/`** on whoever's laptop has the working tree checked out. The directory is tracked but its binary contents are gitignored at the `*.mov` / `*.mp4` / `*.webm` / `*.mkv` / `*.m4a` / `*.mp3` / `*.flac` / `*.wav` patterns — so anyone on the team who clones can `mkdir docs/demo-clips/` and drop their recordings in by the same naming convention without ever risking a `git add -A` accident.

Files stay local. **No team-Drive backup, no YouTube uploads** — except for the 1-minute submission video described below, which is a hackathon-rule requirement (not a sharing mechanism). Pitch-day distribution is presenter laptops opening files from `docs/demo-clips/` in QuickTime / VLC; nothing else needed.

## Filename convention (recorder's laptop)

`HHMM-<lane>-<short-desc>.<ext>` so files are time-ordered and lane-attributed even when only locally present. Examples:
- `2254-security-cot-inject-demo.mov`
- `2300-crypto-sign-bench.mp4`
- `2330-atak-plugin-mvp-demo.mov`

Already on disk under different names? Rename in-place; nothing in this doc references the on-disk filename.

## Recording index — current

### Security lane (P2 — Satriyo)

All five live at `docs/demo-clips/` (gitignored). Anyone with the repo checked out should see them after Satriyo or whoever holds the master copies drops them in.

| # | Recorded | Title | Size | Path in repo (relative to root) | Script that produced it |
|---|----------|-------|------|---------------------------------|--------------------------|
| S1 | Sat 22:54 | CoT Track Injection Demo — 3 scenarios (unsigned reject / tampered reject / signed accept) | 2.7 MB | `docs/demo-clips/2254-security-cot-inject-demo.mp4` | `security/cot_inject_demo.py` ・ `make inject-demo` |
| S2 | Sat 22:59 | Attack-Vector Rejection — 5 regression tests (issue #25) | 769 KB | `docs/demo-clips/2259-security-attack-vector-rejection.mp4` | `security/test_security_regressions.py` ・ `pytest security/test_security_regressions.py -v` |
| S3 | Sat 23:00 | Sign Benchmark — 1000 ML-DSA-65 round-trips, 0.128 ms avg (39× under PRD §11.2 target) | 354 KB | `docs/demo-clips/2300-crypto-sign-bench.mp4` | `crypto/sign_bench.py` ・ `make sign-bench` |
| S4 | Sat 23:02 | Security Scan — Bandit + pip-audit clean across all lanes | 1.7 MB | `docs/demo-clips/2302-security-bandit-pip-audit.mp4` | `make security` |
| S5 | Sat 23:04 | Structured Query Validator — live blocking of 3 attack types (injection / privesc / exfil) | 751 KB | `docs/demo-clips/2304-security-structured-query-validator.mp4` | `security/structured_query_validator.py` |

### ATAK lane (P4 — Ben)

| # | Recorded | Title | Size | Path in repo | Script / scenario |
|---|----------|-------|------|--------------|-------------------|
| B1 | Sat 22:30 | ATAK plugin MVP — no-model hookup demo | 84 MB | `docs/demo-clips/2230-atak-plugin-mvp-demo.mov` | Manual ATAK plugin walkthrough |

### Voice / agent lane (P1 — Jon)

| # | Recorded | Title | Size | Path in repo | Script that produced it |
|---|----------|-------|------|--------------|--------------------------|
| J1 | Sat 23:46 | Severity demo — audio test capture (first OBS recording, sanity check) | 2.7 MB | `docs/demo-clips/2346-voice-severity-audio-test.mov` | `scripts/demo_voice.py --severity-demo` |
| J2 | TBD | Severity demo — judge-facing pitch capture (with narration) | TBD | `docs/demo-clips/<HHMM>-voice-severity-pitch.mov` | `scripts/demo_voice.py --severity-demo` |

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
- All recordings open in QuickTime / VLC, full-screen ready, on the laptop NOT driving the live demo. Source: `docs/demo-clips/*.mp4` and `docs/demo-clips/*.mov`.
- Backup: have the same files copied to a USB stick in case the laptop driving fallbacks dies. Cheap insurance.
- Presenter B has a finger on the alt-tab key. One-second cut, no apology.

## Submission video plan (issue #28)

The hackathon submission **does** require a **1-minute YouTube unlisted video** — separate from team-internal sharing, this one is a hard rule. It's a *cut* of existing footage, not a new recording:

1. Pick the 60 seconds of source material with the highest information density. Current best candidates:
   - 0:00–0:15 — operator's voice prompt + ATAK draws blue line (B1 once it has `/plan` integration)
   - 0:15–0:30 — `make inject-demo` rejecting unsigned, accepting signed (S1)
   - 0:30–0:45 — `tcpdump` window + airplane-mode toggle (live capture or S4)
   - 0:45–1:00 — closing line + URL to public repo
2. Cut in iMovie / DaVinci / `ffmpeg`. No effects.
3. Title: `TERA — Tactical Edge Route Agent (60s overview)`.
4. Upload **unlisted** (not public, not searchable), link in submission form + repo `README.md`. Visibility, comments, embedding, etc. all locked down.

The cut and the URL go in the submission form by Sun 1200; the videos backing the cut stay in `docs/demo-clips/` like everything else.

## Post-event

The recordings stay in `docs/demo-clips/` on each contributor's local checkout. Whether anything goes public after the event is a separate decision — default is *don't* unless we explicitly choose to.

## Cross-references

- PRD §12 (live pitch flow) — primary source for which beats need fallbacks.
- PRD §11.2 (success metrics) — S3 + S4 are the on-stage evidence for these.
- `docs/cyber_demo_script.md` (Satriyo's pitch script) — text version of S1, S2, S5.
- `.gitignore` line 91+ — the rule that keeps binaries out of the repo.
- Issue #28 — 1-minute submission video tracking.
