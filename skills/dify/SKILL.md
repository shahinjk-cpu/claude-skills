---
name: dify
description: Dify open-source LLMOps and agent application development platform (langgenius). Guides visual workflow orchestration, RAG pipelines, Dify DSL authoring, agent tool creation, and Dify plugin/MCP integration.
metadata:
  version: 1.0.0
---

# Dify: LLMOps & Agentic Workflow Platform

`Dify` (by LangGenius) is an open-source platform combining visual AI workflow building, Retrieval-Augmented Generation (RAG) pipelines, model management, and agent orchestration.

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\dify`  
Official website: `https://dify.ai`

## Key Capabilities

1. **Visual Workflow Orchestration & DSL**:
   - Compose multi-step agentic pipelines using declarative YAML/JSON DSL schemas.
   - Node types: `Start`, `LLM`, `Knowledge Retrieval`, `Code (Python/JS)`, `IF/ELSE`, `HTTP Request`, `Tool`, `End`.
2. **Enterprise RAG Engine**:
   - Hybrid search combining dense semantic vectors + sparse BM25 keyword matching + reranking models.
   - Automatic document chunking, metadata extraction, and multi-tenant knowledge bases.
3. **MCP & Plugin Architecture**:
   - Dify agents dynamically connect to external Model Context Protocol (MCP) servers via stdio and SSE transports.
   - Supports custom tool plugins built in Python.
4. **Backend-as-a-Service (BaaS)**:
   - Exposes RESTful APIs and SDKs (`dify-client`) for embedding complex agent workflows into external applications.

## Self-Hosting with Docker Compose

```bash
cd C:\Users\sahin\.gemini\antigravity\scratch\repos\dify\docker
cp .env.example .env
docker compose up -d
```
Access the Dify dashboard at `http://localhost/install` to create the initial admin account.

## Workflow DSL Example (Snippet)
```yaml
app:
  name: "Document QA Agent"
  mode: "workflow"
workflow:
  nodes:
    - id: "start"
      type: "start"
    - id: "retrieval"
      type: "knowledge-retrieval"
      data:
        dataset_ids: ["ds_knowledge_base"]
    - id: "llm_answer"
      type: "llm"
      data:
        model: "gemini-2.5-pro"
        prompt_template: "Context: {{#retrieval.result#}}
Question: {{#start.query#}}"
```
