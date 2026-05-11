# TERA Trust Shield

TERA Trust Shield is a disaster fraud and misinformation protection layer for emergency coordination. It is not a general anti-scam platform. Its job is to keep unverified crisis-related information from automatically changing emergency operations.

## Why Disaster Fraud Matters

During disasters, responders and victims may receive fake donation links, fake FEMA or county portals, phishing links, false shelter instructions, fraudulent supply requests, impersonated responder messages, malicious QR codes, and suspicious field reports. These can divert resources, steal credentials, or create unsafe dispatch decisions.

## Scope

Trust Shield answers:

- Can this crisis-related link be trusted?
- Is this supply request suspicious or unverified?
- Is this shelter claim in the verified shelter list?
- Does this evacuation instruction conflict with official alert context?
- Should a field report require human approval before dispatch?

It does not identify people, accuse individuals, perform takedowns, or report targets.

## Supported Checks

- URL heuristics: shorteners, non-HTTPS, punycode, IP literals, excessive subdomains, suspicious TLDs, embedded credentials, crisis keywords, and official-source impersonation.
- Google Safe Browsing: malware, social engineering, unwanted software, and potentially harmful application matches.
- VirusTotal: optional URL/domain reputation.
- urlscan.io: optional explicit scan submission with `unlisted` visibility.
- RDAP: public domain metadata where available.
- Misinformation tools: unverified shelter claims, unverified evacuation instructions, and conflicting field reports.

## Environment Variables

- `GOOGLE_SAFE_BROWSING_API_KEY`
- `VT_API_KEY`
- `URLSCAN_API_KEY`
- `TERA_TRUST_OFFICIAL_DOMAINS` optional comma-separated allowlist override

`GET /trust/api-status` reports only true/false. It never exposes secret values.

## Example

```bash
curl -s -X POST http://localhost:8000/trust/check-url \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://fema-aid-claim-example.com/login","context":"wildfire relief claim link"}' | jq .
```

Expected behavior:

- possible FEMA impersonation is flagged
- missing threat-intel keys are shown as skipped, not fatal
- risk language stays careful
- human approval is required before mission planning can use the claim

## Human-in-the-loop Safety

TERA recommends. A human commander approves. Signed mission plans can then be verified by field clients. Suspicious or unverified external claims remain isolated until approved.

## Limitations

- Heuristics are not proof of fraud.
- RDAP data is inconsistent across registries.
- Google Safe Browsing, VirusTotal, and urlscan require network access and keys.
- urlscan submission may consume quota and load the target page, so it is explicit only.
- Trust Shield should use phrases like "possible phishing", "unverified source", and "requires approval" unless a provider directly confirms a malicious match.

## Privacy and Security Notes

Do not submit sensitive victim data, private field reports, or internal responder URLs to third-party services without approval. For offline operations, run heuristic checks only and preserve the human approval boundary.
