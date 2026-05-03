# Data Lane

Owner: P4.

This directory tracks source data, hashes, and processing notes. Large OSM PBF, DEM, DTED, and landcover files should not be committed unless the team explicitly chooses Git LFS.

## Required Demo AOs

| AO | Purpose | Data Needed |
| --- | --- | --- |
| San Francisco | familiar judge-facing modality | OSM extract, DEM/elevation, optional waterfront/freshwater POIs |
| Austere AO | mission-real modality | OSM extract, DEM, landcover, selected hero scenario POIs |

## Cesium Ion Token

Use the Cesium ion token only as local configuration for RFSim or terrain preview workflows. Do not commit the token to source. Put it in `.env` as `CESIUM_ION_TOKEN`, or enter it through RFSim's settings UI when using the hosted/local RFSim app.

Cesium-backed terrain is a visualization and preview aid for the hackathon. The TERA demo path should still keep an offline DEM/DTED fallback so the core route pipeline works with network disabled.

## Manifest Fields

```json
{
  "name": "sf",
  "source_url": "https://example.invalid/source.osm.pbf",
  "sha256": "fill-after-download",
  "bounds": [-122.53, 37.70, -122.34, 37.83],
  "generated_at": "2026-05-02T19:00:00Z",
  "notes": "Ferry Building demo AO"
}
```
