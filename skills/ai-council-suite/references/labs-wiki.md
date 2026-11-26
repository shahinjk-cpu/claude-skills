---
name: labs-wiki
description: 🧠 LLM-powered personal wiki — Karpathy pattern implementation with Claude Code skills, incremental compilation, and multi-agent support
---

# labs-wiki

# labs-wiki

A personal LLM-powered knowledge wiki based on [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern, enhanced with best-of-breed features from top community implementations.

## How It Works

```mermaid
graph LR
    subgraph "Capture"
        P[📱 Phone] --> API[Ingest API]
        B[💻 Browser] --> API
        T[⌨️ Terminal] --> API
    end

    subgraph "Auto-Ingest"
        API --> RAW[raw/]
        RAW --> W[File Watcher]
        W --> LLM[Codex CLI Compilation]
    end

    subgraph "Wiki"
        LLM --> S[wiki/sources/]
        LLM --> C[wiki/concepts/]
        LLM --> E[wiki/entities/]
    end

    style RAW fill:#e1f5fe
    style S fill:#f3e5f5
    style C fill:#f3e5f5
    style E fill:#f3e5f5
    style API fill:#e8f5e9
```

**Sources** are captured from any device via the Ingest API → written to `raw/` → **automatically processed** by the auto-ingest service through Codex CLI → wiki pages created with cross-references. Twitter/X and GitHub repo URLs get specialized deterministic fetch/extraction before compilation. **AGENTS.md** defines the schema that all AI tools follow.

## Architecture

```
labs-wiki/
├── raw/                    # Layer 1: Source documents + durable URL snapshots
│   └── assets/             # Binary files (images, PDFs)
├── wiki/                   # Layer 2: LLM-compiled knowledge
│   ├── sources/            # Source summaries (1:1 with raw/)
│   ├── concepts/           # Concept deep-dives
│   ├── entities/           # Named entities (tools, people, orgs)
│   ├── synthesis/          # Cross-cutting analysis
│   ├── index.md            # Auto-generated topic-clustered catalog
│   └── log.md              # Structured audit log
├── templates/              # Page templates with frontmatter
├── scripts/                # Python utilities (scaffold, lint, index, auto-ingest)
├── wiki-ingest-api/        # FastAPI capture service
├── Dockerfile.auto-ingest  # Auto-ingest watcher service
├─
