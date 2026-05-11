# TERA v2 API Inventory

Use `scripts/test_live_apis.py` for optional live checks. Unit tests use fixtures/mocks and do not require network access.

| API | Category | Auth | Env Vars | Endpoint | Priority | TERA Use |
|---|---|---|---|---|---|---|
| NOAA/NWS Alerts | Weather hazards | No key | none | `/alerts/active` | P0 | hazard overlay |
| FEMA OpenFEMA | Disaster declarations | No key | none | OData | P0 | official disaster context |
| HIFLD Hospitals | Critical infra | Public | none | ArcGIS FeatureServer | P0 | hospital selection |
| HIFLD Critical Infrastructure | Critical infra | Public | none | ArcGIS FeatureServer | P0 | fire/EMS/shelter/EOC |
| Google Maps Routes | Routing | Key | `GOOGLE_MAPS_API_KEY` | `computeRoutes` | P0 | route candidates |
| Google Route Optimization | Logistics | OAuth | `GOOGLE_PROJECT_ID`, `GOOGLE_ACCESS_TOKEN` | `optimizeTours` | P0 | vehicle/resource allocation |
| Firebase | Offline sync | Firebase | Firebase config | SDK | P0 | shared state |
| NIFC/WFIGS | Wildfire | Public | none | ArcGIS FeatureServer | P1 | fire perimeter |
| EPA AirNow | Air quality | Key | `AIRNOW_API_KEY` | latLong current | P1 | smoke/PM2.5 risk |
| SF 511 | Traffic | Key | `SF511_API_KEY` | traffic/events | P1 | closures/incidents |
| NASA FIRMS | Satellite fire | Key | `FIRMS_MAP_KEY` | area/csv | P1 | hotspots |
| USGS Earthquake | Earthquake | No key | none | GeoJSON feed | P2 | earthquake scenario |
| USGS Water | Flood | No key | none | nwis/iv | P2 | stream/gage |
| NOAA NWPS | Flood forecast | Public | none | nwps | P2 | flood forecast |
| National Bridge Inventory | Infrastructure | No key | none | ArcGIS FeatureServer | P2 | heavy truck risk |
| NREL Fuel Stations | Fuel logistics | Key | `NREL_API_KEY` | nearest | P2 | fuel feasibility |
| NASA EONET | Natural events | No key | none | events | P3 | backup global events |
| ReliefWeb | Humanitarian reports | Approved appname | `RELIEFWEB_APPNAME` | reports | P3 | situation reports |
| Google Safe Browsing | Phishing/malware URL checking | Google API key | `GOOGLE_SAFE_BROWSING_API_KEY` | `threatMatches:find` | P1 | flag phishing/fake FEMA/donation links |
| VirusTotal | URL/domain reputation | API key | `VT_API_KEY` | v3 URL/domain reports | P2 | enrich suspicious URL/domain reputation |
| urlscan.io | URL behavior and redirect scan | API key | `URLSCAN_API_KEY` | scan/result | P2 | inspect suspicious crisis links |
| RDAP | Domain metadata | Public | none | rdap.org | P2 | check domain metadata and possible newly registered domains |

## PowerShell Live Checks

```powershell
Invoke-RestMethod -Uri "https://api.weather.gov/alerts/active?area=CA"
Invoke-RestMethod -Uri "https://api.weather.gov/points/37.7749,-122.4194"
Invoke-RestMethod -Uri "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?`$top=5"
Invoke-RestMethod -Uri "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?`$filter=state eq 'CA'&`$top=5"
Invoke-RestMethod -Uri "https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/Hospitals_hifld/FeatureServer/0/query?where=STATE%3D%27CA%27&outFields=NAME,ADDRESS,CITY,STATE,TYPE&f=geojson"
Invoke-RestMethod -Uri "https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/Critical_Infrastructure_Map_Service/FeatureServer?f=json"
$ci = Invoke-RestMethod -Uri "https://services.arcgis.com/XG15cJAlne2vxtgt/ArcGIS/rest/services/Critical_Infrastructure_Map_Service/FeatureServer?f=json"
$ci.layers | Select-Object id,name
Invoke-RestMethod -Uri "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/WFIGS_Interagency_Perimeters_Current/FeatureServer/0/query?where=1%3D1&outFields=*&f=geojson"
Invoke-RestMethod -Uri "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson"
Invoke-RestMethod -Uri "https://waterservices.usgs.gov/nwis/iv/?format=json&stateCd=ca&parameterCd=00060,00065&siteStatus=active"
Invoke-RestMethod -Uri "https://api.water.noaa.gov/nwps/v1/docs/"
Invoke-RestMethod -Uri "https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/NTAD_National_Bridge_Inventory/FeatureServer/0/query?where=1%3D1&outFields=STRUCTURE_NUMBER_008,FACILITY_CARRIED_007,STATE_CODE_001,COUNTY_CODE_003,FEATURES_DESC_006A&f=json&resultRecordCount=10"
Invoke-RestMethod -Uri "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=20"
```

Key-based examples:

```powershell
Invoke-RestMethod -Uri "https://www.airnowapi.org/aq/observation/latLong/current/?format=application/json&latitude=37.7749&longitude=-122.4194&distance=25&API_KEY=$env:AIRNOW_API_KEY"
Invoke-RestMethod -Uri "https://api.511.org/traffic/events?api_key=$env:SF511_API_KEY"
Invoke-RestMethod -Uri "https://firms.modaps.eosdis.nasa.gov/api/area/csv/$env:FIRMS_MAP_KEY/VIIRS_SNPP_NRT/-125,32,-113,42/1"
Invoke-RestMethod -Uri "https://developer.nrel.gov/api/alt-fuel-stations/v1/nearest.json?api_key=$env:NREL_API_KEY&latitude=37.7749&longitude=-122.4194&fuel_type=LNG,CNG,BD,RD,LPG,ELEC&radius=50"
```

Google Route Optimization:

```powershell
Invoke-RestMethod `
  -Uri "https://routeoptimization.googleapis.com/v1/projects/$env:GOOGLE_PROJECT_ID:optimizeTours" `
  -Method POST `
  -Headers @{
    "Authorization" = "Bearer $env:GOOGLE_ACCESS_TOKEN"
    "Content-Type" = "application/json"
  } `
  -Body (Get-Content ".\optimize_request.json" -Raw)
```

ReliefWeb:

```powershell
$body = @{
  limit = 5
  sort = @("date:desc")
  filter = @{
    field = "country.name"
    value = "United States of America"
  }
  fields = @{
    include = @("title", "date", "url", "country", "disaster")
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "https://api.reliefweb.int/v2/reports?appname=$env:RELIEFWEB_APPNAME" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

Trust Shield:

```powershell
$body = @{
  client = @{ clientId = "tera"; clientVersion = "0.2" }
  threatInfo = @{
    threatTypes = @("MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION")
    platformTypes = @("ANY_PLATFORM")
    threatEntryTypes = @("URL")
    threatEntries = @(@{ url = "https://www.fema.gov/" })
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=$env:GOOGLE_SAFE_BROWSING_API_KEY" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```
