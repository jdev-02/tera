# ATAK Jetson Link Test

This lane currently contains the LAN test harness for proving that a Samsung
device running ATAK/TERA can reach the Jetson over WiFi and receive a response
from the local Gemma/Ollama path.

The Android ATAK plugin skeleton is not present in this checkout beyond
`.gitkeep`, so these scripts are the reproducible connectivity probe and the
request shape the plugin should issue once the Java/Gradle files are restored.

## What Was Added

- `atak/scripts/run_jetson_gemma_server.sh` starts the Jetson-side FastAPI proof
  harness at `0.0.0.0:8080` and points it at local Ollama.
- `atak/scripts/test_jetson_link.sh` sends the same HTTP request the ATAK plugin
  should send to the Jetson.
- `Makefile` targets `atak-link-server` and `atak-link-test` wrap those scripts.

The test endpoint is:

```text
http://<JETSON_WIFI_IP>:8080/api/prompt
```

The server expects Ollama on the Jetson at:

```text
http://127.0.0.1:11434
```

Default model:

```text
gemma3:4b
```

## Demo-Day Playbook (after the first deploy)

Once the Jetson has been set up once via the steps below, the **only command Kyle
needs each time the team merges new work to `main`** is:

```bash
ssh digitaltrident1@<JETSON_WIFI_IP>
cd /home/digitaltrident1/Documents/tera_folder/tera
make jetson-compose-refresh
```

That single target (added in PR #92) does the full pull / rebuild / smoke-test
cycle:

1. Refuses if the local repo has uncommitted changes (no surprises).
2. Switches to `main` and pulls the latest (uses `make catchup` if available).
3. Stops `tera-planner.service` if it was previously installed via the native
   systemd path, freeing port 8080 for Docker.
4. Runs `docker compose down --remove-orphans && docker compose up --build -d
   llm-dev-kmh` against the repo-root `docker-compose.yml`.
5. Polls `http://127.0.0.1:8080/` for up to 30 seconds and greps the response
   for the ATAK Local button (`id="atakAgentBtn"`) to confirm the new build is
   live.

Verify from the demo laptop on the same WiFi:

```bash
curl -s http://<JETSON_WIFI_IP>:8080/ | grep atakAgentBtn
```

Tail logs if anything looks off:

```bash
docker compose logs -f llm-dev-kmh
```

### Customization knobs (env vars, all defaulted)

| Var                  | Default                                                | When to override                                       |
| -------------------- | ------------------------------------------------------ | ------------------------------------------------------ |
| `REPO_DIR`           | `/home/digitaltrident1/Documents/tera_folder/tera`     | Different clone path on the Jetson                     |
| `REMOTE`             | `origin`                                               | Mirrored fork                                          |
| `BRANCH`             | `main`                                                 | Deploying a feature branch for a one-off demo          |
| `COMPOSE_FILE`       | `docker-compose.yml`                                   | Alternate compose file                                 |
| `SERVICE_NAME`       | `llm-dev-kmh`                                          | Different compose service                              |
| `PLANNER_URL`        | `http://127.0.0.1:8080`                                | Healthcheck on a different port                        |

Example one-off demo deploy:

```bash
BRANCH=khick/source-planner make jetson-compose-refresh
```

### `.env` Kyle populates once on the Jetson

The compose service reads runtime config from the repo-root `.env`. Put this
there before the first `make jetson-compose-refresh`:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=gemma3:4b
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
CESIUM_ION_TOKEN=...
TERA_ATAK_MODEL=gemma3:4b
TERA_ATAK_AGENT_PROFILE=tera-atak-live
TERA_ATAK_DEVICE_URL=
TERA_ATAK_AGENT_COMMAND=
REQUEST_TIMEOUT_S=120
```

### Two refresh paths — pick one as the steady-state runner

The repo ships two ways to keep the Jetson current. **Don't run both at the same
time** — they will fight over port 8080.

| Path                              | Trigger                                | Where the planner runs                                       |
| --------------------------------- | -------------------------------------- | ------------------------------------------------------------ |
| **Native systemd autoupdate**     | `make jetson-autoupdate-install` once; `tera-planner-update.timer` fires every 1 min | `tera-planner.service` runs the FastAPI app **directly on the Jetson** via `deploy/scripts/run_tera_planner.sh` |
| **Docker compose refresh** (new)  | Manual `make jetson-compose-refresh`   | `docker compose up llm-dev-kmh` runs the planner **inside a container**, isolated from the host Python env |

For the hackathon demo we recommend the **Docker compose** path: reproducible,
isolated, and the smoke-test prints a green line when the new build is live.

The Docker path's refresh script is smart enough to `systemctl stop
tera-planner.service` before bringing up the container, so a one-time switch
from the native path to the Docker path is automatic. Going the other direction
(disabling Docker, re-enabling systemd) is manual:

```bash
docker compose -f docker-compose.yml down --remove-orphans
sudo systemctl start tera-planner.service
```

## Jetson Setup

Run these on the Jetson.

1. Connect the Jetson to the same WiFi network as the Samsung ATAK device.

2. Confirm Ollama is installed:

   ```bash
   ollama --version
   ```

3. Pull the model before going offline if it is not installed:

   ```bash
   ollama list
   ollama pull gemma3:4b
   ```

4. From the repo root, install Python dependencies if needed:

   ```bash
   python3.11 -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

5. Start the Jetson link server:

   ```bash
   bash atak/scripts/run_jetson_gemma_server.sh
   ```

   Equivalent make target:

   ```bash
   make atak-link-server
   ```

6. Find the Jetson WiFi IP:

   ```bash
   hostname -I
   ip -4 addr show
   ```

   Use the address on the WiFi interface, for example `192.168.1.42`.

7. Verify locally on the Jetson:

   ```bash
   curl -s http://127.0.0.1:8080/health
   ```

8. Verify the Gemma endpoint locally:

   ```bash
   curl -s -X POST http://127.0.0.1:8080/api/prompt \
     -H "Content-Type: application/json" \
     -d '{"prompt":"TERA ATAK link test. Reply briefly.","model":"gemma3:4b","llm_provider":"ollama","agent_profile":"tera-atak-link-test"}'
   ```

## ATAK Device Setup

Use this first from Android Termux or another shell on the Samsung device. This
proves the same network path the ATAK plugin will use.

1. Connect the Samsung device to the same WiFi network as the Jetson.

2. Install Termux if you need a shell, then install curl:

   ```bash
   pkg install curl python
   ```

3. Run the link test, replacing the IP with the Jetson WiFi IP:

   ```bash
   bash atak/scripts/test_jetson_link.sh 192.168.1.42 8080
   ```

   If running from a dev laptop instead of the phone:

   ```bash
   make atak-link-test JETSON_IP=192.168.1.42
   ```

4. Expected output starts with:

   ```text
   SUCCESS: TERA ATAK link reached Jetson Gemma endpoint.
   ```

5. In the ATAK plugin, configure the same values:

   ```text
   Jetson IP: <JETSON_WIFI_IP>
   Port: 8080
   Endpoint: /api/prompt
   Model: gemma3:4b
   ```

6. The plugin should POST this JSON:

   ```json
   {
     "prompt": "TERA ATAK link test. Reply with JSON containing status, model, and one short readiness sentence.",
     "model": "gemma3:4b",
     "llm_provider": "ollama",
     "agent_profile": "tera-atak-link-test"
   }
   ```

7. Treat HTTP 200 with a non-empty `response` field as success.

## Troubleshooting

- If `http://<JETSON_IP>:8080/health` fails from the phone, check that both
  devices are on the same WiFi subnet and that the Jetson server is bound to
  `0.0.0.0`.
- If health works but `/api/prompt` fails, check `ollama serve` and
  `ollama list` on the Jetson.
- If the first prompt is slow, run it once on the Jetson first to warm the
  model.
- If the phone cannot reach TCP 8080, allow inbound TCP 8080 on the Jetson
  firewall for the test window.
- This is a same-WiFi LAN proof. It is not the final Phase 3 WiFi-off hero path.
