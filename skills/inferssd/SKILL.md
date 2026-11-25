---
name: inferssd
description: >-
  Run massive Mixture-of-Experts (MoE) LLMs (DeepSeek-V4, Qwen3.6-35B, Muse-Spark) directly from fast NVMe SSD storage with low RAM/VRAM footprint via expert dynamic streaming.
---

# InferSSD — SSD-Streaming Mixture-of-Experts (MoE) Inference

InferSSD enables running massive 30B–400B+ MoE models directly from consumer NVMe SSDs without requiring enterprise-grade VRAM (e.g. 80GB H100s).

## Core Principles
1. **Dynamic Expert Offloading**: Only active experts for the current token are paged from NVMe SSD into RAM/VRAM via memory-mapped I/O (`mmap`).
2. **Predictive Prefetching**: Predicts next token candidate experts to overlap SSD read latency with GPU compute.
3. **OpenAI-Compatible API**: Exposes standard `/v1/chat/completions` and `/v1/models` endpoints for direct drop-in integration into agents (Claude Code, Cursor, Antigravity).

## Supported Architectures & Models
- **DeepSeek-V4.1-Flash** (MoE 16x12B active routing)
- **Qwen3.6-35B-A3B** (Hybrid MoE / Dense layers)
- **Muse-Spark-Open** (Multimodal MoE)
- **Gemma4-E4B** (SSD-mapped quantized weights)

## Usage Pattern
```bash
# Launch InferSSD server mapped to NVMe storage
inferssd serve --model-path /mnt/nvme/models/deepseek-moe.gguf --port 8000 --cache-vram 8GB
```

## Agent Integration
Configure the endpoint in `.env`:
```env
OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
OPENAI_API_KEY="sk-inferssd-local"
```
