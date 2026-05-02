# ADR-003: Two-Signature Approval Flow (Device Origin + Operator Commit)

- **Date:** 2026-05-02
- **Status:** Proposed (post-Sat-1500-freeze; closes follow-up issue #42)
- **Decider:** Jon (P1) + Satriyo (P2) + Ben (P4) — pending review

## Context

The current orchestrator stubs `operator_approved=True` (issue #37). That conflates three concerns the system should keep separate:

| Concern | Question | Decided by |
|---|---|---|
| Authenticity | Did this route really come from the device, or was it spoofed? | Math (signature) |
| Correctness | Is this a route I want to take? | Operator's gut |
| Approval | Am I committing to execute this? | Operator's authority |

A signed route can be **authentic but wrong**. A correct route from a malicious device is **unsigned** (we reject). The operator must always have veto. The current single-signature model can't represent any of this clearly.

## Decision

Adopt a two-signature flow:

### Stage 1 — Device-signed plan
`POST /plan` returns a `PlanResponse` carrying the device's ML-DSA-65 signature (already implemented via `crypto.cot_signer.sign_cot`). ATAK renders the route with a **TRUSTED ORIGIN** badge but treats it as **PROVISIONAL**: it is shown but cannot be transmitted, executed, or marked as committed. Stage-1 signature proves "this came from a known device," nothing more.

### Stage 2 — Operator review (UI)
The operator looks at the rendered route and chooses one of:
- **Approve** — accepts the plan as-is.
- **Alternate** — calls `POST /plan` again with `objective=alternate_route` and `exclude=[<route_id>]`. Iterates until satisfied.
- **Edit** — drags a waypoint or adds an exclusion. Re-runs the orchestrator with the modified constraints.
- **Reject** — discards entirely; logs the rejection with reason for the audit trail.

This stage is purely UI + state. No new endpoint required.

### Stage 3 — Operator-signed commit
On Approve, the operator's app calls `POST /plan/approve` with the route id + the operator's local key. The endpoint returns an **operator-signature wrapper** that includes:

```json
{
  "route_id": "TERA-...",
  "device_signature": { ...stage-1 ML-DSA from /plan... },
  "operator_signature": {
    "scheme": "ML-DSA-65",
    "key_id": "OPERATOR-VEGA-001",
    "value_b64": "...",
    "signed_at": "2026-05-02T22:30:00Z",
    "approves_route_hash": "<sha256 of canonical route geom + waypoints>"
  }
}
```

Downstream consumers (ATAK bridge, mesh forwarder, post-mission archiver) only act on routes carrying **both signatures**.

## Consequences

### Security properties

- **Stolen device key alone:** attacker can produce signed routes that ATAK shows with TRUSTED ORIGIN, but cannot get them executed. Worst case = visual spoofing of the operator's screen, not action.
- **Stolen operator key alone:** attacker cannot generate device-signed plans (different key, different secrets) so no committed route can be fabricated end-to-end.
- **Stolen both:** game over. Mitigated by physical-possession assumption and key revocation via the trust list (`crypto/keys/trusted.json`).
- **Replay:** each operator signature includes the route's content hash, so a captured operator signature cannot be reattached to a different route.

### Implementation work (estimated)

| Component | Owner | Effort | Notes |
|---|---|---|---|
| `POST /plan/approve` endpoint | Jon | ~2 hr | New endpoint in `agent/app.py` + handler in `agent/orchestrator.py` |
| Operator key generation + storage on EUD | Satriyo | ~3 hr | Operator's Android EUD generates an ML-DSA keypair on first launch; private key in Android KeyStore |
| Approve / Reject UI | Kyle (Phase 1 web) + Ben (ATAK) | ~3 hr each | Two-button overlay; on Approve, app calls `/plan/approve` |
| ATAK gating: only forward if both sigs present | Ben | ~1 hr | Check in `atak/bridge.py` before forwarding to multicast |
| Tests | Jon + Satriyo | ~2 hr | Unit + integration; mock both signers |
| PRD §8 update + `cot_signed.md` update | Jon | ~30 min | Document the dual-signature contract |

### Trade-offs

- **Cost:** one extra round-trip per approved route (operator -> /plan/approve). Sub-second; not a concern.
- **UX:** adds a button tap. Defensible: every route the operator commits to executing should be a deliberate, conscious action. The whole point of the system is supporting operator decisions, not bypassing them.
- **Scope:** this displaces the stubbed `operator_approved=True` in the security pipeline call. Pipeline `context.operator_approved` becomes `True` only when an operator-signed commit is on file for that route id.

### What this DOES NOT solve

- A coerced operator (gun-to-head). Two signatures cannot help; physical-possession is the assumption boundary.
- An LLM that "lies" inside the structured query (covered by `structured_query_validator` + `pipeline.run_pipeline`'s policy gate, not by signing).
- Long-running missions where the operator approves once but executes hours later. Out of scope; could add signature TTL or per-leg re-approval if needed.

## Follow-ups

- Closes #37 (operator-approval flow stubbed) once implemented.
- Touches #34 (signature contract reconciliation) — reconcile field naming as part of this PR.
- Update PRD §8 threat-model table to include the operator-signed commit row.
- Consider extending `cot_signed.md` to describe the wrapper shape.
