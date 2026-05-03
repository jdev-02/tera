# TERA Security Posture

> Public-facing posture summary. Authoritative source for what the hackathon
> build does and does not defend against. Cross-reference with PRD `docs/PRD.md`
> §6, §8, §9 for the full threat model. Code citations are file path + line
> number against `main` as of post-#97 / #100 / #105.

---

## 1. Threat model

The TERA threat model is articulated in PRD §8 (`docs/PRD.md` lines 270–334)
and the competitive framing in §9 (`docs/PRD.md` lines 338–355). The headline
threat the system is designed for is **TAK track injection on a contested or
coalition mesh** (PRD §8.1, lines 274–282):

> CoT (Cursor on Target) is the lingua franca of TAK. By default, CoT messages
> are unauthenticated… A clean route from a Marine's Jetson is
> indistinguishable on the wire from a poisoned route injected by an
> adversary.

Around that headline threat sits a set of secondary threats the build also
takes positions on (PRD §8.3 table, lines 305–314):

- **Data exfiltration via LLM** — prompt-injected tool calls with outbound URLs.
- **Model tampering / supply chain** — compromised LLM or TTS weights.
- **Map data poisoning** — tampered OSM extracts or DEM tiles.
- **Adversarial prompts** — operator-style queries crafted to leak position or
  route through hostile AOs.
- **ATAK CoT injection** — same family as track injection, scoped to ATAK
  ingest specifically.

Out of scope for this hackathon (PRD §8.5, lines 327–333): FIPS 140-3
validation of the crypto module, DoD STIG compliance, cross-domain solutions,
formal ATO. Each is explicitly flagged as transition work.

---

## 2. Defenses shipped

One row per real defense. The table is intentionally compact so judges can
read it from one paste; padding it would make the gaps in §4 less honest.

| Threat | Mitigation | Code | Tests |
|---|---|---|---|
| **TAK track injection** (PRD §8.1) | ML-DSA-65 (Dilithium3, NIST FIPS 204) signature on every plan response and CoT field; fail-closed verify gate before ATAK render. Ed25519 fallback for dev machines without `liboqs`. | `crypto/ml_dsa_signer.py` (signer/verifier), `crypto/cot_signer.py:88` (`sign_cot`) and `crypto/cot_signer.py:190` (`verify_cot`), `agent/orchestrator.py:365` (`verify_plan_response`), `agent/app.py:142` (`/plan/verify` endpoint) | `tests/test_orchestrator.py:591` (`test_verify_plan_response_accepts_signed_response`), `tests/test_orchestrator.py:601` (`test_verify_plan_response_rejects_tampered_route`), `tests/test_orchestrator.py:612` (`test_verify_plan_response_rejects_missing_signature`), `crypto/sign_bench.py` (perf), `security/cot_inject_demo.py` (S1 demo clip) |
| **Track injection — payload binding** | Signed payload is bound back to the rendered route (`request_id`, `route_hash`, `rationale`, destination lat/lon, `mission_type`). A signature that verifies cryptographically but covers a different route is rejected. | `agent/orchestrator.py:322` (`_payload_matches_plan_response`), `crypto/cot_signer.py:116` (`_verify_payload_matches_cot_envelope`) | `tests/test_orchestrator.py:601` (tampered route → reject) |
| **Two-signature operator approval** (ADR-003) | `/plan/approve` returns a wrapper signed by both device key and operator key; `verify_approval_wrapper` requires both signatures and binds operator's signed payload to the wrapper's `route_hash`. | `crypto/cot_signer.py:330` (`verify_approval_wrapper`) | `tests/test_orchestrator.py` two-sig wrapper tests; ADR `docs/adrs/2026-05-02-003-two-signature-approval.md` |
| **Trust list — both render paths** (post-#105) | `crypto/keys/trust_list.json` flat-file map of `key_id → public_key_hex`. **The HTTP `/plan/verify` path consults the trust list before any crypto math** (`agent/orchestrator.py:420` imports `load_trust_list`, `:430` looks up the `key_id`, `:438` returns `Untrusted key_id - REJECTED` on miss). The trusted public key is then passed *explicitly* into `MLDSASigner.verify` (`agent/orchestrator.py:459`) so the signer cannot silently fall back to a freshly-generated local keypair under the same `key_id` string. The CoT-XML mesh path is unchanged: `verify_cot` (`crypto/cot_signer.py:230`) does the same check. The device's own public key is auto-bootstrapped at FastAPI startup (`agent/app.py:42` lifespan → `agent/app.py:58` calls `_bootstrap_device_trust`) and again on first sign as belt-and-suspenders (`agent/orchestrator.py:267`, `:288` `_bootstrap_device_trust` → `crypto/cot_signer.py:532` `export_public_key_to_trust_list`). | `crypto/cot_signer.py:518` (`load_trust_list`), `crypto/cot_signer.py:532` (`export_public_key_to_trust_list`), `agent/orchestrator.py:420–459` (verify-path wiring), `agent/app.py:42–60` (lifespan bootstrap) | `tests/test_orchestrator.py:626` (`test_verify_plan_response_rejects_untrusted_key_id`), `tests/test_orchestrator.py:654` (`test_verify_plan_response_accepts_trusted_key_id`), `tests/test_orchestrator.py:679` (`test_trust_list_bootstrapped_on_startup`) |
| **Model tampering — committed assets** (PRD §8.3 row 3) | SHA-256 manifest pinning all four committed Piper voice configs; CI gate via `make model-integrity` runs on every push. | `models/MANIFEST.yml` (4 required, 4 placeholder), `security/model_integrity.py:58` (`verify_manifest`) | `security/test_model_integrity.py:23` (manifest exists), `security/test_model_integrity.py:29` (required hashes pass), `security/test_model_integrity.py:43` (tamper detection) |
| **Unsafe deserialization at model load** | AST scanner blocks `torch.load(...)` calls without `weights_only=True`; CI fails on any hit. | `security/model_integrity.py:101` (`_scan_file_for_unsafe_loads`), `security/model_integrity.py:139` (`scan_unsafe_loads`); `Makefile:95` (`model-integrity` target wired into `ci`) | `security/test_model_integrity.py:57` (detects unsafe), `security/test_model_integrity.py:71` (accepts safe), `security/test_model_integrity.py:85` (project source clean) |
| **Prompt injection / instruction override** (PRD §8.3 row 5) | Six-stage `security.pipeline.run_pipeline`: SuperAgent Guard (or local regex fallback), redactor, provenance check, schema validator with substring-blocklist, policy gate, route trust score. LLM emits structured RouteQuery JSON only — natural-language strings never reach the routing engine. | `security/pipeline.py:67` (`run_pipeline`), `security/structured_query_validator.py:53` (forbidden substrings), `security/superagent_integration.py` (Guard + Redact wrapper with offline fallback), `security/data_provenance.py`, `security/policy_gate.py`, `security/route_trust_score.py` | `security/test_security_regressions.py` (S2 demo clip, 5 attack vectors), `security/test_plan_guard.py`, `security/prompt_injection_tests.py`; eval set `eval/prompts.yml` includes `adversarial_*` entries that must pipeline-block |
| **Data exfiltration via LLM** (PRD §8.3 row 2) | No `http_get` / `fetch` tool registered; tool dispatch is a static deterministic mapping from validated `RouteQuery.objective` → `find_pois` / `route`. Egress firewall (`infra/jetson_firewall.sh enable`) drops outbound on Phase 3. | `agent/orchestrator.py:_dispatch_tools` (deterministic mapping, no network tools), `agent/tools.py` (registered tools), `infra/jetson_firewall.sh` | `infra/security_demo_monitors.sh` (tcpdump pane proves zero outbound during plan); `make tcpdump-demo` |
| **Audit trail** (PRD §8.4 proof point 4) | Every prompt, RouteQuery emission, pipeline allow/block, tool dispatch, and signature event is emitted as a structured `audit_event(...)`. | `security/audit_log.py`, `agent/orchestrator.py` (audit_event call sites in `plan()`) | `security/test_audit_log.py` |
| **Offline-only operation proof** (PRD §8.4 proof points 1–3) | Three-pane demo monitor: tcpdump (zero outbound), audit log scroll, signed-CoT scroll. SHA-256 manifest can be diffed against printed-on-card hashes (PRD §8.4 proof point 3). | `infra/security_demo_monitors.sh`, `infra/tcpdump_demo.sh`, `infra/audit_log_scroll.sh`, `infra/cot_signed_scroll.sh` | manual; recordings S1–S5 in `docs/demo-recording-plan.md` |

---

## 3. Defenses out of scope for hackathon

We are not claiming any of the following. If a judge asks, the honest answer
is "post-hackathon transition work":

- **Mesh-distributed CRL or signed key-rotation protocol.** PRD §8.2 row 4
  (line 294) describes the trust list as "static list of allowed key IDs for
  the demo" and explicitly defers CRL/shared-root distribution to post-MVP.
  The flat-file allowlist at `crypto/keys/trust_list.json` is the *intended*
  shape for the hackathon. There is no CRL, no revocation path, no expiry,
  and no multi-device key-distribution protocol — these are tracked
  separately (PRD §8.5; production encrypted-tunnel ADR is open as #70).
- **Hardware-rooted device identity.** Keys live on the rootfs at
  `/etc/wayfinder/keys/` (Jetson) or `crypto/keys/` (dev). The PRD claims
  "rootfs encrypted" (PRD §8.2 row 1, line 291) — encrypted-rootfs is an
  install-time configuration, not something the application enforces. There is
  no TPM, no secure element, no attestation.
- **Signed map / DEM differential updates.** PRD §8.3 row 4 (line 310) lists
  "hash-verify PBF on load; ship known-good extracts" for the MVP. Today the
  PBF/DEM verification step is documented but not implemented in CI; only
  model artifacts are pinned in `models/MANIFEST.yml`.
- **FIPS-validated crypto module.** We use `liboqs` (a research/reference
  implementation), not a FIPS 140-3 module. PRD §8.5 (line 329) flags this
  explicitly.
- **DoD STIG / formal ATO.** PRD §8.5 lines 330–332.
- **Side-channel hardening** (power, thermal, EM). PRD §8.3 row 8 (line 314).
- **Sandboxed tool runtime / DNS sinkhole.** PRD §8.3 row 2 post-MVP column
  (line 308) — out of scope.

---

## 4. Verification recipe

Seven commands a judge can run on a fresh checkout to verify each defense
beat. All work offline; none require network egress after `make install`.
Last validated against `main` post-#105 — every test in command 2 was
re-run locally and passed (`6 passed in 0.76s`).

```bash
# 1. Model supply-chain integrity (manifest + AST scan).
#    Expects: 4 required Piper hashes verified, scan finds 0 unsafe loads.
make model-integrity

# 2. Plan response verify gate — happy path + tamper-reject + missing-sig
#    + trust-list-reject + trust-list-accept + startup-bootstrap.
pytest tests/test_orchestrator.py::test_verify_plan_response_accepts_signed_response \
       tests/test_orchestrator.py::test_verify_plan_response_rejects_tampered_route \
       tests/test_orchestrator.py::test_verify_plan_response_rejects_missing_signature \
       tests/test_orchestrator.py::test_verify_plan_response_rejects_untrusted_key_id \
       tests/test_orchestrator.py::test_verify_plan_response_accepts_trusted_key_id \
       tests/test_orchestrator.py::test_trust_list_bootstrapped_on_startup -v

# 3. Spoofed-key_id end-to-end check. Sign a route, then mutate the
#    Signature.key_id to a name the trust list has never seen and POST to
#    /plan/verify. Expect HTTP 200 with body
#    `{"valid": false, "reason": "Untrusted key_id - REJECTED", ...}`.
#    See tests/test_orchestrator.py::test_verify_plan_response_rejects_untrusted_key_id
#    for the exact monkeypatch shape; the same construct is the new
#    presenter Cut-1b in docs/presentation/security-beat.md.

# 4. CoT inject-reject construct (single-device PS4 demo, S1 clip source).
make inject-demo

# 5. Sign benchmark — proves ML-DSA-65 sign+verify under PRD §11.2 5ms target.
make sign-bench

# 6. Security pipeline regression suite (5 attack vectors blocked, S2 source).
pytest security/test_security_regressions.py -v

# 7. Three-pane offline-proof demo: tcpdump (zero outbound) + audit log
#    scroll + signed CoT scroll. Run while issuing a /plan request from
#    another shell.
make demo-proofs    # or: bash infra/security_demo_monitors.sh
```

The full CI gate that runs on every push is `make ci`, which composes
`lint`, `test`, `security` (Bandit + pip-audit), `shellcheck-syntax`, and
`model-integrity` (`Makefile:1`, `Makefile:98`).

---

## 5. Honest gaps (read these before you cite us)

These are the things we know are weak. They are listed here on purpose —
credibility on a hackathon submission is built more by surfacing gaps than by
extending wins.

### 5.1 The trust list is auto-bootstrapped from the device's own public key

The `/plan/verify` HTTP path does consult the trust list (post-#105: see
§2 row 4 and `agent/orchestrator.py:420–459`), and `verify_cot` has done
the same thing for the CoT-XML mesh path since the original signer landed.
What a careful reader should still understand is **how the trust list is
populated**: it is auto-bootstrapped from the device's own public key at
two points.

- **App startup (FastAPI lifespan).** `agent/app.py:42` registers the
  `_lifespan` hook; `agent/app.py:58` calls `_bootstrap_device_trust(signer.key_id)`
  before the first request can land. This guarantees that
  `make jetson-compose-refresh` → first `/plan` → first `/plan/verify` works
  zero-friction on a fresh Jetson.
- **First sign (belt-and-suspenders).** `agent/orchestrator.py:267` (inside
  `_sign_response`) also calls `_bootstrap_device_trust` so the file exists
  even if the lifespan hook was skipped.

Both paths funnel into `agent/orchestrator.py:288 _bootstrap_device_trust` →
`crypto/cot_signer.py:532 export_public_key_to_trust_list`, which merges
the device's public key into `crypto/keys/trust_list.json`. The bootstrap
is idempotent on disk and memoized per-process via `_BOOTSTRAPPED_KEY_IDS`.

**The honest framing:** for a single-device hackathon demo this is correct
and intentional. The trust model the judge is being shown is "this Jetson
self-attests its own signing key" — a self-signed allowlist, not a chain
back to an external CA. PRD §8.2 row 4 (line 294) explicitly scopes the
trust list to "static list of allowed key IDs for the demo" and defers
CRL / shared-root distribution to post-MVP.

What this trust model does **not** defend against:

- A second TERA Jetson on the same mesh whose key was never registered
  with this device's trust list. Multi-device trust requires an enrollment
  ceremony; we have not built one.
- An adversary who has already obtained write access to the device's
  rootfs (and therefore to `crypto/keys/trust_list.json`). PRD §8.3 row 7
  treats physical compromise as "encrypt rootfs; no plaintext mission
  data at rest" for the MVP and tamper-evident enclosure post-MVP.

What it does defend against — proven by the post-#105 tests:

- An attacker producing a syntactically valid signature under a `key_id`
  this device has never seen → `Untrusted key_id - REJECTED`
  (`tests/test_orchestrator.py:626`).
- A signature whose `key_id` is in the trust list but whose payload bytes
  no longer match the rendered route → rejected at the binding stage
  (`tests/test_orchestrator.py:601`).

### 5.2 `models/MANIFEST.yml` is unsigned

The manifest itself is a plain YAML file in the repo. Anyone with write
access to the repo (or to a release artifact) can change a pinned hash and
the CI will keep passing. There is no detached signature on the manifest, no
in-toto attestation, no Sigstore artifact bundle — it's a hash list, not a
provenance chain.

PRD §8.3 row 3 post-MVP column (line 309) acknowledges this: the documented
upgrade path is "Sigstore-signed artifacts; reproducible build". For now,
trusting `MANIFEST.yml` requires trusting the repo, which means the manifest
is only as strong as the signed-commit / branch-protection posture on
GitHub.

Additionally, the runtime LLM (Gemma 2B / 3B) and Piper `.onnx` weights are
all currently `PLACEHOLDER_run_sha256sum_after_download` (`models/MANIFEST.yml`
lines 20, 25, 56, 61). Until a release engineer fills those in post-download,
the largest model artifacts are **listed but not pinned** — the manifest
catches placeholders by skipping them, not by failing.

### 5.3 The unsafe-`torch.load` AST scanner is a one-rule linter, not taint analysis

`security/model_integrity.py:101` walks the AST of every `*.py` under
`agent/`, `routing/`, `security/`, `crypto/`, `voice/`, `eval/`, `scripts/`
and flags `torch.load(...)` calls without a `weights_only` keyword. It is
roughly equivalent to Bandit's `B614` rule (`pytorch_load_save`) and the
semgrep public registry rule `python.pytorch.security.pytorch-load`.

What it does not catch:

- **Aliased imports.** `from torch import load; load("model.pt")` is not
  detected. The scanner code has a defensive branch
  `(isinstance(func, ast.Name) and func.attr == "load") if hasattr(func, "attr") else False`
  (`security/model_integrity.py:122`) but `ast.Name` does not have an `attr`
  attribute, so the `hasattr` guard always returns False and that branch is
  effectively unreachable.
- **Indirect calls.** `loader = torch.load; loader("model.pt")` is not
  detected.
- **Cross-function taint.** A wrapper function around `torch.load` would hide
  the call from the scan.

This is a competent ad-hoc lint, not a research-grade static analyzer. It is
worth running because the codebase is small enough that direct
`torch.load(...)` calls are the realistic risk surface, but it should not be
sold as anything more than that.

### 5.4 Prompt-injection defenses are layered, not bulletproof

The structured-query validator (`security/structured_query_validator.py:53`)
uses a substring blocklist of 16 phrases. Trivial paraphrases ("disregard
earlier", Unicode lookalikes, base64-encoded payloads) bypass it. The LLM is
sandboxed to JSON-only output, which is the **load-bearing** defense — the
substring list is belt-and-suspenders. SuperAgent Guard
(`security/superagent_integration.py`) adds a second layer when the API key
is set, with a regex local fallback otherwise.

The pipeline blocks the categories shown in `security/test_security_regressions.py`,
but we make no claim of comprehensive coverage against an adaptive attacker.

### 5.5 `operator_approved` and `policy_valid` are stub-true

`agent/orchestrator._run_security_pipeline` (`agent/orchestrator.py:_run_security_pipeline`)
hard-codes `operator_approved=True, policy_valid=True` for the MVP path with
an in-line comment pointing at issue #37. The two-signature approval wrapper
(ADR-003) is the real path that exercises operator approval; the
single-`/plan` path does not.

### 5.6 The Ed25519 fallback is dev-only

`crypto/ml_dsa_signer.py:183` (`FallbackSigner`) explicitly self-identifies as
"Ed25519-fallback" and "use only in development. NOT post-quantum." The
factory `create_signer` (`crypto/ml_dsa_signer.py:253`) prints a `WARNING`
banner when the fallback is selected. Production / Jetson installs must have
`liboqs-python`; the demo runbook covers this.

---

## 6. Cross-references

- PRD threat model: `docs/PRD.md` §6 (lines 75–99), §8 (lines 270–334), §9
  (lines 338–355).
- Demo recording plan and clip index: `docs/demo-recording-plan.md`.
- Issue scrub (closed by #97 and #100): `docs/issue-scrub-2026-05-03.md`
  (post-scrub appendix).
- ADRs: `docs/adrs/2026-05-02-003-two-signature-approval.md` (two-sig
  approval), planned ADR for production encrypted tunnel architecture (#70).
- Presenter beat: `docs/presentation/security-beat.md`.
