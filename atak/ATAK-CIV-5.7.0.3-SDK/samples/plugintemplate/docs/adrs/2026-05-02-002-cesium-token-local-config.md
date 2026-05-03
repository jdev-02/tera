# 2026-05-02-002 Cesium Token Local Config

## Context

P4 has access to a Cesium ion token. RFSim supports Cesium terrain/building workflows and can accept a token through settings or configuration.

## Decision

Treat the Cesium ion token as local-only configuration. Add `.env.example` with `CESIUM_ION_TOKEN`, ignore real `.env` files, and keep offline DEM/DTED as the required TERA routing fallback.

## Consequences

The team can use Cesium for terrain preview and RFSim workflows without leaking credentials or making the core offline demo dependent on Cesium network access.
