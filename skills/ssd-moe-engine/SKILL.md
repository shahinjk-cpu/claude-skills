---
name: ssd-moe-engine
description: >
  Run massive 70B-405B Mixture-of-Experts (MoE) LLMs directly on consumer hardware by streaming expert weights dynamically from fast NVMe SSDs with minimal VRAM/RAM.
metadata:
  version: "1.0.0"
  category: ai_ml
  triggers: ssd moe, airllm, fiddler, run 70b on ssd, large moe ssd, nvme offload
---

# SSD MoE Engine — Massive Models on Consumer Hardware

Deploys and optimizes runtimes (such as AirLLM, Fiddler, and MoE-Infinity) that dynamically stream Mixture-of-Experts (MoE) weights from an NVMe SSD into GPU/CPU memory on-demand.

## How It Works
Because MoE architectures only activate 2 to 8 experts per token out of 64+ experts, 90% of model weights remain idle. By pinning the shared attention layers in VRAM and streaming only the active expert tensors from NVMe disk, users can run models like Mixtral 8x22B or DeepSeek MoE with as little as 16GB RAM.

## Setup Pattern (AirLLM / HuggingFace)
```python
from airllm import AutoModel

model = AutoModel.from_pretrained("deepseek-ai/DeepSeek-V2-Lite")
input_text = ["Explain quantum computing in simple terms:"]
input_tokens = model.tokenizer(input_text, return_tensors="pt")
output = model.generate(input_tokens["input_ids"], max_new_tokens=100)
```
