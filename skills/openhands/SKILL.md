---
name: openhands
description: OpenHands (formerly OpenDevin) AI software engineering platform. Guides running autonomous coding agents, configuring Docker sandboxes, authoring Microagents, executing headless CLI tasks, and connecting Model Context Protocol (MCP) servers.
metadata:
  version: 1.0.0
---

# OpenHands: Autonomous AI Software Engineer

`OpenHands` (by All-Hands-AI) is an open-source platform that enables AI software development agents to write code, debug issues, execute terminal commands, browse the web, and run tests inside isolated environments.

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\OpenHands`  
Official website: `https://all-hands.dev`

## Core Architectural Components

1. **Agent Runtime & Execution Sandbox**:
   - Sandboxed execution runs inside secure Docker containers (or Kubernetes clusters).
   - Prevents host file corruption while giving the agent full bash, python, and git capabilities.
2. **Microagents**:
   - Dynamically triggered instruction blocks residing in `.openhands/microagents/`.
   - Provide repo-specific knowledge (e.g. how to run custom test suites, linting guidelines, database migrations).
3. **Model Context Protocol (MCP) Integration**:
   - OpenHands agents natively discover and execute MCP tools from external servers (Figma, databases, web scraping, custom APIs).
   - Configured via `mcp_config` in agent settings or backend environment variables.

## Running OpenHands

### 1. Docker Run (All-in-One Web GUI)
```bash
docker run -it --pull=always \
    -e SANDBOX_USER_ID=$(id -u) \
    -e WORKSPACE_BASE=$PWD/workspace \
    -v $PWD/workspace:/opt/workspace_base \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -p 3000:3000 \
    --add-host host.docker.internal:host-gateway \
    --name openhands-app \
    docker.all-hands.dev/all-hands-ai/openhands:0.28
```

### 2. Headless CLI Execution
```bash
# Run autonomous issue resolution from terminal
python -m openhands.core.main -t "Fix TypeError in auth middleware when token is expired"
```

## Best Practices
- **Explicit Scoping**: Specify the exact directories the agent should touch.
- **Verification Gates**: Always instruct OpenHands to run existing unit tests before marking an issue resolved.
- **Microagent Scaffolding**: Add repo-specific rules to `.openhands/microagents/repo.md` for consistent workflows.
