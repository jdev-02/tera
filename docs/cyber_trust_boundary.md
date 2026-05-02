# Cyber Trust Boundary

## Core Principles

1. Intent is not authority.
2. Data is not instruction.

Natural-language input from the operator, map labels, cached overlays, prior route notes, and local files are treated as untrusted input until validated.

The LLM is not allowed to directly command the routing engine, signing module, or ATAK rendering layer.

## Secure Pipeline

```
U → [G] → [X] → L → Q → R → S → M
```

Where:

- U   = user utterance or typed intent
- [G] = SuperAgent Guard (prompt injection detection)
- [X] = SuperAgent Redact (PII / secret stripping)
- L   = local language interpretation + provenance tagging
- Q   = structured geospatial query (schema-validated)
- R   = local routing engine
- S   = signing / trust module
- M   = tactical map rendering layer (ATAK)

## Forbidden Direct Paths

- U must not directly access R
- U must not directly access S
- U must not directly access M
- U must pass [G] and [X] before reaching L

## Security Boundary

Natural language can only influence the route system after it:
1. Passes SuperAgent Guard (no injection detected)
2. Has PII and secrets redacted by SuperAgent Redact
3. Is provenance-tagged as a trusted instruction source
4. Becomes a schema-valid, policy-authorized structured query

## SuperAgent Integration

| Component        | Role in pipeline                                      | Fallback (offline)        |
|------------------|------------------------------------------------------|---------------------------|
| Guard (`guard()`) | Classifies input as `pass` or `block` with reasoning + CWE codes | Local regex heuristic     |
| Redact (`redact()`) | Strips PII, PHI, secrets; replaces with `<TYPE_REDACTED>` | Local regex redaction     |

SuperAgent is the **outermost gate** — nothing enters the local pipeline unless Guard returns `pass`.
If `SUPERAGENT_API_KEY` is not set, the pipeline degrades gracefully to local heuristics without breaking.

## Agent Authority Model

No single agent holds full authority. Each agent is scoped:

| Agent          | Permitted Operations                              |
|----------------|---------------------------------------------------|
| IntentAgent    | ParseIntent                                       |
| PolicyAgent    | ValidateQuery, ApprovePolicy                      |
| GeoQueryAgent  | ReadTerrain, ReadTrails, ReadHydrography, BuildGeoQuery |
| RoutingAgent   | ComputeRoute                                      |
| SigningAgent   | SignApprovedRoute                                 |
| RenderingAgent | RenderVerifiedRoute, RenderSuggestedRoute         |

## Route Trust States

| Trust Status  | Condition                                    | ATAK Display              |
|---------------|----------------------------------------------|---------------------------|
| trusted       | score >= 80 (all checks pass)                | Trusted Route             |
| needs_review  | score 50–79 (approval or signature missing)  | Suggested Route – Needs Review |
| untrusted     | score < 50 (multiple failures)               | Untrusted – Do Not Execute |

## Data Provenance Authority Levels

| Source Type      | Authority Level | Trusted as Instruction |
|------------------|-----------------|------------------------|
| system-policy    | 100             | Yes                    |
| operator-intent  | 80              | Yes                    |
| signed-route     | 75              | No                     |
| routing-result   | 60              | No                     |
| field-report     | 40              | No                     |
| cached-overlay   | 25              | No                     |
| map-label        | 10              | No                     |
| unknown-source   | 0               | No                     |

Map labels, cached overlays, and field reports are **data**, not instructions. Even if they contain imperative text, they cannot instruct the routing, signing, or rendering subsystems.
