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
     -d '{"prompt":"TERA ATAK link test. Reply briefly.","model":"gemma3:4b","llm_provider":"ollama","agent_profile":"tera-atak-live"}'
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
     "agent_profile": "tera-atak-live"
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
