# ADR-001: Adopt PRD v0.5 Decisions Wholesale

- **Date:** 2026-05-02
- **Status:** Accepted
- **Decider:** Full team (kickoff vote)

## Context

The PRD (`/docs/PRD.md`) was authored pre-kickoff and went through five iterative refinement rounds. It locks in product, architecture, security posture, lane split, CI/CD, and demo plan. We need an explicit ADR so the decisions are first-class repo artifacts and not just documentation.

## Decision

We adopt PRD v0.5 wholesale as the binding plan for the hackathon, including:

- **Primary problem statement:** PS2 (Edge Deployments). Secondary: PS3. Tertiary: PS4 via PQC-signed CoT.
- **Phased build:** P1 web MVP → P2 Jetson + frontier API → P3 Jetson + local Gemma + WiFi off (HERO) → stretch mesh.
- **Demo construct:** dual-modality (SF Ferry Building → austere AO flip), voice input (Whisper-tiny), both ATAK targets (Android EUD + WinTAK), PQC-signed CoT as the security beat.
- **Lane split:** see PRD §13 and `CODEOWNERS`.
- **Five non-negotiables:** see `AGENTS.md` §10.
- **Kickoff plan:** 30-min contract-lock + 4 parallel lanes, per PRD §13.1.

Items voted at kickoff (codename, austere AO, hero scenario, OSM extract size, ollama vs llama.cpp, Palantir AIP yes/no, Danti yes/no, kepler.gl vs Leaflet) get their own ADRs as decided.

## Consequences

- The PRD is binding; deviations require a superseding ADR.
- All AI agents (Codex, Cursor, etc.) read the PRD via `AGENTS.md` and `/.agents/10-architecture.md` references.
- Cross-cutting changes that touch the architecture or threat model must update the PRD via PR.
- Post-hackathon, the PRD becomes the basis for the SBIR / xTech follow-on submission.
