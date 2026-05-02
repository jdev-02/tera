# RF Sim — AI Provider Configuration & Local Model Setup

---

## Supported Providers

### 1. Local Model (Ollama / LM Studio / llama.cpp)
- **Provider ID**: `local-model`
- **UI Label**: "Local Model"
- **Key field label**: "Model Name"
- **Key placeholder**: `e.g. llama3, mistral, phi3`
- **isLocalModel**: true
- **Models**: dynamically discovered from local endpoint

### 2. Anthropic (Claude)
- **Provider ID**: `anthropic`
- **UI Label**: "Claude"
- **Key field label**: "Anthropic API Key"
- **Key placeholder**: `Paste sk-ant-... API key`
- **Default model**: `claude-sonnet-4-6`
- **Available models**:
  - `claude-sonnet-4-6` → Claude Sonnet 4.6
  - `claude-3-7-sonnet-latest` → Claude 3.7 Sonnet
- **Max tokens**: 16,000
- **Temperature**: 0.2
- **Image support**: Yes (base64 multimodal)
- **Streaming**: Yes (SSE)
- **API endpoint**: `https://api.anthropic.com/v1/messages`

### 3. GenAI.mil (Gemini)
- **Provider ID**: `genai-mil`
- **UI Label**: "GenAI.mil"
- **Key field label**: "GenAI.mil API Key"
- **Key placeholder**: `Paste STARK_ API key`
- **Default model**: `gemini-3.1-pro`
- **Available models**:
  - `gemini-3.1-pro` → Gemini 3.1 Pro
  - `gemini-3.1` → Gemini 3.1
  - `gemini-2.5-pro` → Gemini 2.5 Pro
  - `gemini-2.5-flash` → Gemini 2.5 Flash
- **supportsModelDiscovery**: true (dynamically loads model list)
- **Max tokens**: 32,000
- **Temperature**: 0.2
- **Image support**: No (images are noted and ignored)
- **Streaming**: Yes (SSE)
- **API base**: `https://api.genai.mil/v1`

---

## Local Model Proxy — genai-proxy.js

### Ports
| Port | Protocol | Purpose |
|---|---|---|
| 8787 | HTTP | GenAI.mil proxy (local dev only) |
| 8788 | HTTPS (self-signed TLS) | Local model bridge (used by hosted https:// app) |

### Endpoints
| Path | Purpose |
|---|---|
| `/v1/chat/completions` | GenAI.mil proxy (HTTP port 8787) |
| `/v1/local/chat/completions` | Local model bridge (HTTPS port 8788) |
| `/v1/local/models` | Health check / model list |

### Start Commands
```bash
# GenAI.mil proxy only (HTTP, port 8787)
node genai-proxy.js

# Local model bridge + GenAI.mil proxy (HTTPS, port 8788)
node genai-proxy.js --local-model
```

### Local Model Backend — Default & Override
| Backend | Default URL | Override |
|---|---|---|
| Ollama | `http://localhost:11434/v1/chat/completions` | (default) |
| LM Studio | `http://localhost:1234/v1/chat/completions` | `LOCAL_MODEL_URL=http://localhost:1234/v1/chat/completions` |
| llama.cpp | `http://localhost:8080/v1/chat/completions` | `LOCAL_MODEL_URL=http://localhost:8080/v1/chat/completions` |

Set via environment variable:
```bash
# PowerShell
$env:LOCAL_MODEL_URL = "http://localhost:1234/v1/chat/completions"
node genai-proxy.js --local-model

# Bash
LOCAL_MODEL_URL=http://localhost:1234/v1/chat/completions node genai-proxy.js --local-model
```

### TLS Certificate Setup (required for local model mode)

The proxy needs a self-signed cert so the https:// hosted app can call it without mixed-content errors.

**Windows (Git for Windows OpenSSL):**
```powershell
New-Item -ItemType Directory -Force ".\certs" | Out-Null
& "C:\Program Files\Git\usr\bin\openssl.exe" req -x509 -newkey rsa:2048 -keyout ".\certs\proxy.key" -out ".\certs\proxy.crt" -days 3650 -nodes -subj "/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
```

**macOS/Linux:**
```bash
mkdir -p ./certs
openssl req -x509 -newkey rsa:2048 -keyout ./certs/proxy.key -out ./certs/proxy.crt -days 3650 -nodes -subj "/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
```

Then visit `https://127.0.0.1:8788` in the browser and trust the cert once.

---

## Request Parameters by Provider

| Parameter | Local Model | Anthropic | GenAI.mil |
|---|---|---|---|
| max_tokens | 999999 | 16000 | 32000 |
| temperature | 0.1 | 0.2 | 0.2 |
| stream | true (SSE) | true (SSE) | true (SSE) |
| image support | No | Yes (base64) | No |
| Scenario truncation | 6000 chars | Full | Full |
| Prompt style | Condensed + examples | Full expert | Full expert |

---

## Rate Limiting (Backend Server)

The backend server (`backend/src/server.js`) enforces:
- **AI relay bucket**: 30 requests per 60 seconds

---

## API Key Storage

API keys are stored encrypted in the backend database:
- **Algorithm**: AES-256-GCM
- **Key derivation**: from `aiConfigSecret` environment variable (`backend/src/config.js`)
- Encryption functions: `encryptSecret()` / `decryptSecret()` in `backend/src/server.js`

---

## Propagation Models

Used in `run-simulation` actions (`propagationModel` field):

| Value | Description |
|---|---|
| `itu-p525` | Free space path loss (ITU-R P.525) |
| `itu-p526` | Terrain-aware propagation (ITU-R P.526) |
| `itu-hybrid` | Terrain + weather combined |
| `itu-buildings-weather` | Buildings + weather (urban) |
