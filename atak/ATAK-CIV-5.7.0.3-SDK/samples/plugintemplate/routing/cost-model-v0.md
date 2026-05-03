# Routing Cost Model v0

Owner: P4.

Goal: make the route explainable to a combat engineer in the demo, not perfect GIS science.

## Profiles

| Profile | Primary Use | Hard Constraints | Soft Costs |
| --- | --- | --- | --- |
| `foot_fast` | fastest dismount movement | OSM foot access | distance, grade |
| `foot_covered` | signature-managed dismount movement | OSM foot access, max slope | exposure, ridgeline, grade, distance |
| `vehicle_mrap` | stretch vehicle scenario | road access, bridge/fording constraints | grade, road class, chokepoints |

## Terrain Costs

- `slope`: derived from DEM; reject cells above prompt threshold when specified.
- `ridgeline`: penalize local high-prominence cells and skyline crossings.
- `cover`: prefer vegetation, draws, and terrain masking; penalize open/high-exposure landcover.
- `water`: freshwater POI candidates from OSM tags such as `natural=spring`, `waterway=stream`, `water=river`, and `amenity=drinking_water`.

## Demo Acceptance

- Golden route for SF starts near Ferry Building and returns a plausible route with visible rationale.
- Golden route for austere AO returns a route that P4 rates at least 4/5 versus hand planning.
- Every route response includes a cost breakdown suitable for a one-line on-stage explanation.
