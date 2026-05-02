# 24 — Security / Crypto / Infra / CI Lane (P2 — Satriyo, Indonesian Navy, cybersecurity)

> Owns: `/security/`, `/crypto/`, `/infra/`, `/.github/`, `/.agents/` (file maintenance). Pairs with P3 on Jetson hardening, P4 on signer integration.

## What this lane delivers

1. **ML-DSA (Dilithium) signer + verifier** library, used by `/atak/` to sign every CoT field.
2. **Threat model document** + the live demo proof points (`tcpdump`, hash-verify, audit log).
3. **Jetson hardening** — egress firewall, signed model artifacts, SBOM.
4. **CI/CD pipeline** — `make ci`, `lefthook`, branch protection, AI PR review.
5. **Intrinsic parsing-verification layer** (per Jon's paper, see `/docs/papers/`).
6. **CODEOWNERS enforcement + repo hygiene.**

## Entry points

- `make ci` — the gate. Runs lint, type, test, security scans.
- `make security` — bandit + pip-audit + gitleaks.
- `make sign-bench` — micro-bench ML-DSA sign/verify roundtrip on Jetson.
- `make tcpdump-demo` — starts a `tcpdump` window for the demo proof.

## Stack

- **`liboqs-python` 0.10.0** for ML-DSA-65 sign/verify (and ML-KEM-768 for stretch encryption).
- **`cryptography`** for AES-256-GCM (stretch peer encryption).
- **`bandit`** Python security linter.
- **`pip-audit`** dependency vuln scan.
- **`gitleaks`** secret detection (in lefthook + CI).
- **`lefthook`** for git hooks.
- **`uv` or `pip-tools`** for deterministic deps (`uv` if available; saves time).

## File layout

```
crypto/
  __init__.py
  signer.py          # ML-DSA-65 signer (sign / verify)
  kem.py             # ML-KEM-768 (stretch)
  trust.py           # static trust list loader
  keys/              # NOT committed. Keys are generated at first boot.
  README.md
security/
  threat_model.md    # live document, updated as we add mitigations
  demo_proofs.md     # pre-flight checklist for the demo security beat
  parse_verify.py    # intrinsic parsing-verification per Jon's paper
infra/
  jetson_harden.sh   # systemd lockdown, egress firewall, sysctl
  egress.iptables    # default-deny outbound for Phase 3
  README.md
.github/
  workflows/
    ci.yml
  pull_request_template.md
  CODEOWNERS         # actually lives at root, but P2 maintains
```

## Contracts you OWN

- `/docs/contracts/cot_signed.md` — co-owned with P4. Format of the signature wrapper on CoT.
- `Makefile`, `lefthook.yml`, `pyproject.toml`, `.github/workflows/ci.yml`.

## Contracts you MUST respect

- The `/plan` response signature object format from `/.agents/10-architecture.md`.

## Threat model — featured

**TAK track injection** is the headline threat. CoT messages are unauthenticated by default. We sign every CoT field with ML-DSA-65; ATAK Bridge verifies on ingress.

The flow:
1. On first boot, generate ML-DSA-65 keypair; persist `keys/identity.priv` (mode 0600) and `keys/identity.pub`.
2. Maintain a `keys/trusted.json` listing allowed key IDs (flat file is fine for the demo).
3. `signer.sign(payload)` returns `{scheme, key_id, value_b64, signed_at}`.
4. `signer.verify(payload, signature)` returns bool; verifier rejects on any failure (signature mismatch, key not in trust list, timestamp drift > 60s).

## Intrinsic parsing-verification (per Jon's paper)

Read the paper before implementing. Core idea: structurally validate inputs (OSM tags, tool-call args, prompt text) against grammars/schemas and reject anomalies before they reach downstream tools.

Apply to:
- OSM PBF tags: anomalous tag combinations rejected at load.
- Tool-call args: schema validation (already in `/agent/` lane via JSON schema).
- LLM-generated rationale: token-set whitelist (no URLs, no MGRS for non-AOI grids).

## Common gotchas

1. **`liboqs-python` requires `liboqs` system lib.** Install `liboqs` first (`brew install liboqs` on macOS dev; `apt install liboqs-dev` on Ubuntu/Jetson). Pin both versions.
2. **ML-DSA signature is large (~3.3KB).** Don't embed it as a CoT attribute string — use a child element with base64 + line wrapping.
3. **Trust list management is the unsexy hard part.** For the demo, ship a static trust list. Document the CRL/distribution path in the threat model as future work.
4. **Egress firewall must allow loopback + multicast (239.2.3.1).** Default-deny is fine for Phase 3; just open these.
5. **gitleaks pre-commit can flag false positives** (e.g., your structured-log examples). Use `# gitleaks:allow` comment to override on a case-by-case basis, never globally disable.

## Definition of done for this lane

- `make sign-bench` reports sign + verify < 5ms per call.
- `make ci` includes bandit + pip-audit + gitleaks; fails the build on HIGH findings.
- `lefthook` blocks pushes that fail `make ci`.
- ATAK Bridge integration tested: signed CoT accepted, unsigned CoT rejected.
- Threat model doc is presentable as a 1-page handout.
- `tcpdump` capture during P3 demo shows zero outbound packets.
