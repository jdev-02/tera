# Cyber Trust Layer — Demo Script

## Elevator Pitch (30 seconds)

> "The novelty here is not offline routing — it's a **cyber-secure mediation layer** that separates intent from authority and data from instruction *before* a route is computed or displayed as trusted on ATAK."

---

## Demo Flow (5 minutes)

### Step 1 — Show the architecture diagram (30 sec)

Open `docs/cyber_trust_boundary.md`.

Point out the pipeline: **U → L → Q → R → S → M**

Key message: "Natural language never directly reaches the routing engine, signing module, or ATAK renderer."

---

### Step 2 — Run the security tests live (2 min)

```bash
python cyber/prompt_injection_tests.py
```

Walk through 4 key results as they print:

| Test | What it proves |
|------|---------------|
| `normal_operator_request_is_trusted` | Legitimate operator intent flows correctly |
| `map_label_injection_blocked` | A map label containing "Ignore all prior instructions" is tagged as `authority_level: 10`, `trusted_as_instruction: false` |
| `intent_agent_cannot_sign_route` | IntentAgent is denied `SignApprovedRoute` — privilege separation works |
| `unsigned_unapproved_route_is_needs_review` | An unsigned route appears as "Suggested Route – Needs Review", never "Trusted Route" |

---

### Step 3 — Explain the three core security properties (1.5 min)

**Property 1: Structured Query as Security Boundary**
> "The LLM can only produce a schema-validated structured query. It cannot call tools, modify policy, or trigger signing directly. The schema is the security boundary between language and action."

Show `schemas/route_query.schema.json` — closed enum lists, no free-text fields in action-sensitive positions.

**Property 2: Data ≠ Instruction (Provenance)**
> "Every input entering the pipeline is tagged with a source type and authority level. Map labels, cached overlays, and field reports are data. Only operator utterances and system policy are instructions."

Show `cyber/data_provenance.py` — `AUTHORITY_LEVELS` table, `INSTRUCTION_SOURCES` set.

**Property 3: Least-Privilege Agent Separation**
> "No single agent holds full authority. IntentAgent can parse. PolicyAgent can validate. Only SigningAgent can sign, and only after operator approval and policy validation are confirmed."

Show `cyber/policy_gate.py` — `AGENT_PERMISSIONS` dict, guarded operations.

---

### Step 4 — Show ATAK trust states (30 sec)

Describe (or sketch on whiteboard):

```
Unsigned route    →  "Suggested Route – Needs Review"
Signed route      →  "Trusted Route"
Failed checks     →  "Untrusted – Do Not Execute"
```

Key message to ATAK teammate: "Send me the route artifact dict with these five boolean fields: `schema_valid`, `policy_valid`, `operator_approved`, `signature_valid`, `untrusted_inputs_used`. I'll return trust score + ATAK display label."

---

## Handoff to Teammates

```
My deliverables are complete.

docs/cyber_trust_boundary.md      — trust contract for the whole team
schemas/route_query.schema.json   — LLM output schema (security boundary)
cyber/structured_query_validator.py
cyber/policy_gate.py
cyber/data_provenance.py
cyber/route_trust_score.py
cyber/prompt_injection_tests.py   — 10 tests, all PASS

Integration points:
- Route agent: validate your LLM output against route_query.schema.json,
  then call validate_route_query() before sending to routing engine.
- ATAK/map layer: call compute_route_trust(artifact) to get trust_status
  and use atak_label() for the map display string.
- Signing module: call allow("SigningAgent", "SignApprovedRoute", context)
  before executing any signing operation.
```
