# P2 Security Demo Proofs

This document is the P2 runbook for proving the cyber trust boundary during
the TERA hackathon demo.

## What P2 Proves

P2 owns the security claim that natural language, map text, compromised local
context, and unsigned CoT messages cannot become trusted route authority.
The paper/pitch framing lives in `docs/cyber_mitigation_contribution.md`.

The demo should prove four things:

1. Prompt injection is blocked before routing.
2. Structured route queries are schema-validated before execution.
3. Unsigned or tampered CoT envelopes are rejected.
4. Offline mode produces no outbound network traffic.
5. Device-signed routes remain provisional until `/plan/approve` returns an
   operator signature over the same route hash.

## Preflight

From the repository root:

```powershell
python -m pytest security crypto -q
python security\pipeline.py
python crypto\cot_signer.py
```

Expected result:

```text
security/crypto tests: passed
pipeline.py: normal request PASS, injection attempts BLOCK
cot_signer.py: signed route VALID, unsigned CoT REJECTED, tampered CoT REJECTED
```

If `SUPERAGENT_API_KEY` is set, `security\pipeline.py` should report live
SuperAgent API mode. If not set, it should report local heuristic mode. Both
are acceptable for the hackathon; local heuristic mode is required for WiFi-off
Phase 3.

## Proof 1: Prompt Injection Rejected

Command:

```powershell
python security\pipeline.py
```

Observed expected scenario:

```text
SCENARIO: Map label prompt injection attempt
Overall: [BLOCK]
ATAK: BLOCKED - Prompt Injection Detected
```

Security interpretation:

Map labels and cached local text are treated as untrusted data, not executable
operator intent. This preserves the boundary:

```text
Data != Instruction
```

## Proof 2: Structured Query Boundary

Command:

```powershell
python -m pytest security\test_security_regressions.py -q
```

Expected result:

```text
5 passed
```

Security interpretation:

The route engine only receives schema-valid, policy-valid query objects.
Unexpected fields such as `unexpected_tool=transmit_data` and invalid enum
values are rejected before route computation.

## Proof 3: Signed CoT Accepted, Unsigned/Tampered CoT Rejected

Command:

```powershell
python crypto\cot_signer.py
```

Expected result:

```text
Embed + Verify (should be VALID)
valid=True

Unsigned CoT (should be REJECTED)
valid=False

Tampered CoT envelope (should be REJECTED)
valid=False
```

Security interpretation:

The verifier binds the signed payload to the rendered CoT envelope. An attacker
cannot keep the signed payload intact while changing the outer route metadata
or point coordinates and still have ATAK treat the route as trusted.

## Proof 4: Offline / No-Outbound Traffic

On Jetson or Linux demo hardware, run this in a second terminal before the
`/plan` demo:

```bash
sudo bash infra/jetson_firewall.sh enable
sudo bash infra/tcpdump_demo.sh any
```

Then run the plan request from the demo terminal.

Expected result:

```text
[OK] No outbound packets.
```

Security interpretation:

In Phase 3, the agent must not call frontier APIs or external map services.
The demo should show route planning while WiFi is disabled or outbound egress
is blocked.

Restore connectivity after the demo:

```bash
sudo bash infra/jetson_firewall.sh disable
```

## Stage Script

Short version for the pitch:

```text
This is the cyber layer. First, a prompt injection is blocked before it can
become a route command. Second, malformed route queries fail schema validation.
Third, unsigned and tampered CoT routes are rejected. Finally, tcpdump shows no
outbound packets while the route is generated locally.
```

One-sentence claim:

```text
TERA does not merely compute a route; it proves whether the route is authorized,
provenance-bound, and safe to render as trusted.
```

Paper-ready claim:

```text
TERA contributes a cyber-secure cognitive control architecture for offline
natural-language tactical route agents: intent can guide route optimization,
but natural language, map data, and adversarial context cannot become
unauthorized executable instruction.
```

## PR Checklist

Before merging P2 changes:

```text
[ ] python -m pytest security crypto -q
[ ] python security\pipeline.py
[ ] python crypto\cot_signer.py
[ ] No real API keys committed
[ ] If touching /plan integration, guard runs before routing/signing
```
