# Blog outline — TERA security beat

> **Status:** outline only. Drafted because items A and E in the novelty
> assessment scored *NOVEL — INDUSTRY-BLOG-PUBLISHABLE* (deployment-context
> novelty, not primitive novelty). This is hackathon-experience-report
> material, not a research paper. See "What this is NOT" below before
> drafting.

## Working title + hook

**Title:** *Hardening an offline edge-LLM for ATAK: post-quantum signed
routes, hash-pinned weights, and a fail-closed render gate, in 36 hours*

**One-line hook:** "We took a 4B-parameter LLM, an Android Tactical Assault
Kit plugin, a Jetson Orin Nano, and the NIST PQC standard from August 2024,
and stitched them into the first offline route planner whose every line on
the map carries a Dilithium signature back to the device that drew it — and
this is what we'd ship differently next time."

## Five-section outline

### 1. Why the Marine on the contested mesh can't trust the blue line on his ATAK

- The unauthenticated-CoT problem: ATAK's *Cursor on Target* protocol has no
  authentication primitive in the base spec; on a coalition or adversary-
  proximate mesh, an injected track is indistinguishable from a friendly one.
- This isn't a research observation; it's documented and well-known. What's
  not documented is what happens when you put an *LLM-generated* route on
  that wire — the same lack-of-authentication, but now the producer is a
  language model running on a device with no human in the cryptographic
  loop.

**Cite:** PRD §8.1 (`docs/PRD.md` lines 274–282); the field-known
unauthenticated-CoT property of TAK; ATAK plugin chat threads.

### 2. The verify gate, end-to-end

- Show the actual flow: voice → Whisper-tiny → Gemma → structured RouteQuery
  JSON → Valhalla → signed PlanResponse → `/plan/verify` → ATAK.
- Walk through `agent/orchestrator.py:334` (`verify_plan_response`): payload
  binding (uid, route_hash, rationale, lat/lon, mission_type), then crypto
  verify, then fail-closed.
- The deployment-context delta from "ML-DSA exists" to "ML-DSA gates the
  render path of an LLM-produced route on a Jetson at 7W idle in airplane
  mode": this is the part worth writing up.
- Include the tamper-reject test transcript
  (`tests/test_orchestrator.py:601`) as the "show, don't tell".

**Cite:** `crypto/ml_dsa_signer.py`, `agent/orchestrator.py:184`
(`_sign_response`), `agent/orchestrator.py:334` (`verify_plan_response`),
`agent/app.py:115` (`/plan/verify`).

### 3. The supply-chain layer: SHA-256 pinning is the floor, not the ceiling

- `models/MANIFEST.yml` + `make model-integrity` is competent industrial
  practice — analogous to a constrained Sigstore / in-toto attestation
  shape, just without the signed-attestation step.
- Be honest in the post: a hash list checked into the same repo as the code
  is only as strong as the repo's branch protection. Show the upgrade path
  to detached signatures + Sigstore.
- The unsafe-`torch.load` AST scan is a Bandit `B614` equivalent. Ship it
  anyway, because the cost is one CI minute and the failure mode is RCE.
- Discuss what the scanner does *not* catch (aliased imports, indirect
  calls, cross-function taint) — credibility move.

**Cite:** `models/MANIFEST.yml`, `security/model_integrity.py`,
`security/test_model_integrity.py`, `Makefile:95`, Bandit B614 docs,
semgrep `python.pytorch.security.pytorch-load`.

### 4. The offline-only proof: tcpdump beats audits

- Pre-flight checklist on stage; airplane-mode toggle visible to audience.
- Three-pane demo monitor (`infra/security_demo_monitors.sh`): tcpdump, audit
  log scroll, signed CoT scroll. Zero outbound packets is a *visible*
  artifact, not a claim in a slide.
- Key insight for the post: when your threat model includes "operator's
  device may already be in a denied environment", the right verification is
  a live wire-trace that judges can independently witness, not a SOC2 audit
  artifact.

**Cite:** `infra/security_demo_monitors.sh`, `infra/tcpdump_demo.sh`,
PRD §8.4 lines 317–325.

### 5. What we'd ship differently in v2 (the credibility section)

- Trust list: implement key_id → public-key lookup at the `/plan/verify`
  layer (not just in `verify_cot`); document an enrollment ceremony for
  multi-device.
- Manifest: add a detached signature on `MANIFEST.yml` itself; move toward a
  SLSA Level 2 build with provenance attestations.
- Hardware-rooted identity: TPM2 / NV-SE-backed device key on Jetson Orin
  with attestation; out-of-scope for hackathon, on the v2 wishlist.
- Egress firewall: today an opt-in shell script; v2 is a `tera-firewall.service`
  triggered by `TERA_PHASE=3` (PRD §8.4 line 321; tracked in #22).
- The two-signature operator-approval path (ADR-003) is the more interesting
  workflow than single-sig `/plan` — call out the asymmetry.

## Specific code & data the post would cite

- `crypto/ml_dsa_signer.py:115` — the Dilithium3 signer.
- `crypto/ml_dsa_signer.py:165` — the verify path with payload-hash fast
  path.
- `agent/orchestrator.py:184` — sign on emit.
- `agent/orchestrator.py:334` — verify on render.
- `agent/orchestrator.py:292` — the payload→response binding (this is the
  "you can't swap the geometry without breaking the sig" piece).
- `models/MANIFEST.yml` — the actual pin file.
- `security/model_integrity.py:43` — `_sha256_file` with CRLF normalization
  (Windows-CI lesson).
- `security/model_integrity.py:101` — the AST scanner.
- `security/pipeline.py:67` — the six-stage `run_pipeline`.
- `security/test_security_regressions.py` — the 5 prompt-injection vectors
  the pipeline blocks (S2 demo clip).
- `crypto/sign_bench.py` — the sign+verify benchmark output (under
  PRD §11.2's 5ms target).
- `tests/test_orchestrator.py:601` — the tamper-reject test.
- `infra/security_demo_monitors.sh` — the offline-only proof harness.

Recordings to embed (already captured):
- S1 — `docs/demo-clips/2254-security-cot-inject-demo.mp4` (CoT inject reject).
- S2 — `docs/demo-clips/2259-security-attack-vector-rejection.mp4` (5
  attack vectors).
- S3 — `docs/demo-clips/2300-crypto-sign-bench.mp4` (0.128ms sign+verify).

## What this is NOT

This blog post is **not** a novel cryptographic contribution. We did not
invent ML-DSA. We did not invent Sigstore. We did not invent Bandit. We did
not invent CoT. We did not invent ATAK. The contribution is a **deployment
synthesis**: assembling a coherent, tested, demonstrable security posture
for a specific deployment context (offline edge LLM → ATAK render gate on
a battery-powered Jetson) where prior art exists for each piece but the
assembled whole is — to the authors' knowledge — not yet documented in the
open literature for this use case.

If a reviewer asks "what's new here?", the answer is "the assembly, the
testing transcript, the honest gap list — not the primitives". If that
answer doesn't satisfy a venue, the post is in the wrong venue.

We must not call this work "post-quantum cryptography research". The PQC
piece (ML-DSA-65 / Dilithium3) is a NIST-standardized primitive used as
designed. Calling our application of a standard a research contribution is
academic-fraud-adjacent and would correctly get the post rejected.

## Suggested venues, ranked by fit

1. **Team / company engineering blog (TruePoint).** Best fit by far. House
   blogs are the natural home for hackathon experience reports; the
   audience expectation is "we built this in a weekend, here's what we
   learned" rather than "we proved a new theorem".
2. **The Rust / Python / `liboqs-python` user community via lobste.rs +
   /r/netsec.** The honest gap-list approach plays well in these venues;
   the deployment-context novelty is interesting to practitioners.
3. **USENIX `;login:` short article.** A short *experience report* under
   the deployment / lessons-learned column is a credible fit. Not a peer-
   reviewed venue; reasonable submission cost.
4. **IEEE Security & Privacy magazine "Building Security In" column.** Same
   shape — practitioner-facing, not peer-reviewed in the academic sense,
   open to deployment writeups. Submission process is heavier; only worth
   it if there's a coalition / DoD audience reason to want it indexed
   there.
5. **DEF CON / B-Sides talk-not-paper track (next cycle).** A talk version
   of this material plays well to a tactical / mil-hacker audience.
   Different deliverable; mention as future channel, not as a near-term
   target.

We **do not** target SOSP, NDSS, S&P (the academic conference), CCS,
USENIX Security, or any peer-reviewed cryptography venue. We are not making
a research-grade contribution and pretending otherwise wastes reviewer
time.
