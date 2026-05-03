# Agent to Routing Contract v0

Owner pair: P1 and P4.

Status: freeze candidate for Sat 1500.

## Request

`POST /plan`

```json
{
  "prompt": "Route me to the nearest freshwater source within 5km, on foot, covered terrain.",
  "lat": 37.7955,
  "lon": -122.3937,
  "ao": "sf",
  "profile": "foot_covered",
  "constraints": {
    "max_slope_degrees": 35,
    "avoid": ["ridgeline", "exposed_terrain"],
    "find": {"type": "freshwater", "radius_m": 5000}
  }
}
```

## Response

```json
{
  "route_id": "tera-demo-001",
  "status": "ok",
  "rationale": "Selected creek 2.1km NE; route follows draw to avoid ridgeline exposure.",
  "route_geojson": {
    "type": "Feature",
    "properties": {
      "name": "TERA Route",
      "profile": "foot_covered",
      "distance_m": 2100,
      "eta_s": 1800
    },
    "geometry": {
      "type": "LineString",
      "coordinates": [[-122.3937, 37.7955], [-122.389, 37.802]]
    }
  },
  "waypoints": [
    {"name": "Start", "lat": 37.7955, "lon": -122.3937},
    {"name": "Freshwater", "lat": 37.802, "lon": -122.389}
  ],
  "cost_breakdown": {
    "distance": 0.42,
    "slope": 0.18,
    "cover": 0.31,
    "ridgeline": 0.09
  },
  "signature": null
}
```

## Notes

- Coordinates are WGS84 decimal degrees.
- `route_geojson` is the common handoff to ATAK, WinTAK, web MVP, and RFSim.
- RFSim compatibility target: retain plain GeoJSON/KML export because RFSim imports GeoJSON, KML, KMZ, ATAK data packages, routes, overlays, DTED, and offline terrain data.
- Signature is `null` until P2 signer output is wired in.
