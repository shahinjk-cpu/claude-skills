---
name: librechat
description: LibreChat extensible open-source AI platform and multi-model chat interface (danny-avila). Guides configuring librechat.yaml, integrating MCP servers, custom Subagents, Code Interpreter, Artifacts, and multi-provider deployments.
metadata:
  version: 1.0.0
---

# LibreChat: Extensible Multi-Model AI Platform

`LibreChat` (by Danny Avila) is an open-source, multi-user AI platform supporting all leading AI providers (OpenAI, Anthropic, Google Gemini, Ollama, DeepSeek, AWS Bedrock, OpenRouter) with native MCP integration, Subagents, Artifacts, and Code Interpreter.

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\LibreChat`  
Official website: `https://librechat.ai`

## Core Features

1. **Model Context Protocol (MCP) Integration**:
   - Native first-class MCP server support in `librechat.yaml`.
   - Allows LibreChat agents to invoke live filesystem, database, web search, and GitHub tools seamlessly.
2. **Subagents & Multi-Agent Workflows**:
   - Built-in LangGraph agent runtime enabling autonomous multi-agent delegation, parallel tool calling, and human-in-the-loop validation.
3. **Code Interpreter & Artifacts**:
   - Sandboxed python execution for charts, data wrangling, and simulations.
   - Interactive HTML/React/SVG Artifacts rendering directly in the chat stream.

## Configuration: `librechat.yaml` with MCP

```yaml
version: 1.1.5
cache: true
endpoints:
  custom:
    - name: "Local-Ollama"
      apiKey: "ollama"
      baseURL: "http://localhost:11434/v1"
      models:
        default: ["llama3.3", "qwen2.5-coder"]
mcpServers:
  filesystem:
    type: stdio
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "C:/Users/sahin/workspace"]
  web_search:
    type: sse
    url: "http://localhost:8080/sse"
```

## Running LibreChat with Docker Compose

```bash
cd C:\Users\sahin\.gemini\antigravity\scratch\repos\LibreChat
cp .env.example .env
docker compose up -d
```
Access the LibreChat interface at `http://localhost:3080`.
