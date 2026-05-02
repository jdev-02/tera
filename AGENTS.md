# AGENTS.md — Agent Operating Guide

> **Read this file before every task.** It is the contract for AI coding agents (Codex, Cursor, Claude Code, Copilot) and the humans who steer them on this project.
>
> If you are an AI agent: read this file in full, then read `/.agents/10-architecture.md`, then the lane file for the directory you are editing (`/.agents/2X-<lane>.md`), then the relevant contract under `/docs/contracts/`. Only then begin work.

---

## 1. What we are building

A pocket-sized, fully-offline AI agent that turns natural language ("plot a covered route to the nearest freshwater within 5km") into trustworthy tactical routes inside ATAK, on a Jetson Orin Nano, with no cloud and no outbound packets.

- **Hackathon:** 3rd Annual National Security Hackathon (Cerebral Valley × US Army xTech), May 2-3, 2026, San Francisco.
- **Build window:** Sat 1145 → Sun 1200 (~24 hours).
- **Source of truth for the product:** [`/docs/PRD.md`](docs/PRD.md) — read sections §1, §4, §6, §7, §8, §13, §14 before any non-trivial change.
- **Primary problem statement:** PS2 (Edge Deployments). Secondary: PS3 (Mission C2). Tertiary: PS4 (Cyber, via PQC-signed CoT).

## 2. Hard rules — never violate

These are mechanical / legal / pitch-survival concerns. The integrator will revert any commit that breaks these.

1. **Never commit secrets.** No API keys, tokens, model weights, or `.env` files. `.gitignore` blocks the obvious ones; `gitleaks` runs in CI; `lefthook` runs `gitleaks` pre-commit.
2. **Never bypass `make ci`.** `lefthook` enforces `make ci` pre-push. Branch protection on `main` has an empty bypass list. If `make ci` is wrong, fix `make ci` — don't sidestep it.
3. **Never edit a directory you don't own.** See `CODEOWNERS` and PRD §13.2. Cross-cutting changes go through paired sign-off (PRD §13).
4. **Never make outbound network calls in Phase 3 code.** The hero demo runs with WiFi off. Any `requests`, `httpx`, `urllib` call in `/agent/`, `/routing/`, `/atak/`, or `/voice/` for the Phase 3 path will break the demo and the security claim simultaneously.
5. **Never let the LLM emit a tool call without JSON-schema validation.** Tool-call args are validated against `/docs/contracts/agent_routing.schema.json` before they hit any geospatial tool. If the schema is wrong, fix the schema; don't loosen the validator.
6. **Never write code without a corresponding GitHub issue.** Pull from the board (`TASKS.md` is the seed). One issue → one branch → one PR.
7. **Never push directly to `main`.** Branch, PR, AI review, merge. Empty bypass list applies to everyone, integrator included.

## 3. Read-before-edit protocol (for AI agents)

Before generating any code change, the agent must:

1. Read this file (`AGENTS.md`).
2. Read `/.agents/10-architecture.md`.
3. Read the lane file for the directory you are editing: `/.agents/2X-<lane>.md`.
4. Read the relevant contract under `/docs/contracts/` if you are touching the agent ↔ routing path or the CoT bridge.
5. Read at least one existing file in the target directory to match conventions.
6. Read the GitHub issue for this task (acceptance criteria are non-negotiable).

If any of those files don't exist or don't apply, say so in the PR description and proceed with documented assumptions — but do not skip steps 1, 2, and 6.

## 4. Workflow per task

```
┌────────────────────────────────────────────────────────────────────┐
│  1. PICK an issue from the GitHub board labeled with your lane     │
│  2. CHECK OUT a feature branch: <name>/<short-desc>                │
│     (e.g., jon/agent-tool-find-pois)                               │
│  3. CODE the smallest change that satisfies acceptance criteria    │
│  4. RUN `make ci` locally (lefthook will block push if it fails)   │
│  5. COMMIT with conventional-commit message:                       │
│        feat(agent): add find_pois tool with OSM tag predicates     │
│  6. PUSH, OPEN PR, fill template (Summary + Test Plan)             │
│  7. AI REVIEW runs automatically; address HIGH severity findings   │
│  8. If cross-lane: request review from paired lane owner (§13)     │
│  9. MERGE; close issue; pick next                                  │
└────────────────────────────────────────────────────────────────────┘
```

**WIP cap:** maximum **2 issues in `Doing`** per person at any moment. If you have 2 in flight, finish one before pulling another.

## 5. Conventional commits (enforced)

Format: `type(scope): description`

| Type | When |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `chore` | Tooling, config, docs, deps |
| `refactor` | Code change that neither adds nor fixes |
| `test` | Test-only changes |
| `docs` | Docs-only changes |

Scopes match lane folders: `agent`, `ontology`, `eval`, `voice`, `atak`, `routing`, `data`, `hardware`, `deploy`, `models`, `mesh`, `security`, `crypto`, `infra`, `docs`, `ci`.

Examples:
- `feat(agent): add find_pois tool with OSM tag predicates`
- `fix(routing): handle empty waypoint list from Valhalla`
- `chore(ci): pin liboqs-python to 0.10.0`
- `feat(crypto): ML-DSA sign on /plan response`

## 6. Definition of Done

A change is **Done** when:

1. Local `make ci` passes (lint, type-check, test, security scan).
2. PR exists with a one-line summary and a "test plan" line (even if "ran the unit test, validated by hand").
3. Remote CI passes on the PR.
4. AI PR review completed; HIGH severity findings addressed or explicitly waived in PR description.
5. If the change touches `/docs/contracts/` or a public API: paired reviewer signed off (PRD §13).
6. Merged to `main`; `main` still demo-runnable (`make run` succeeds; `make demo` still passes once the demo path lands by Sun 0500).

## 7. Smoke-test cadence (PRD §13.4)

Every **30 minutes**, the lane owner runs `make run` in their lane and pings their endpoint. If a lane has been silent for 90+ minutes, the active integrator pings the owner.

By **Sun 0500 (hour 18)**, the entire hero scenario must execute via `make demo`. From that point on, **anything that breaks `make demo` is reverted, not "fixed forward."**

## 8. Scope discipline (PRD §14.12)

- **Build backward from the demo.** If a change does not serve the Sun 1410 finalist demo, cut it, defer it, or stub it. There is no Sunday afternoon refactor.
- **Hardcode what you can.** API keys in `.env`. AOIs in `data/aois.yml`. Trust list in a flat file. No dynamic config service.
- **Use frameworks that give you things for free.** FastAPI (routing, validation, OpenAPI free), Valhalla (routing engine free), `liboqs-python` (PQC primitives free), `ollama` (model serving free). We integrate; we do not build infrastructure.
- **Skip these:** Kubernetes, microservices beyond `agent` + `bridge`, custom auth, full e2e suite, observability stack, docs site.

## 9. Asking for help (the rubber-duck rule)

For the overnight grind (Sat 2200 – Sun 0700), when stuck:

1. Re-read this file and the relevant lane file.
2. Paste the problem into your AI agent (Codex / Cursor / Claude Code) — explain what you tried, what you expected, what happened.
3. **Only then** ping a teammate. A teammate's flow state at 0300 is more expensive than a 30-second AI round-trip.

## 9.1. Resuming work after a break (sleep, lunch, demo dry-run)

Before you write a single line of code after any break:

```
make catchup
```

This pulls main, refreshes deps if `pyproject.toml`/`Makefile` changed, summarizes recent commits, **flags contract changes** that may affect your in-flight work, and lists your open issues. Paste the output into your AI agent and ask it to flag anything you should know before resuming.

If a contract under `/docs/contracts/` changed while you were away, STOP coding and re-read it before continuing — your half-written code may be stale. The integrator-on-shift announces contract changes in Signal `#wayfinder` thread, but `make catchup` is your machine-side check.

## 10. The five non-negotiables

Verbatim from PRD §14.11. If we drop everything else, we keep these:

1. **`AGENTS.md` + `/.agents/*.md` ship in the first commit** (this file).
2. **`make ci` runs locally and remotely, identically.** Pre-push hook enforces it.
3. **AI PR review on every PR.** Sleep-deprived humans miss things; the bot doesn't get tired.
4. **Conventional commits enforced.** Clean commit history is what the integrator uses to triage at 0700.
5. **Branch protection on `main` with empty bypass list.** "Just this once" cannot become a habit if the server says no.

These five are the entire delta between "4 smart people writing 4 incompatible codebases" and "4 smart people shipping one product."

## 11. Glossary (skim once)

- **CoT** — Cursor on Target, the XML message format used by ATAK / WinTAK to share entities.
- **ML-DSA / Dilithium** — NIST FIPS 204 post-quantum digital signature.
- **ML-KEM / Kyber** — NIST FIPS 203 post-quantum key encapsulation.
- **liboqs** — Open Quantum Safe library; we use its Python bindings.
- **Jetson Orin Nano** — NVIDIA edge SBC, 8GB, ~7-15W, our deployment target.
- **Valhalla** — open-source routing engine; we extend its cost model.
- **OSM PBF** — OpenStreetMap binary format, our offline vector data.
- **DEM** — Digital Elevation Model; we use SRTM 1-arcsec.
- **PS2 / PS3 / PS4** — hackathon Problem Statements 2 (Edge), 3 (C2), 4 (Cyber).
- **AGENTS.md** — this file. Read it.

## 12. If you are confused

Default to the PRD. If the PRD doesn't say, write a 5-line ADR in `/docs/adrs/` and commit it as part of your PR. The ADR template is at `/docs/adrs/template.md`.
