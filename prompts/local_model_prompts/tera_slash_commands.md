# TERA — Slash Commands (AI Preset Prompts)

These slash commands are pre-built prompts that users can trigger via `/command` syntax in the AI chat.
Each command injects a full expert prompt into the chat input, which the AI then executes against the current scenario state.

---

## Environment Commands

### `/rf-environment` — RF Environment Analysis
**Category:** Environment
```
Generate a comprehensive RF environmental analysis of the current map area. Include terrain effects (line-of-sight, diffraction, shadowing), urban density and multipath, vegetation attenuation by frequency band, atmospheric effects (ducting, rain fade, thermal layers), ground conductivity, and estimated RF noise floor across relevant bands. Pull specific terrain and asset data from the scenario.
```

### `/rf-terrain-mask` — Terrain Masking Analysis
**Category:** Environment
```
Identify terrain masking opportunities in the area of operations. Map RF shadow regions and concealed zones from the terrain data, identify protected movement corridors screened from adversary intercept, and suggest hidden relay and emitter placement locations that exploit terrain shielding. Reference the terrain LOS matrix for specific obstruction points.
```

### `/rf-mobility-impact` — Mobility Impact Analysis
**Category:** Environment
```
Analyze how movement affects RF performance across the scenario. Assess link stability along likely movement routes, identify dead zones and signal drop corridors, specify handoff requirements between radio nodes during movement, and recommend mobile relay positioning for each phase of maneuver.
```

---

## Analysis Commands

### `/rf-link-analysis` — RF Link Analysis
**Category:** Analysis
```
Analyze RF links between all placed assets. Provide full link budget for each pair, SNR estimates, fade margin, path loss, Eb/N0, estimated throughput, interference sources, and probability of detection or intercept where applicable. Use the terrain LOS matrix to cite specific blocked and clear links.
```

### `/rf-coverage` — RF Coverage Analysis
**Category:** Analysis
```
Produce an RF coverage analysis for all active emitters in the scenario. Describe expected signal strength regions, LOS vs NLOS zones, coverage gaps, overlap and interference zones, and how coverage varies by frequency across the area of operations.
```

---

## Spectrum Commands

### `/rf-spectrum` — Spectrum Analysis
**Category:** Spectrum
```
Analyze spectrum usage within the current area of operations. List all occupied frequency bands from placed assets, identify interference sources and congestion, flag frequencies within 5 MHz of each other as potential intermodulation risks, assess spectrum availability in VHF/UHF/microwave bands, and classify detected emitters as friendly, hostile, or unknown where context is available.
```

### `/rf-deconflict` — Frequency Deconfliction
**Category:** Spectrum
```
Optimize frequency and network assignments for all placed assets. Provide a frequency allocation plan with minimum separation requirements, time-slotting recommendations for shared spectrum, network separation strategies, interference mitigation techniques, and an EMCON-compliant configuration. Flag any current frequency conflicts.
```

### `/spectrum-plan` — Generate Spectrum Plan
**Category:** Spectrum
```
Generate a detailed spectrum management plan for all assets in the scenario. List all in-use frequencies grouped by band, identify conflicts and intermodulation risks, and provide a deconfliction table with recommended frequency assignments, separation requirements, and remarks.
```

---

## EW / Electronic Warfare Commands

### `/rf-threat-assessment` — EW Threat Assessment
**Category:** EW
```
Assess RF and EW threats in the area of operations based on the current scenario. Identify likely jammer or adversary emitter locations, estimate EW coverage zones, highlight vulnerable links from the terrain LOS matrix, prioritize threats by severity, and recommend countermeasures for the most critical vulnerabilities.
```

### `/rf-jamming-effects` — Jamming Effects Simulation
**Category:** EW
```
Simulate the effects of jamming on the placed friendly systems. Estimate J/S ratios for each link, identify denied and degraded regions, describe system-specific impacts by radio type, calculate burn-through ranges where applicable, and recommend specific countermeasures including frequency hopping, power increase, and antenna options.
```

### `/rf-detection-risk` — Detection Risk Assessment
**Category:** EW
```
Estimate the likelihood of adversary detection of RF emissions from placed friendly assets. Provide detection range estimates per emitter, intercept probability based on power and frequency, emitter signature analysis, LPI/LPD effectiveness for applicable systems, and exposure timelines. Recommend emission control measures.
```

### `/rf-geolocate` — Emitter Geolocation Analysis
**Category:** EW
```
Simulate emitter geolocation using RF techniques for the placed assets or adversary emitters in the scenario. Describe TDOA, FDOA, and AOA solutions, estimate error ellipses based on sensor geometry, specify required sensor geometry for fix accuracy, estimate time to fix, and provide confidence levels for each method.
```

---

## Network Commands

### `/rf-network-optimize` — Network Optimization
**Category:** Network
```
Optimize the full RF network across all placed assets. Recommend node placement improvements, relay positioning for air/ground/space platforms, transmit power adjustments to minimize detection risk while maintaining link margins, antenna selection for each node type, and routing improvements. Use the terrain LOS matrix to justify each recommendation.
```

### `/rf-relay-plan` — Relay Architecture Plan
**Category:** Network
```
Design a relay architecture for the current scenario. Identify which links require relays based on distance and terrain blockage, propose optimal relay positions with coordinates, compare platform options (UAV, UGV, hilltop static, SATCOM), provide coverage extension analysis for each option, and include redundancy planning for critical links.
```

### `/rf-antenna-select` — Antenna Selection
**Category:** Network
```
Recommend antenna configurations for all placed assets. For each node specify the optimal antenna type (omni, directional, phased array), required gain in dBi, beamwidth tradeoffs, polarization, and antenna height optimization. Tailor recommendations to each asset's role (command post, dismounted, vehicle, relay, ISR).
```

### `/rf-power-control` — Power Control Optimization
**Category:** Network
```
Optimize transmit power across all placed assets. Determine minimum effective power levels that maintain required link margins, quantify detection risk reduction at lower power, estimate battery consumption impacts for manpack radios, and align power settings with EMCON posture. Provide a power plan table per asset.
```

### `/rf-dataflow` — Data Flow Analysis
**Category:** Network
```
Map and analyze data flow across the RF network. Estimate bandwidth usage per link based on asset types and roles, identify bottlenecks and latency hotspots, describe priority-based routing recommendations, and flag links where data demand exceeds estimated capacity.
```

---

## Planning Commands

### `/rf-mission-profile` — Mission RF Profile
**Category:** Planning
```
Generate a complete RF communications plan based on the current scenario and asset layout. Include a full communications architecture, frequency plan with primary and alternate frequencies per net, EMCON posture by phase, redundancy strategy, and integration of all placed assets into a coherent net structure.
```

### `/rf-isr-integration` — ISR Integration Plan
**Category:** Planning
```
Integrate RF planning with ISR assets in the scenario. Specify data link requirements per sensor type, bandwidth allocation across the network, UAV relay roles and orbit positions, and sensor-to-shooter connectivity paths. Identify bottlenecks and recommend waveform or routing improvements.
```

### `/rf-predict` — RF Condition Prediction
**Category:** Planning
```
Predict RF conditions over time for the current scenario. Include expected propagation changes with weather and time-of-day, atmospheric ducting risk periods, anticipated adversary EW adaptation patterns, and recommended frequency or posture adjustments for each predicted condition change.
```

### `/rf-recommend` — RF Recommendations
**Category:** Planning
```
Provide prioritized, actionable RF recommendations for the current scenario. Assess the full picture — terrain, assets, frequencies, links, threats — and output the top recommended actions ranked by impact and urgency, with specific risk mitigation steps and the best course of action given current conditions.
```

### `/pace` — Generate PACE Plan
**Category:** Planning
```
Generate a complete PACE (Primary / Alternate / Contingency / Emergency) communications plan for the current scenario. Structure each tier with: method, equipment, frequency/channel, call signs, authentication, and remarks. Use placed assets and their frequencies as the basis. Include COMSEC/OPSEC notes.
```

### `/soi` — Generate SOI/CEOI
**Category:** Planning
```
Generate a Signal Operating Instructions (SOI) and Communications-Electronics Operating Instructions (CEOI) document for the current scenario. Include net names, frequencies, call signs, authentication tables, equipment types, channel plans, COMSEC fill instructions, relay designations, and MEDEVAC frequencies.
```

### `/aar` — Generate AAR
**Category:** Planning
```
Generate an After-Action Report (AAR) for the current scenario. Include classification, DTG, unit, objectives, summary of RF communications performance, what was sustained, what needs improvement, and recommendations. Pull data from placed assets, LOS matrix, and simulation results.
```

---

## Simulation Commands

### `/tera-simulate` — Full Scenario Simulation
**Category:** Simulation
```
Run a full RF scenario simulation across all placed assets. Describe end-to-end communication performance, identify failure points and single points of failure, provide timeline-based outcomes for a representative mission sequence, and give what-if comparisons for alternate configurations or terrain conditions.
```

---

## Diagnostics Commands

### `/rf-debug` — RF Diagnostics
**Category:** Diagnostics
```
Diagnose RF issues in the current scenario. Identify root causes of any blocked links, coverage gaps, or configuration anomalies. Check for mismatched frequencies, implausible power or gain values, terrain obstructions, and relay gaps. Provide specific corrective actions for each identified problem.
```

---

## Export Commands

### `/rf-export` — Export RF Plan
**Category:** Export
```
Generate an exportable RF plan document for the current scenario. Produce a comprehensive report in structured markdown that includes all asset configurations, frequency assignments, link statuses, relay topology, PACE plan summary, and key recommendations — formatted for use as a mission planning reference or briefing product.
```

---

## Summary Table

| Command | Label | Category |
|---|---|---|
| `/rf-environment` | RF Environment Analysis | Environment |
| `/rf-terrain-mask` | Terrain Masking Analysis | Environment |
| `/rf-mobility-impact` | Mobility Impact Analysis | Environment |
| `/rf-link-analysis` | RF Link Analysis | Analysis |
| `/rf-coverage` | RF Coverage Analysis | Analysis |
| `/rf-spectrum` | Spectrum Analysis | Spectrum |
| `/rf-deconflict` | Frequency Deconfliction | Spectrum |
| `/spectrum-plan` | Generate Spectrum Plan | Spectrum |
| `/rf-threat-assessment` | EW Threat Assessment | EW |
| `/rf-jamming-effects` | Jamming Effects Simulation | EW |
| `/rf-detection-risk` | Detection Risk Assessment | EW |
| `/rf-geolocate` | Emitter Geolocation Analysis | EW |
| `/rf-network-optimize` | Network Optimization | Network |
| `/rf-relay-plan` | Relay Architecture Plan | Network |
| `/rf-antenna-select` | Antenna Selection | Network |
| `/rf-power-control` | Power Control Optimization | Network |
| `/rf-dataflow` | Data Flow Analysis | Network |
| `/rf-mission-profile` | Mission RF Profile | Planning |
| `/rf-isr-integration` | ISR Integration Plan | Planning |
| `/rf-predict` | RF Condition Prediction | Planning |
| `/rf-recommend` | RF Recommendations | Planning |
| `/pace` | Generate PACE Plan | Planning |
| `/soi` | Generate SOI/CEOI | Planning |
| `/aar` | Generate AAR | Planning |
| `/tera-simulate` | Full Scenario Simulation | Simulation |
| `/rf-debug` | RF Diagnostics | Diagnostics |
| `/rf-export` | Export RF Plan | Export |
