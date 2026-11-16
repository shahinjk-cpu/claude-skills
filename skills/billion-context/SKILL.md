---
name: billion-context
description: >
  Architecture patterns and techniques for massive context windows (1M to 10M+ tokens). Needle-in-a-haystack retrieval, hierarchical summarization, and context preservation.
metadata:
  version: "1.0.0"
  category: memory_context
  triggers: billion context, massive context, 1m tokens, context window management, long context
---

# Billion-Context — Massive Context Window Engineering

Guidelines and optimization patterns for effectively utilizing ultra-large context models (Gemini 1.5/2.0 1M–2M context, Claude 200k, and billion-token research frameworks).

## Strategic Context Hygiene
1. **Attention Sink Awareness**: Models recall information best at the very beginning and very end of the prompt (the "lost in the middle" phenomenon). Place critical system instructions and target queries at the edges.
2. **Hierarchical Indexing**: For huge document sets, provide a top-level table of contents and file manifests first before streaming raw contents.
3. **Structured Chunk Tagging**: Wrap distinct source documents with clear XML tags (`<document id="doc_1" path="...">...</document>`).
