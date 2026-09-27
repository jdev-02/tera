# TERA v2 PRD: Emergency Logistics and Disaster Coordination

## Product Vision

TERA helps emergency teams coordinate disaster response with degraded connectivity. It converts natural-language operational intent into an explainable logistics plan that combines hazards, infrastructure, routes, vehicles, resources, shelter needs, and trust checks.

## Target Users

- county emergency operations centers
- field response teams
- shelter coordinators
- logistics officers
- humanitarian relief coordinators
- volunteer coordinators who need verified instructions

## Core Workflows

1. Operator describes the mission: "Route water and N95 masks to the safest available shelter."
2. TERA gathers live or cached context: weather alerts, fire perimeter, AQI, hospitals, shelters, road events, and infrastructure.
3. TERA scores shelter needs and route risks.
4. TERA runs deterministic offline allocation, or Google Route Optimization when available.
5. TERA Trust Shield checks external links, field reports, shelter claims, and supply requests.
6. TERA explains what it recommends, what it blocked, and what requires human approval.
7. Approved plans can be signed and verified by field clients.

## Non-goals

- General anti-scam platform.
- Replacement for official evacuation orders.
- Automated takedown, spam reporting, attribution, or law-enforcement action.
- Cloud-only operations.
- Removing the legacy tactical/ATAK architecture.

## Success Metrics

- Mission plan produced with no external API keys.
- Live API enrichment works when keys are present.
- Suspicious crisis links and unverified supply requests do not modify dispatch automatically.
- Operator receives a concise explanation and approval boundary.
- Legacy `/plan`, `/plan/approve`, and `/plan/verify` remain compatible.

## Judging Relevance

TERA demonstrates practical Google technology use while solving a humanitarian problem:

- Gemini for multimodal emergency reasoning and explanation.
- Gemma for offline fallback.
- Google Maps Routes for route candidates.
- Google Route Optimization for fleet/resource dispatch.
- Firebase for offline-first shared mission state.
- Google Safe Browsing for crisis-link protection.

## Security and Offline-first Rationale

Emergency response is vulnerable to degraded networks and hostile or fraudulent information. TERA treats external links, field reports, and unverified supply requests as untrusted until assessed and approved. Offline fallback is not a downgrade; it is the default safety posture.
