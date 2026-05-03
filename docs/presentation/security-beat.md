# Security beat — 90s presenter script

> Slot in the 5-minute pitch flow: PRD §12 / `docs/PRD.md` line 433 (3:00–3:30,
> Presenter B). This document expands that 30-second beat into a 90-second
> script for use in a separate security-focused 5-minute deck or extended
> Q&A. The live pitch beat itself is still 30s; this script is the source
> material we cut down from.
>
> **Suggested presenter:** P2 (Satriyo) — owns the entire crypto + security
> lane (PRD §13 lane mapping; signers in `crypto/`, pipeline in `security/`,
> demo monitors in `infra/`). The signed-route construct lands harder when
> the engineer who shipped it is the one narrating.
> Backup: P1 (Jon) if Satriyo is on the live `/plan` driver seat.

---

## Beat structure (90 seconds)

Two demo cuts, three sentences each. One framing line at the end.

### Cut 1 — Signed-route tamper-reject (≈40 seconds)

**What's on screen:** terminal split. Left pane: `python security/cot_inject_demo.py`
output (or replay of clip S1, `docs/demo-clips/2254-security-cot-inject-demo.mp4`).
Right pane: ATAK MapView with the rejected route highlighted in red.

**What presenter B actually says:**

1. "CoT — the message format every TAK device speaks — is unauthenticated by
   default. Anyone on the multicast bus can inject a fake route and ATAK has
   no way to know."
2. "We sign every route at the source with ML-DSA-65 — Dilithium, the NIST
   FIPS 204 post-quantum standard from August 2024. Here's a tampered route
   hitting the verifier; the bridge rejects it before ATAK ever renders it."
3. "The signed payload is bound to the route geometry, the rationale, and the
   destination — so an adversary who flips one byte of the geometry breaks the
   signature. Fail-closed: no signature, no render."

**Code anchor for Q&A:** `agent/orchestrator.py:334` (`verify_plan_response`),
`crypto/ml_dsa_signer.py:115` (signer/verifier), `tests/test_orchestrator.py:601`
(tamper-reject test).

---

### Cut 2 — Model integrity CI fail (≈40 seconds)

**What's on screen:** terminal. Run `make model-integrity` once green, then
mutate one byte of `models/piper/en_US-ryan-high.onnx.json`, re-run, show
the red FAIL with the expected/actual diff.

**What presenter B actually says:**

1. "Same threat model, one layer down: if an attacker swaps a model file
   on disk, the signed-route guarantee at the top is meaningless because the
   thing producing the route was already poisoned."
2. "Every model artifact in the repo has a SHA-256 pin in `models/MANIFEST.yml`,
   verified on every CI run. Watch — I flip one byte of a Piper voice config
   and the CI gate fires immediately, with the expected vs actual hash."
3. "Same script also AST-scans our Python for `torch.load(...)` calls
   without `weights_only=True` — that one parameter is the difference between
   loading weights and loading arbitrary pickle code from the filesystem."

**Code anchor for Q&A:** `models/MANIFEST.yml`, `security/model_integrity.py:43`
(`_sha256_file`), `security/model_integrity.py:101` (`_scan_file_for_unsafe_loads`),
`security/test_model_integrity.py:43` (tamper detection test), `Makefile:95`
(`make model-integrity`), `Makefile:98` (wired into `make ci`).

---

## The framing line (≈10 seconds)

The single line that lands the "why this matters for tactical edge AI"
framing:

> **"Edge AI for tactical routing means the device, the model, and the route
> are all in the threat surface. Sign the route, pin the model, prove zero
> egress — three primitives, none of them new in isolation, but no one else
> on the contested-mesh side has stitched them into one offline-only pipeline
> for the Marine you can't reach."**

Delivered after Cut 2, into the airplane-mode / `tcpdump` proof beat
(PRD §12 line 434, the 3:30–4:00 beat). This is the handoff line from the
security beat into the offline-proof beat.

---

## Cut decisions on the day

- If the live verify-reject demo hangs > 5 seconds, presenter B Cmd-Tabs to
  clip **S1** (`docs/demo-clips/2254-security-cot-inject-demo.mp4`).
- If `make model-integrity` is slow because the manifest is unhashed
  locally, fall back to the new `M1` recording (see
  `docs/demo-recording-plan.md` §Security lane). The model-integrity beat
  has a cheap recovery — there's no operator-perceptible difference between
  live and recorded for this segment.
- If the entire 90s overruns, drop Cut 2 first (model integrity is the
  layer-down beat; Cut 1 is the headline). Cut 1 carries the §12 PS4 hook;
  Cut 2 is the bonus.

---

## What this beat is **not** trying to claim

When a judge asks "is the cryptography novel?", the honest answer is:

- The **primitives** (ML-DSA-65, SHA-256 manifest pinning, structured-query
  validation, unsafe-`torch.load` linting) are all standard practice or
  NIST-standardized.
- The **delta** is the system-level integration: PQC-signed routes + supply-
  chain pinned models + offline-only egress + structured-query injection
  guard, all assembled for an edge-LLM-in-ATAK use case where today's
  baseline is unauthenticated CoT and unverified weights.

We do not claim novel cryptography. We claim the first open, fully-offline,
voice-enabled NL route planner that renders into ATAK with PQC-signed
provenance (PRD §9 line 355, novelty claim). That is the framing every
follow-up answer should ladder back to.
