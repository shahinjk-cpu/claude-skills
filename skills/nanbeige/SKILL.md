---
name: nanbeige
description: Nanbeige LLM Lab models (Nanbeige4.3-33B, Nanbeige4-3B-Thinking) featuring Depth-Hybrid-Attention, extended context (512K), deep-search tool reasoning, and specialized vLLM/SGLang deployment workflows.
metadata:
  version: 1.0.0
---

# Nanbeige LLM: Hybrid-Attention Reasoning Models

`Nanbeige` is an advanced open-weights model family engineered by the Nanbeige LLM Lab, recognized for high-density reasoning, deep tool use, and long-context comprehension up to 512,000 tokens.

Official models: `huggingface.co/Nanbeige`  
Local tools: `C:\Users\sahin\.gemini\antigravity\scratch\repos\Nanbeige`

## Model Family

- **Nanbeige4.3-33B**: 52-layer dense model with Depth-Hybrid-Attention, excelling at code generation, mathematical analysis, and structured agent planning.
- **Nanbeige4-3B-Thinking**: Compact 3-billion parameter reasoning model with native inner thought tokens (`<think>...</think>`), tailored for high-speed edge reasoning.
- **Depth-Hybrid-Attention**: Combines sliding window attention with full global attention layers to slash memory consumption during 512K inference.

## Serving with vLLM / SGLang

```bash
# High-throughput serving via vLLM
vllm serve Nanbeige/Nanbeige4.3-33B-Chat \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --trust-remote-code
```
