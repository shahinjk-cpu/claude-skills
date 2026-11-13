---
name: mesh-llm
description: Distributed P2P inference cloud and GPU compute pooling. Links spare local compute across macOS, Linux, and Windows nodes via Skippy (patched llama.cpp) and exposes an OpenAI-compatible /v1 API for agent execution.
metadata:
  version: 1.0.0
---

# Mesh-LLM: Distributed P2P Compute Pooling

`Mesh-LLM` is a distributed infrastructure framework designed to pool GPUs and memory across multiple heterogeneous devices (macOS Metal, Linux CUDA/ROCm, Windows Vulkan/DirectX, and CPU fallback), exposing them as a unified OpenAI-compatible endpoint (`http://localhost:9337/v1`).

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\mesh-llm`

## Key Architecture

1. **Compute Federation**:
   - Links local desktops, laptops, and servers over low-latency P2P mesh networking without centralized cloud dependencies.
2. **Split Model Execution (Skippy)**:
   - Uses a patched, memory-efficient build of `llama.cpp` to split large models (e.g. 70B, DeepSeek 671B MoE) across physical nodes.
3. **OpenAI Drop-In Replacement**:
   - Any tool or agent supporting `OPENAI_BASE_URL` can connect seamlessly:
   ```bash
   export OPENAI_BASE_URL="http://localhost:9337/v1"
   export OPENAI_API_KEY="mesh"
   ```

## Getting Started

```bash
cd C:\Users\sahin\.gemini\antigravity\scratch\repos\mesh-llm
# Join or host a mesh cluster
cargo run --release -- --host
```
