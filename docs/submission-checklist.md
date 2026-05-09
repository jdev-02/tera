# TERA — 1200 PDT Submission Checklist + First-Principles Drift Check

> **For:** Jon (team lead). **Authored:** Sun 2026-05-03 ~10:50 PDT against `main` HEAD `9961df6`.
> **Submission cutoff:** Sun **1200 PDT** (~70 minutes from authoring).
> **Stage time:** 1410 PDT.
> **Source of truth for posture:** `docs/SUBMISSION_NOTES.md` (read-only). PRD §1, §12, §13 in `PRD.md` / `docs/PRD.md`.
> **Audit basis:** `docs/demo-readiness-2026-05-03.md` (read against `main @ f02d24e` ~0950 PDT today).
>
> **Read-only inputs (the writer of this checklist did not modify):** `docs/PRD.md`, `TERA pitch.docx`, `docs/SUBMISSION_NOTES.md`, `docs/presentation/deck-outline.md`. Drift surfaced here, not patched there.

---

## Section 1 — Submission artifacts (1200 PDT cutoff)

| # | Artifact | Owner | Status | Location / URL when ready | Next action (with time slot) |
|---|----------|-------|--------|---------------------------|------------------------------|
| 1 | **Public GitHub repo URL** | Jon | **DONE** | `https://github.com/jdev-02/tera` — verified `gh repo view jdev-02/tera --json url,visibility` returns `{"isPrivate":false,"visibility":"PUBLIC"}` at 10:51 PDT. | None. Confirmed accessible. |
| 2 | **README.md at repo root** | Jon | **TODO (stale claim — see drift check §3)** | `https://github.com/jdev-02/tera/blob/main/README.md` | **Jon, 1130–1140:** strike `Whisper-tiny (in)` from the repo-layout block at `README.md:66` (Whisper is not shipped on `main` per audit R3). Optional: replace with `Android SpeechRecognizer (plugin) + Piper TTS (out)`. The §2 hook line at `README.md:5` ("Voice in, voice and visual out") is defensible as written. |
| 3 | **PRD link** | Jon | **DONE** | `https://github.com/jdev-02/tera/blob/main/PRD.md` (and `docs/PRD.md`). 813 lines, lifecycle current. | None. **(Note: docs/PRD.md has uncommitted local edits in Jon's working tree — confirm whether those should ship before 1200, see §1 follow-up below.)** |
| 4 | **`docs/SUBMISSION_NOTES.md`** | Jon | **DONE** | `https://github.com/jdev-02/tera/blob/main/docs/SUBMISSION_NOTES.md` — 50 lines, complete. NPS Foundation affiliation, prize-handling, ethics, branding, disclosures all present. | None. |
| 5 | **Pitch deck — `TERA pitch.docx`** | Jon (writing now) | **IN PROGRESS** (Jon's 1000–1100 rewrite slot) | Repo root: `TERA pitch.docx`. **Currently UNTRACKED** in git (`git status`: `Untracked files: TERA pitch.docx`). | **Jon, by 1140:** confirm finished file is in repo root, then `git add "TERA pitch.docx" && git commit -m "docs(pitch): final v3 deck for 1200 submission"` on a feature branch (NOT main directly per repo branch protection) and merge via PR. If the deck is delivered as `.pptx` / `.pdf` instead, drop alongside and add the path to the submission form. |
| 6 | **Demo recording bundle (YouTube unlisted, 1-min cut + supporting clips)** | Jon (cut) / Satriyo (S7) / Ben (B2/K2) | **TODO** | Per `docs/demo-recording-plan.md`: most clips are local-only by design (gitignored binaries). The hackathon-rule **1-min YouTube unlisted** cut (issue #28) is the one external link. | **Jon, 1100–1145:** assemble per `docs/demo-recording-plan.md` "Submission video plan" — 4×15s segments. Upload **unlisted**. Submission form gets that single URL. **Submission can list "live demo at 1410, supporting recordings published to <YouTube playlist URL> by 1300"** if the playlist isn't fully populated by 1200. |
| 7 | **Tag a release at the submission commit** | Jon | **TODO (skip if not required by submission form)** | Suggested tag: `v1.0-submission` at the `main` HEAD that the submission form points to. | **Jon, 1155:** if the submission form requires a tag/release, run `git tag v1.0-submission <sha> && git push --tags`. If the form just takes a repo URL, **skip**. |
| 8 | **Cesium Ion token** | Satriyo | **DONE** (not committed; not required) | `.env.example` ships `CESIUM_ION_TOKEN=` empty. `.env` is gitignored. Audit R1 / R2 do not flag a leaked token; per `docs/SUBMISSION_NOTES.md:19` Cesium Ion is "provided as a partner resource by the event organizer" → judges have their own access. | None. **Do not** put a token in the submission form even if a field exists for it. |
| 9 | **Submission form (the actual URL/email submission goes to)** | Jon | **🔴 RED — NOT FOUND. BLOCKER.** | **Not referenced in:** `KICKOFF.md`, `README.md`, `docs/SUBMISSION_NOTES.md`, `PRD.md`, `docs/PRD.md`, `TASKS.md`, `AGENTS.md` (rg confirmed: only generic mentions of "submission form" appear in `TASKS.md:196` and `docs/PRD.md:530-540` without a URL). | **Jon, IMMEDIATELY (10:55):** find it. Likely sources, in order of speed: (a) Cerebral Valley event Slack / Discord pinned message; (b) the original event registration confirmation email; (c) Cerebral Valley + xTech event landing page; (d) ask Kyle (he handled team registration per `KICKOFF.md:16`). **Until this URL is in hand, the 1200 cutoff is at risk.** |
| 10 | **Team list / handles** | Jon | **DONE (verify match)** | `team.yml` + `README.md:84-90` table + `docs/PRD.md` §13 list **Jon (`@jdev-02`), Satriyo (`@aleens-labs`), Kyle (`@khicks1724` / `@kylemhicks`), Ben (`@benschwierking`)**. Posture per `docs/SUBMISSION_NOTES.md` is "Team TruePoint, NPS Foundation Entrepreneurship Club affiliation, no DoD representation." | **Jon, 1155:** when filling the submission form, paste the names + GitHub handles directly from `README.md:84-90`. Team name on the form = **TruePoint** (`docs/SUBMISSION_NOTES.md:4`); product name = **TERA — Tactical Edge Route Agent** (`README.md:1`). |

### Submission-form fields Jon should pre-answer (30-second list)

The submission form will likely ask for one or more of these. Pre-write the answer so Jon doesn't have to think at 1155:

- **Team name:** TruePoint (`docs/SUBMISSION_NOTES.md:4`).
- **Product name:** TERA — Tactical Edge Route Agent (`README.md:1`).
- **Problem statement(s) addressed:** PS2 (Edge Deployments and Drone Operation) primary, PS3 (Mission Command and Control) secondary, PS4 (Digital Defense and Cybersecurity) tertiary. (`docs/PRD.md:24-26`.)
- **One-line description (≤140 chars):** *"Pocket-sized, fully-offline AI agent that turns natural-language intent into ML-DSA-signed tactical routes rendered inside ATAK on a Jetson."*
- **Longer description (≤500 chars):** lift PRD §2 thesis at `docs/PRD.md:54` ("A pocket-sized, fully-offline AI agent that turns natural language into trustworthy tactical routes inside ATAK, on the edge, in environments where the cloud doesn't exist — and where the network around you can't be trusted either.").
- **Repo URL:** `https://github.com/jdev-02/tera`.
- **Demo video URL:** the YouTube unlisted 1-min cut (TBD, target 1145).
- **Team category / track (if asked):** US Army xTech RFI alignment, PS2 lead.
- **Target user / customer (if asked):** Recon Marine / SOF Team Lead (PRD §5 P-1 "Sgt. Vega"); secondary SAR / wildland fire / expedition lead (PRD §5 P-3 "Sam") for dual-use.
- **Open-source license:** MIT (`README.md:104`).
- **Affiliation (if asked):** NPS Foundation Entrepreneurship Club. **Not** representing US Army, Navy, or any DoD entity (`docs/SUBMISSION_NOTES.md:12`). Prize, if any, → NPS Foundation 501(c)(3) (`docs/SUBMISSION_NOTES.md:38`).

If the form asks for fields **not** in this list (e.g., "expected impact KPI," "founder LinkedIn URLs," "investor introductions wanted"), Jon answers in 30 seconds — none should be blockers.

### Section 1 follow-ups (flag, don't block)

- **`docs/PRD.md` has uncommitted local edits** (`git status` on this branch shows `M docs/PRD.md`, ~30 line delta). The user instructed this coordinator to leave PRD untouched, so the diff has not been inspected or committed here. **Jon: decide before 1200 whether those edits ship, get reverted, or stay in your working tree.** If they ship: separate PR, fast.
- **`docs/demo-readiness-2026-05-03.md`, `docs/presentation/deck-outline.md`, `docs/presentation/security-briefing-satriyo.md` are all currently UNTRACKED** (`git status`). They're referenced repeatedly from this checklist and from `TERA pitch.docx`'s rewrite. **Jon, 1140:** decide whether to commit (recommended — they're public-safe) or leave local. If staying local, the submission form's repo link won't show them.

---

## Section 2 — Status legend

- **DONE** — artifact exists at the location stated, verified at authoring time.
- **IN PROGRESS** — owner is actively working; deliverable expected before 1200.
- **TODO** — concrete next action listed; owner has the time slot.
- **🔴 RED** — blocker; must resolve before 1200 or the submission slips/fails.

---

## Section 3 — PRD First-Principles Drift Check

> **Premise:** the PRD §1 / §4 / §2 product promise paragraph (`PRD.md:39-91`, lines 70 and 91 in particular) describes the contract TERA makes with the operator and the judge. Each verb-by-verb promise is checked against `main` HEAD `9961df6` (post-#102 / #105 / #106 / #109 / #110 / #111). **Kyle's branch `khick/jetson-webapp-run-20260503` is explicitly out of scope for this check** — its 2,104 lines of staged code may flip individual rows from RED to GREEN if shipped as a scoped PR before stage time, but on `main` today the math is what's below.

### 3.1 Drift table

| PRD §1 / §4 promise | Where it's implemented | Current state on `main` | Slide claim should be |
|---|---|---|---|
| **"operator speaks or types intent"** | ATAK plugin: `atak/plugin/.../TERAPlugin.java:288-381` (Android `SpeechRecognizer`, per #94 / #110) for voice; plain text `prompt` field in `PlanRequest` (`agent/schemas.py`) for typed intent. | **YELLOW.** Voice IN works *via the plugin*, **not** via Whisper-tiny on the Jetson as PRD §7.2 line 218 promises. There is no `/plan/voice` endpoint in `agent/app.py`; no Whisper import anywhere in `agent/` or `voice/`. Audit R3 (`docs/demo-readiness-2026-05-03.md:33`). | *"Operator speaks via the ATAK plugin's on-device STT (Android `SpeechRecognizer`) or types in the plugin chat — text reaches the agent."* **Do not say "Whisper-tiny on Jetson."** |
| **"on-device LLM interprets it as structured query"** | `agent/orchestrator.py` calls `agent/llm/...` registry; system prompt + JSON schema from `ontology/`; structured output → `RouteQuery`. On Jetson with `OLLAMA_MODEL=gemma3:4b` per audit b1. | **YELLOW.** Code path is real on `main`. Live exercise on the **Jetson** is unproven (audit R2, `docs/demo-readiness-2026-05-03.md:31` — #82 LEAVE OPEN). On a laptop with `austere` profile and ollama, it works; on the demo Jetson, **untested as of 0950 today**. | *"On-device Gemma 3 4B (Q4_K_M, via ollama) interprets the prompt and emits a strict-schema `RouteQuery` JSON. The LLM never sees the prompt unless it passes 6 pre-LLM security stages first."* Pair with deck slide 5. |
| **"local routing engine returns a route"** | **NOT WIRED.** `agent/orchestrator.py:36` imports `from agent.tools import find_pois, route` → `agent/tools/__init__.py:12` re-exports from `agent/tools/stubs.py:90-128` which returns a 2-coordinate straight `LineString`. `routing/valhalla_client.py` is shipped (#109) and tested but **not imported by `agent/`** (rg `valhalla\|ValhallaClient` against `agent/` returns 0 hits). Audit R1, `docs/demo-readiness-2026-05-03.md:31`. | **🔴 RED.** The "blue line down a draw, around a saddle" hero claim from PRD §2 (`PRD.md:46`) is, on stage today, a straight geodesic between origin and destination. Anyone who watches the map render will see this. | **Default V-B framing per deck-outline slide 6 (`docs/presentation/deck-outline.md:183-184`):** *"Candidate routes are preloaded and vetted against OSM, NAIP imagery, and DTED for the demo AOI. The agent picks and signs the right one for the operator's intent. Live solver over the same stack is the next milestone — Valhalla client merged at #109; wiring tracked at #83."* **Do not** narrate "see how it routes around the ridge" on slide 3. **Conditional flip (future tense only):** *if* Kyle's solver lands as a scoped PR before 1410, this row flips RED → GREEN and slide 6 becomes V-A. That is a decision for 1300 dress rehearsal #1, not a 1100 claim. |
| **"route is signed with post-quantum credentials"** | `crypto/ml_dsa_signer.py` (Dilithium3 / FIPS 204, with Ed25519 fallback when liboqs missing). `agent/orchestrator.py:_sign_response` binds canonical JSON of route + waypoints + rationale + destination + mission_type. `/plan/verify` enforces trust list at `agent/orchestrator.py:438`. Trust-list bootstrap on startup (#105) at `agent/app.py:40-62`. 16 tests in `security/prompt_injection_tests.py` + `tests/test_orchestrator.py:591-723` all pass. | **GREEN** (with a Yellow caveat for the demo box). Sign + verify round-trip measured at **0.426 ms avg** on the dev box (Ed25519 fallback) — 12× under PRD §11.2 5 ms target either way. On the demo Jetson with `make install-crypto`, scheme prints `ML-DSA-65`. **Caveat:** if liboqs isn't installed on the demo box at stage time, the on-screen field reads `Ed25519-fallback`, not `ML-DSA-65` (audit b2). | *"Every `/plan` response is signed with **ML-DSA-65** (NIST FIPS 204). The plugin calls `/plan/verify` before drawing any route — invalid sig, untrusted key, or tampered route are all rejected before pixels hit the operator's screen. Sign + verify under 0.5 ms on Jetson."* If liboqs is not installed on the demo box, **either** install it pre-stage (`make install-crypto` per `docs/demo-readiness-2026-05-03.md:206`) **or** acknowledge "Ed25519 fallback for the laptop demo; Jetson uses ML-DSA-65" (less crisp, still honest). |
| **"ATAK renders it visually"** | `atak/plugin/.../TERAPlugin.java:487-545` reads `route.geometry.coordinates` (RFC 7946 `[lon,lat]`), renders blue polyline `Color.argb(220, 0, 100, 255)` strokeWeight 4.0, drops `Marker` per `waypoints[i]`. PR #106 on `main`. Code-verified GREEN; **device-verified UNKNOWN** in this audit (no Android in audit env). | **GREEN (code) / YELLOW (live device).** The plugin's render code is correct and on `main`. Stage validity depends on the Samsung EUD being paired to the Jetson at 1410. Audit e1 (`docs/demo-readiness-2026-05-03.md:60`). Cosmetic gap: plugin reads `wp.optString("name", ...)`, but `agent.schemas.Waypoint` field is `label` → markers default to `WP-1`, `WP-2`. Not demo-blocking. | *"ATAK renders the verified blue polyline with waypoint pins on NAIP imagery — exactly the way an operator already uses TAK."* Add the 2-second silent hold for the blue-line moment per PRD §12 line 439. |
| **"on-device TTS engine speaks the rationale + waypoints aloud"** | `voice/tts.py` + `voice/piper_client.py` → Piper neural TTS (~30 MB voice, CPU-only so it doesn't fight Gemma for GPU). `agent/orchestrator.py:639-652` lazy-imports `synthesize_rationale_b64`, embeds in `audio_b64` when `?tts=true`. `voice/glossary.py` + `voice/rationale.py` handle MGRS/acronym phonetics. Tests pass in `make ci`. | **YELLOW.** Code path is live on `main`. Latency on this dev box: cold synth **3054 ms**, warm synth **1126 ms** (PRD §11.2 line 403 target: <1s). **On Jetson, unmeasured today.** Audit d1 (`docs/demo-readiness-2026-05-03.md:57`). For stage stability the deck-outline (`docs/presentation/deck-outline.md:84`) is treating Piper as live — pre-rendering would be the prudent fallback if the warm number on Jetson exceeds 1.5s at dress rehearsal. | *"Piper neural TTS speaks the route rationale + waypoints in the operator's headset, in operator cadence — about a second on warm voice."* If Jetson warm latency >1s at rehearsal, **drop the "<1s" wording** and say "about a second" or "near-instant on warm voice." If the rehearsal shows >2s consistently, pre-render the rationale audio for the SAR-divert prompt and play it from the `audio_b64` blob (still defensible — the synth was real, just cached). |

### 3.2 Verdict and color-coded summary

- **GREEN:** "route is signed with post-quantum credentials" (with Ed25519-fallback caveat for the demo box).
- **YELLOW:** "operator speaks or types intent" · "on-device LLM interprets it as structured query" · "ATAK renders it visually" · "on-device TTS engine speaks the rationale + waypoints aloud."
- **🔴 RED:** "local routing engine returns a route." Slide 6 architecture variant must default to **V-B (preloaded vetted routes)** until Kyle's solver lands as a scoped PR. Slide 3 narration must avoid "see how it routes around the ridge."

### 3.3 Specific deck-outline bullets that need tightening

Cross-referenced against `docs/presentation/deck-outline.md` as Jon writes. Each bullet here needs a one-sentence edit to stay defensible.

| Deck-outline location | Current draft language | Drift risk | Tighter wording |
|---|---|---|---|
| `docs/presentation/deck-outline.md:82` (Slide 3 bullet) | *"Operator speaks via plugin STT (Android `SpeechRecognizer` per #94/#110 — **do not say "Whisper"**)."* | None — already tight. The "do not say Whisper" guardrail honors audit R3. | **Keep as-is.** |
| `docs/presentation/deck-outline.md:85` (Slide 3 bullet) | *"ATAK plugin renders the **blue polyline** … Hold the blue-line moment for 2 seconds in silence."* | None — code-verified GREEN. | **Keep as-is.** Pair with LD1 fallback clip per recording plan. |
| `docs/presentation/deck-outline.md:91` (Slide 3 verbatim lift, hero claim line) | *"From spoken intent to ATAK-rendered route plus narrated turn-by-turn in under 30 seconds, with WiFi physically off, every track post-quantum signed."* | YELLOW — "under 30 seconds" is unmeasured on the Jetson today (audit b3). | **Conditional:** if dress rehearsal #1 (1300) measures <30s, keep verbatim. If 30–60s, change to *"in under a minute"* and rely on PRD §11.2 line 401 (<60s p95 prompt → ATAK render). If >60s, drop the time number and say *"in one continuous take, on a battery, with WiFi off."* |
| `docs/presentation/deck-outline.md:98` (Slide 3 footer) | *"If asked about routing fidelity (audit R1 — straight-line stub today): see slide 6 architecture-variant V-B framing; do not promise 'around the saddle' on this slide."* | None — already honors RED row of drift table. | **Keep as-is.** This is the most important guardrail in the deck. |
| `docs/presentation/deck-outline.md:144` (Slide 5 verbatim lift) | *"After the pipeline passes, the response is signed with ML-DSA-65 — NIST FIPS 204."* | YELLOW — only if liboqs is not on the demo box at stage time (then on-screen field reads `Ed25519-fallback`). | **Pre-stage:** install liboqs on the demo box (`make install-crypto` per `docs/demo-readiness-2026-05-03.md:206`). **Fallback wording** if liboqs missing: *"Signed with ML-DSA-65 in production; this laptop is showing the Ed25519 fallback path because liboqs isn't installed here."* |
| `docs/presentation/deck-outline.md:166` (Slide 6 imagery & terrain claim) | *"OSM vector data + NAIP aerial imagery + DTED terrain, preloaded locally on Jetson; no runtime network dependency."* | YELLOW — preloading status of the **AOI bbox SW 38.160,-119.720 / NE 38.460,-119.360** on the demo Jetson is untested (audit a3 — Cesium currently from CDN at runtime, not WiFi-off-safe). | If WiFi-off-with-Cesium-cached cannot be confirmed by Kyle at 1300, change to *"Pre-cached on Jetson before WiFi off; runtime network dependency goes to zero (`tcpdump` will show 0 packets during the demo)."* — true and surfaces the proof point. |
| `docs/presentation/deck-outline.md:178-184` (Slide 6 V-A vs V-B variant) | Default V-B already chosen; V-A reserved for "if Kyle confirms `routing.valhalla_client` wired". | None — already honors RED row + the constraint of not relitigating Kyle's branch. | **Keep as-is.** This is the deck's most important honest scope-down. **Conditional flip:** if Kyle's solver lands as a scoped PR before 1410 *and* tiles are built for the AOI, slide 6 flips to V-A — that is a 1300 rehearsal decision, not a 1100 deck-write decision. |
| `docs/presentation/deck-outline.md:84` (Slide 3 — Piper TTS) | *"Piper speaks the rationale aloud in operator cadence — let the audience hear ~6–10 seconds of TTS."* | YELLOW — Jetson warm latency unmeasured (audit d1). | If Jetson warm latency at 1300 rehearsal is >1.5s, **pre-render** the SAR-divert rationale audio (still defensible — the synth is real, the byte stream is cached). Don't claim "real-time TTS." |

### 3.4 Honest caveats Jon should know but not volunteer (already in `docs/presentation/security-briefing-satriyo.md:74-80`)

1. **Prompt-Guard is substring-based** — sophisticated paraphrase / Unicode bypass is not caught by the first stage. Defense-in-depth is the structured-output JSON channel + schema validation downstream.
2. **Trust list bootstrap is "device self-attests."** First-boot auto-add of device key is in #105; multi-device fleet would need CRL / shared root (PRD §294, intentionally out of scope).
3. **Model integrity covers the small JSON metadata files** (4 Piper voices, ~33 KB) by SHA-256. Gemma weights and Piper `.onnx` are placeholder hashes pending download.

If a judge asks any of these directly, the answer is the above. **Do not preemptively volunteer** any of them on stage.

---

## Section 4 — Cross-references

- `PRD.md` / `docs/PRD.md` §1, §4, §12 — product promise + pitch flow.
- `docs/SUBMISSION_NOTES.md` — eligibility, ethics, prize handling, branding posture.
- `docs/demo-readiness-2026-05-03.md` — full demo-readiness audit (R1–R4, scoring, 4-hour priority plan).
- `docs/demo-recording-plan.md` — recording index + pitch-day fallback rules. **Updated in this PR with LD1 (SAR divert), S7 (4-cut security reel), `signal-2026-05-03-101544.mp4` placeholder, B2 (`connect_to_jetson.mov` placeholder), K2 (`tera_startup.mov` placeholder).**
- `docs/presentation/deck-outline.md` — Jon's 1000-1100 rewrite spine.
- `docs/presentation/security-briefing-satriyo.md` — Satriyo's brief; source of S7's 4 commands and security-beat slide language.

---

*End of checklist. Generated 2026-05-03 ~10:50 PDT for Jon's submission window.*
