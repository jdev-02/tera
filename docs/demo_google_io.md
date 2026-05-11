# 3-minute Google I/O Demo Script

## 0:00 - Wildfire Scenario Begins

"A wildfire and smoke event is pressuring Bay Area shelters. Connectivity is degraded, but responders still need a logistics decision."

Run:

```bash
curl -s http://localhost:8000/mission/demo/bay-area-wildfire | jq .
```

## 0:30 - TERA Loads Context

TERA can enrich from NWS alerts, WFIGS fire perimeter, AirNow AQI, HIFLD hospitals, SF511 road events, and cached sample state. In offline mode, it uses local fallback state.

## 1:00 - Shelter and Hospital Selection

TERA identifies Shelter North as nearly full and smoke exposed. It selects Shelter West because it has cleaner air and available capacity. It also keeps a hospital option in critical infrastructure.

## 1:30 - Vehicle and Resource Allocation

TERA assigns trucks to verified needs: water, N95 masks, medical kits, and blankets. If Google Route Optimization is configured, it can optimize dispatch; otherwise deterministic fallback keeps the mission running.

## 2:00 - Route Selection

TERA chooses Route C, the offline route candidate, and reports risk factors from available hazards, traffic, bridge, and AQI data.

## 2:20 - Trust Shield

A fake FEMA login link and unverified supply request appear in the scenario. TERA flags possible impersonation, marks the request as unverified, requires human approval, and prevents the unverified request from changing dispatch.

## 2:45 - Explanation

Gemini can generate an operator-facing explanation when online. Gemma/local fallback keeps the explanation available offline.

## 3:00 - Close

"TERA is not only a route planner. It is an offline-first emergency logistics coordinator with built-in trust protection."
