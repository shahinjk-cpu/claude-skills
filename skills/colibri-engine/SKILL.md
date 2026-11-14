---
name: colibri-engine
description: >
  High-performance hierarchical MoE inference engine in pure C for frontier LLMs (GLM-5.2 744B,
  DeepSeek-V4, Qwen-36/38, Kimi K3, Inkling, MiMo) on consumer hardware. Streams cold experts on-demand
  from NVMe SSD into RAM and GPU (Vulkan/CUDA) with zero dependencies. Use when the user wants to run,
  benchmark, or serve massive Mixture-of-Experts models locally, inspect hardware compatibility,
  or start the Colibri OpenAI-compatible API and MCP server.
---

# Colibri Engine — Pure-C Hierarchical MoE Inference Engine 🚀

Colibri is a groundbreaking, zero-dependency inference engine written in pure C that makes running frontier-class Mixture-of-Experts (MoE) models (such as GLM-5.2 744B, DeepSeek-V4, and Qwen3.6-35B) possible on consumer PCs and laptops.

Instead of requiring multi-GPU server clusters costing tens of thousands of dollars, Colibri unifies NVMe storage, system RAM, and GPU memory into an intelligent hierarchical memory system:
* **Dense layers & routers**: Kept resident in RAM/VRAM (~3.5 GB to 10 GB).
* **Hot experts**: Cached in GPU VRAM (via Vulkan or CUDA) or high-speed system RAM.
* **Cold experts**: Streamed dynamically on-demand directly from the NVMe SSD as tokens are generated.

---

## 🖥️ System Hardware Profile (Auto-Detected)

* **CPU**: Intel Core Ultra 7 155H (16 physical / 22 logical cores, AVX2).
* **RAM**: 16 GB DDR5 (total 16.8 GB).
* **GPU**: Intel Arc Graphics (Vulkan 1.4, ~9.6 GB budget, device-local).
* **Storage**: NVMe SSD (C: drive with 90+ GB free).

---

## 📦 Supported Model Families & Hardware Tiers

| Model ID | Full Name | Download | RAM Min / Good | Streaming Mode | Status on this PC |
|---|---|---|---|---|---|
| `qwen36-35b` | Qwen3.6-35B-A3B | 23.1 GB | 10 GB / 20 GB | From RAM | **Recommended & Fits** |
| `qwen3-coder-30b` | Qwen3-Coder-30B-A3B | 19.4 GB | 8 GB / 18 GB | From RAM | **Fits (Coding Specialist)** |
| `deepseek-v4-flash-reap` | DeepSeek-V4 Flash REAP 150B | 84.7 GB | 16 GB / 32 GB | Streams from SSD | **Fits (Streams from SSD)** |
| `qwen-image-2.1` | Qwen-Image-2.1 | 33.1 GB | 12 GB / 18 GB | From RAM | **Fits (Image Generation)** |
| `deepseek-v4-flash` | DeepSeek-V4 Flash 284B | 166.9 GB | 16 GB / 32 GB | Streams from SSD | Needs >172 GB disk |
| `glm-5.2` / `glm-5.3` | GLM-5.2 / GLM-5.3 (744B) | ~420 GB | 16 GB / 24 GB | Streams from SSD | Needs >440 GB disk |
| `kimi-k3` | Kimi K3 (2.8T MoE) | 1.56 TB | 32 GB / 64 GB | Streams from SSD | Needs >1.6 TB disk |

---

## 🛠️ CLI & Management Commands

### Local Repository Path
```text
C:\Users\sahin\.gemini\antigravity\scratch\repos\colibri
```

### 1. Hardware Inspection
```bash
python c/setup_hw.py --json
```

### 2. Check Model Compatibility
```bash
python c/coli setup --list --json
```

### 3. Automated Setup & Model Download
```bash
# Setup with confirmation and model choice (e.g. qwen36-35b or qwen3-coder-30b)
python c/coli setup --yes --model qwen36-35b --no-start
```

### 4. Running the Model Server
```bash
# Starts local inference server with OpenAI-compatible endpoint at http://127.0.0.1:8000/v1
python c/coli start
```

### 5. Running the Native MCP Server
```bash
# Exposes detect_hardware, recommend_models, install, start, stop, status tools
python c/coli mcp
# or directly:
python c/mcp_server.py
```

---

## 🌐 AI Client Integration (OpenAI API Gateway)

Once started, Colibri serves an OpenAI-compatible REST API at `http://127.0.0.1:8000/v1`. Any coding tool or agent can use it:
* **Base URL**: `http://127.0.0.1:8000/v1`
* **API Key**: `none` (or any dummy string)
* **Model ID**: Configured model (e.g. `qwen36-35b`)
* Compatible with Aider, Continue, Cline, Claude Code, Cursor, and custom Python scripts.
