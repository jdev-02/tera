# CoT Signature Wrapper v0

Owner pair: P2 and P4.

Status: freeze candidate for Sat 1500.

## MVP Rule

TERA emits unsigned CoT only in local developer mode. Demo mode requires each route CoT payload to carry a `tera_signature` detail block before ATAK ingest.

## Detail Block

```xml
<detail>
  <tera_signature
      alg="ML-DSA-65"
      key_id="tera-demo-key-01"
      signed_at="2026-05-02T19:00:00Z"
      fields="uid,type,time,point,route,rationale"
      sig_b64="BASE64_SIGNATURE" />
</detail>
```

## Verification Behavior

- Accept when `key_id` exists in the P2 trust list and signature verifies over the canonical field bundle.
- Reject when signature is missing, malformed, expired, or not trusted.
- Log every accept/reject event as structured JSON for the demo audit window.

## ATAK Handoff

P4 bridge forwards accepted CoT to ATAK internal/external dispatch. The ATAK SDK platformsim sample demonstrates dispatching parsed CoT through `CotMapComponent` dispatchers.
