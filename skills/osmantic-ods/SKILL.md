---
name: osmantic-ods
description: "Manage, monitor, and deploy Osmantic Deployment System (ODS V3) private AI server: local model inference (llama.cpp/vLLM), Portal/Pixel agent, Open WebUI, LiteLLM, n8n workflows, Qdrant RAG, SearXNG, ComfyUI, and extensions."
---

# Osmantic Deployment System (ODS V3)

ODS V3 turns any PC, Mac, or Linux server into a sovereign, private AI homelab and deployment system with a single command. It wires together inference engines, chat interfaces, agent runtimes, vector storage, private search, and workflow automation without sending telemetry or requiring cloud subscriptions.

---

## Architecture Overview

```
                           +----------------------------------------+
                           |              User / Browser            |
                           +-------------------+--------------------+
                                               |
                  +----------------------------+---------------------------+
                  |                                                        |
                  v (Port 3001/3021)                                       v (Port 3000)
    +---------------------------+                              +-----------------------+
    |   ODS Dashboard & Portal   |                              |      Open WebUI       |
    | - Control Center & Stats  |                              | - ChatGPT-like Chat   |
    | - Pixel Autonomous Agent  |                              | - Multi-model select  |
    +-------------+-------------+                              +-----------+-----------+
                  |                                                        |
                  +----------------------------+---------------------------+
                                               |
                                               v (Port 4000)
                               +-------------------------------+
                               |        LiteLLM Gateway        |
                               | - Unified OpenAI-compat proxy |
                               | - Rate limits & key routing   |
                               +---------------+---------------+
                                               |
                 +-----------------------------+-----------------------------+
                 |                                                           |
                 v (Port 8080)                                               v
  +-------------------------------+                           +-------------------------------+
  |   llama-server / vLLM Engine  |                           |     External / Cloud APIs     |
  | - Local GGUF models           |                           | - Gemini API, Anthropic,      |
  | - CPU, NVIDIA CUDA, AMD, Arc  |                           |   OpenAI, LM Studio, Ollama   |
  +-------------------------------+                           +-------------------------------+
                 |
                 +-----------------------------------------------------------+
                 |                                                           |
                 v                                                           v
  +-------------------------------+                           +-------------------------------+
  |        Qdrant Vector DB       |                           |       SearXNG Meta-Search     |
  | - Private document RAG        |                           | - Zero-tracking web retrieval |
  +-------------------------------+                           +-------------------------------+
```

### Core Components
1. **Portal & Pixel Agent** (`http://localhost:3001/pixel` or `:3021/pixel`):
   - Autonomous task-executing AI agent running directly on private models or external APIs.
   - Tool calling, file access, bash execution, web search integration.
2. **Homelab Dashboard** (`http://localhost:3001` or `:3021`):
   - Fast React + Vite frontend and FastAPI backend (`dashboard-api`).
   - Service health status, GPU telemetry, VRAM usage, model switcher, extensions library.
3. **Open WebUI** (`http://localhost:3000`):
   - Full-featured ChatGPT/Claude-style conversational workspace with prompt library, document upload, and chat history.
4. **LiteLLM Gateway** (`http://localhost:4000`):
   - Standardized `/v1/chat/completions`, `/v1/embeddings`, `/v1/models` endpoint unifying local and cloud LLMs.
5. **Inference Engines**:
   - `llama-server` (llama.cpp) with Vulkan/ROCm/CUDA/SYCL/CPU backends.
   - `vLLM` for high-throughput multi-GPU deployments.
6. **Auxiliary Extensions**:
   - `n8n`: Autonomous workflow automation (`http://localhost:5678`).
   - `ComfyUI`: Local image and video generation (`http://localhost:8188`).
   - `SearXNG`: Self-hosted private search engine (`http://localhost:8080`).
   - `Qdrant`: Vector database for local knowledge base & RAG (`http://localhost:6333`).
   - `Whisper & Kokoro TTS`: Voice recognition and text-to-speech.

---

## Managing ODS via CLI

On Linux or via WSL2 on Windows (`wsl -d Ubuntu -e ods <command>`):

```bash
# Check stack health, container statuses, and running models
ods status

# View live logs for all services or a specific container
ods logs
ods logs -f llama-server
ods logs -f open-webui
ods logs -f dashboard-api

# Start, stop, or restart services
ods start
ods stop
ods restart
ods restart dashboard

# Update ODS to the latest release
ods update

# Manage configuration & secrets
ods config get LLM_MODEL
ods config set LLM_MODEL qwen3.5-2b

# Inspect system and GPU capabilities
ods doctor

# Interactive container shell
ods shell llama-server
```

---

## Windows & WSL2 Environment

On Windows 11, ODS runs seamlessly inside Ubuntu WSL2 with native hardware virtualization:
- **Distro**: Ubuntu 24.04 LTS Noble Numbat (`systemd=true`).
- **Container Engine**: Native `docker.io` and `docker-compose-v2` managed via systemd.
- **Port Forwarding**: WSL2 automatically mirrors ports (`3000`, `3001`/`3021`, `4000`, `8080`) to Windows `localhost`.
- **Desktop Launcher**: `AI-Agent-Desktop-Apps\ods_app.py` provides a native Windows GUI control station.

---

## Python REST API Integration

Interact with ODS programmatically from Python or Antigravity agents:

```python
import httpx

# LiteLLM OpenAI-compatible endpoint
response = httpx.post(
    "http://localhost:4000/v1/chat/completions",
    json={
        "model": "qwen3.5-2b",
        "messages": [{"role": "user", "content": "Hello, private AI server!"}],
        "temperature": 0.7
    },
    timeout=60.0
)
print(response.json()["choices"][0]["message"]["content"])
```

---

## Troubleshooting Checklist
- **Port Conflict**: If port 3001 is occupied, set `DASHBOARD_PORT=3021` in `.env`.
- **Docker Daemon**: Ensure docker is active via `sudo systemctl status docker`.
- **WSL Status**: Check `wsl --status` and `wsl -l -v`.
- **Logs**: Detailed installer log is saved at `/tmp/ods-install-<uid>.log`.

