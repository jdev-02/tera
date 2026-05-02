# Signed CoT Contract v0.1

> Co-owned by P2 (crypto lane) and P4 (atak lane). Changes require both sign-off.
> See PRD §8 for the threat model. See `/.agents/24-security.md` for the implementation guide.

## What is being signed

We sign the **full CoT XML message** (canonicalized) with ML-DSA-65. The signature is attached as a child of `<detail>`.

## XML shape

```xml
<event version="2.0" uid="WAYFINDER-2026-05-02-0001"
       type="b-m-r" how="m-g"
       time="2026-05-02T19:30:00Z"
       start="2026-05-02T19:30:00Z"
       stale="2026-05-02T20:30:00Z">
  <point lat="37.7955" lon="-122.3937" hae="9999999.0" ce="9999999.0" le="9999999.0"/>
  <detail>
    <link uid="..." type="..." relation="..."/>
    <route>
      <!-- route geometry as a polyline / waypoint list -->
    </route>
    <signature
      scheme="ML-DSA-65"
      key_id="WF-DEV-0001"
      signed_at="2026-05-02T19:30:00Z"
      canonicalization="c14n11"
      value_b64="<base64 ML-DSA-65 signature, ~3.3KB>"
    />
  </detail>
</event>
```

## Canonicalization

Before signing or verifying:
1. Strip the `<signature>` child from `<detail>` (if present).
2. Apply XML C14N 1.1 (Canonical XML 1.1).
3. UTF-8 encode the canonicalized bytes.
4. Sign / verify those bytes.

This makes the signature stable across whitespace and attribute-order changes that don't affect semantics.

## Signing flow (emit side)

```python
from crypto.signer import Signer  # P2's lib

signer = Signer.load(key_id="WF-DEV-0001")
canonical_bytes = canonicalize(event_xml)  # strip <signature>, c14n11
sig = signer.sign(canonical_bytes)  # returns bytes (~3.3KB)
event_xml = inject_signature(event_xml, sig, key_id=signer.key_id, scheme="ML-DSA-65")
multicast.emit(event_xml)
```

## Verification flow (ingress side)

```python
from crypto.signer import Verifier
from security.parse_verify import verify_cot_structure  # Jon's paper layer

verifier = Verifier.from_trust_list("./crypto/keys/trusted.json")

# Step 1: structural / parsing verification (rejects malformed or anomalous CoT)
ok, reasons = verify_cot_structure(event_xml)
if not ok:
    log.warn("cot_rejected_structure", reasons=reasons)
    return

# Step 2: extract signature, canonicalize, verify
sig = extract_signature(event_xml)
if sig is None:
    log.warn("cot_rejected_unsigned")
    return

canonical_bytes = canonicalize(event_xml)  # strip <signature>, c14n11
if not verifier.verify(canonical_bytes, sig):
    log.warn("cot_rejected_bad_signature", key_id=sig.key_id)
    return

# Step 3: timestamp drift check (replay protection)
if abs(now() - sig.signed_at) > 60:
    log.warn("cot_rejected_timestamp_drift")
    return

forward_to_atak(event_xml)
```

## Trust list format (`crypto/keys/trusted.json`)

```json
{
  "version": 1,
  "updated": "2026-05-02T11:45:00Z",
  "keys": [
    {
      "key_id": "WF-DEV-0001",
      "scheme": "ML-DSA-65",
      "public_key_b64": "...",
      "owner": "Jetson-prototype-A",
      "valid_until": "2026-12-31T23:59:59Z"
    }
  ]
}
```

## Performance budget

- Sign: < 5 ms per CoT message on Jetson Orin Nano.
- Verify: < 5 ms per CoT message on Jetson Orin Nano.
- Total budget for sign + multicast emit: < 20 ms.

## Open items (P2 + P4)

- [ ] Decide whether route geometry inside `<route>` is an inline polyline string or a child element with per-point children.
- [ ] Confirm CoT type code: `b-m-r` (route) is the natural pick; verify ATAK draws it as a line.
- [ ] Decide on key rotation cadence (out of scope for hackathon; document for post-MVP).
- [ ] Decide on stretch ML-KEM peer encryption: which fields are encrypted vs. which are signed-only.
