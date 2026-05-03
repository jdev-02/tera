# Data Pipeline

The Phase 1/2 data build produces four local artifacts:

- `data/extracts/sf.osm.pbf`
- `data/extracts/austere.osm.pbf`
- `data/dem/sf.tif`
- `data/dem/austere.tif`

Install lane tools:

```bash
brew install osmium-tool gdal
```

Fetch and verify the full Phase 1 data bundle:

```bash
data/scripts/fetch_all.sh
```

This downloads a small San Francisco PBF from BBBike, queries Overpass for the
austere AO, downloads public Copernicus GLO-30 DEM source tiles, crops both AOIs,
then writes and verifies `data/manifest.sha256`.

Clip OSM extracts from a larger source PBF:

```bash
data/scripts/clip_osm.sh /path/to/california-latest.osm.pbf
```

Crop DEM GeoTIFFs from one or more source DEM tiles:

```bash
data/scripts/build_dem.sh /path/to/source-dem-1.tif /path/to/source-dem-2.tif
```

Write and verify the artifact manifest:

```bash
data/scripts/write_manifest.sh
data/scripts/verify_manifest.sh
```

`data/aois.yml` is the source of truth for AOI bounding boxes and output paths.

Root-level `make data-fetch` / `make data-verify` are documented lane entry
points, but the root `Makefile` is owned by P2. Until P2 wires those targets,
use `data/scripts/fetch_all.sh` and `data/scripts/verify_manifest.sh` directly.
