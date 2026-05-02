# Novel Cyber-Mitigation Contribution

## Thesis

TERA is not novel because it computes an offline route. Offline routing, local
geospatial search, and tactical map rendering already exist.

The novel contribution is a cyber-secure cognitive control architecture for a
natural-language tactical route agent: spoken or typed intent may guide route
optimization, but natural language, map data, cached context, and adversarial
annotations cannot become unauthorized executable instruction.

In short:

```text
Intent != Authority
Data != Instruction
```

## Product-Specific Risk

TERA places a language model between an operator and mission-critical
geospatial functions. That creates a new cyber risk surface: the model must
interpret ambiguous human intent, but it must not become an uncontrolled command
interpreter.

Untrusted instructions may arrive through:

- spoken or typed prompts
- copied mission notes
- hostile map labels
- manipulated route metadata
- corrupted geospatial overlays
- adversarial text embedded in local files
- compromised prior session context
- malformed route requests
- spoofed agent outputs

The central failure mode is prompt injection crossing a mission boundary. A
successful attack could cause the system to ignore constraints, alter route
objectives, prefer unsafe terrain, fabricate confidence, bypass authorization,
sign an untrusted route, or render a route as trusted when it is not.

## Secure Route-Control Pipeline

TERA's route flow is:

```text
U -> L -> Q -> G -> R -> S -> M
```

Where:

- `U` is the operator utterance or typed request
- `L` is local language interpretation
- `Q` is the structured geospatial query
- `G` is the security gate: prompt guard, provenance, schema, policy, trust
- `R` is the local route engine
- `S` is the signing and approval layer
- `M` is the tactical map rendering layer

The important property is that the natural-language input is never direct:

```text
U !-> R
U !-> S
U !-> M
```

Natural language can only influence routing after it becomes a schema-valid,
policy-authorized, provenance-tagged query.

## Architecture Mapping

| Concept | Product implementation | Repo artifact |
|---|---|---|
| Perceptual input is not command authority | Raw prompts are guarded, redacted, tagged, and converted into structured query objects before routing | `security/plan_guard.py`, `security/superagent_integration.py` |
| Data is not instruction | Map labels, cached overlays, field reports, routing results, and signed routes retain source type and authority level | `security/data_provenance.py` |
| Structured query is the security boundary | LLM output must satisfy closed enums, bounded distances, allowed layers, and authority context | `docs/route_query.schema.json`, `security/structured_query_validator.py` |
| Zero-trust agent orchestration | Intent, policy, geospatial query, routing, signing, and rendering have separate permissions | `security/policy_gate.py` |
| Route trust is explicit | A route is `trusted`, `needs_review`, or `untrusted` based on schema, policy, approval, signature, and input provenance | `security/route_trust_score.py` |
| Device origin is cryptographic | Device-signed route artifacts prove known-device origin | `crypto/ml_dsa_signer.py`, `crypto/cot_signer.py` |
| Operator approval is separate authority | `/plan` creates a provisional route; `/plan/approve` commits it with an operator signature over the route hash | `agent/app.py`, `agent/orchestrator.py`, `docs/adrs/2026-05-02-003-two-signature-approval.md` |
| Offline resilience | Guard fallback, local routing, local signing, and no-outbound proof run without cloud dependency | `security/demo_proofs.md`, `infra/tcpdump_demo.sh` |

## Security Invariants

TERA preserves these invariants:

1. The LLM cannot directly call the routing engine.
2. The LLM cannot sign a route.
3. The routing engine cannot approve its own output.
4. The rendering layer cannot upgrade an untrusted route to trusted.
5. A map label is always data, even if it contains imperative text.
6. Device signature proves origin, not operator commitment.
7. Operator approval signs the route hash, preventing signature reuse on a
   different route.
8. Unsigned, unapproved, or low-provenance routes are downgraded or rejected.

## Route Artifact Model

A route is not just geometry:

```text
A_p = (p, Q, D, Pi, ID_u, ID_a, tau)
```

Where:

- `p` is route geometry
- `Q` is the structured query
- `D` is the local data used
- `Pi` is the policy set applied
- `ID_u` is the operator or device-local authority
- `ID_a` is the agent identity chain
- `tau` is the timestamp or local event marker

The signed route is:

```text
sigma = Sign_sk(H(A_p))
```

The map should render a route as trusted only when verification and approval
match the route artifact being displayed.

## Demo Proofs

| Proof | What the judge sees | Security claim |
|---|---|---|
| Prompt injection block | A hostile prompt or map label is blocked before routing | Data is not instruction |
| Schema boundary | Invalid fields such as `transmit_data` or invalid route enums are rejected | LLM output is not arbitrary command execution |
| Policy gate | `IntentAgent` cannot perform `SignApprovedRoute` | Intent is not authority |
| Trust downgrade | Unsigned or unapproved route returns `needs_review` | Device output is not operator commitment |
| Two-signature commit | `/plan/approve` signs the route hash with an operator key | Commitment is explicit and replay-resistant |
| CoT verification | Unsigned or tampered CoT fails verification | Tactical rendering is provenance-bound |
| No outbound traffic | `tcpdump` shows no egress during local route generation | Security controls work offline |

## Paper-Ready Contribution Statement

This work contributes a defense-in-depth cyber mitigation architecture for
offline natural-language tactical route agents. The system separates user
intent from execution authority by transforming spoken or typed requests into
schema-bound, provenance-tagged, policy-validated geospatial queries before any
route computation occurs. It applies control gating, context-aware provenance,
zero-trust agent orchestration, persona-bound identity, ephemeral route-session
isolation, and cryptographic route signing to a mission-critical routing
workflow. As a result, prompt injection, corrupted geospatial annotations,
compromised local context, or unauthorized agent behavior cannot directly alter
route computation, signing, or trusted map rendering.

## One-Sentence Claim

TERA contributes a cyber-secure cognitive control architecture for offline
natural-language tactical route agents, ensuring that operator intent can guide
route optimization without allowing natural language, map data, or adversarial
context to become unauthorized executable instruction.
