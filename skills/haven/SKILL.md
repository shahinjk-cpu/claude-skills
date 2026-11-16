---
name: haven
description: >
  Private self-hosted LLM home server and personal AI assistant orchestrator. Host local open-weights models, manage GPU/CPU offloading, and route home network agent queries securely.
metadata:
  version: "1.0.0"
  category: ai_ml
  triggers: haven, self-hosted ai, private assistant, home llm server, private agent
---

# Haven — Private Self-Hosted AI Server

Orchestrates a fully private, home-hosted AI inference server and agent hub. Connects local devices to private open-source models with zero external data telemetry.

## Architecture
- **Inference Backends**: vLLM, Ollama, llama.cpp, or TGI.
- **Hardware Management**: Dynamic model quantization (GGUF Q4_K_M / Q8 / EXL2) and VRAM budgeting.
- **Local Network Endpoint**: OpenAI-compatible REST API at `http://haven.local:8000/v1`.
