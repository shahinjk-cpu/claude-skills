---
name: mcp-server-builder
description: >-
  Guides designing, building, testing, and debugging production-grade Model Context
  Protocol (MCP) servers in Python (FastMCP) and TypeScript (@modelcontextprotocol/sdk).
  Inspired by anthropics/mcp-builder. Use when creating custom tools, external service
  connectors, or MCP plugins for Antigravity, Claude, or Cursor.
---

# MCP Server Builder & Plugin Architect

Inspired by `anthropics/mcp-builder` (~181k ⭐) and official MCP SDK reference implementations. Use this skill whenever building or debugging custom MCP servers.

## 1. Technology Choice

- **Python (FastMCP)**: Recommended for rapid tool creation, data science, AI workflows, and scripting.
- **TypeScript (`@modelcontextprotocol/sdk`)**: Recommended for web integrations, Node/npm tools, or production services.

## 2. FastMCP (Python) Quick Blueprint

```python
from mcp.server.fastmcp import FastMCP
from pydantic import Field

mcp = FastMCP("my-custom-service")

@mcp.tool()
def search_data(
    query: str = Field(description="Search term to query"),
    limit: int = Field(default=10, description="Max results to return (1-50)")
) -> str:
    """Detailed docstring explaining WHAT this tool does and WHEN the agent should call it."""
    # Implementation logic
    return f"Results for: {query}"

if __name__ == "__main__":
    mcp.run()
```

## 3. Best Practices for Agent-Friendly MCP Tools

1. **Descriptive Names & Docstrings**:
   - The LLM chooses tools based on name and docstring. Name tools cleanly (`search_orders`, not `s1`).
   - Clearly state requirements, constraints, and valid argument formats.
2. **Strict Parameter Validation**:
   - Use Pydantic / Zod schemas with default values and field descriptions.
3. **Structured & Compact Outputs**:
   - Return clean Markdown or JSON. Avoid dumping raw HTML or multi-megabyte binary data into the tool result.
4. **Security & Principle of Least Privilege**:
   - Never allow arbitrary shell execution without strict command whitelisting.
   - Validate paths against directory traversal (`../`).
