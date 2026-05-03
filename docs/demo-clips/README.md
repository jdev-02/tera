# Demo Clips — Local-Only

> **This directory is gitignored** (`*.mov`, `*.mp4`, `*.webm`, `*.mkv`, `*.m4a`, `*.mp3`, `*.flac`, `*.wav`). Only this README and a `.gitkeep` live in version control. The clips themselves stay on the recorder's laptop and (post-recording) in the team Drive folder + an unlisted YouTube channel for pitch-day fallback.
>
> **Why not commit?** Repo bloat (the ATAK plugin SDK incident at ~117 MB is the cautionary tale). YouTube unlisted serves the dissemination need at a fraction of the friction.

## Filename convention

`HHMM-<lane>-<short-desc>.<ext>`

- `HHMM` = 24-hour time the clip was recorded (Pacific). Files sort chronologically.
- `<lane>` = `voice`, `security`, `atak`, `crypto`, `hardware`, `agent`, etc.
- `<short-desc>` = kebab-cased one-liner.

Examples:
- `2230-atak-plugin-mvp-demo.mov`
- `2346-voice-severity-audio-test.mov`
- `0500-voice-severity-pitch-mode.mov`

## Index

The canonical recording index lives in [`../demo-recording-plan.md`](../demo-recording-plan.md). Update there when you record a new clip; this directory is just where the binary lives until it lands in the team Drive folder + YouTube.

## Workflow per clip

1. Record locally (OBS / QuickTime).
2. Save to this directory with the filename convention above.
3. Update `docs/demo-recording-plan.md` table with the local filename + lane + description.
4. Upload to YouTube unlisted (post-Sun-1300 cutover) and add the URL to the same table.
5. Optionally drop a copy in the team Drive folder for cross-team review.

## Cross-references

- `docs/demo-recording-plan.md` — canonical recording index + pitch-day fallback rules.
- PRD §12 — live pitch flow this material backs up.
- `.gitignore` — the rule keeping these binaries out of git.
