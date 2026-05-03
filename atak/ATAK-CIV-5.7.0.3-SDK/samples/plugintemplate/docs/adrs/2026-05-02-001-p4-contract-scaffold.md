# 2026-05-02-001 P4 Contract Scaffold

## Context

The PRD assigns P4 ownership of `atak/`, `routing/`, and `data/`, plus cross-cutting contracts with P1 and P2. Figma mockups are no longer in P4 scope.

## Decision

Add freeze-candidate contracts for agent-routing and CoT signature handoff, plus P4 lane notes for ATAK, routing, and data.

## Consequences

P1 can build `/plan` against a stable request/response shape, P2 can wire signatures against a named CoT detail block, and RFSim interoperability stays anchored on GeoJSON/KML.
