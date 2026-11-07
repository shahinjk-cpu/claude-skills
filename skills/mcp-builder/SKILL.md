---
name: mcp-builder
description: Build custom MCP servers — tool definitions, resource exposure, TypeScript SDK, testing
metadata:
  type: skill
  triggers: ["mcp", "model context protocol", "mcp server", "build mcp", "custom tool"]
---

# MCP Server Builder

## Setup
```bash
npm create @modelcontextprotocol/server my-mcp-server
cd my-mcp-server && npm install
```

## Tool definition
```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new Server({ name: 'my-server', version: '1.0.0' }, {
  capabilities: { tools: {} }
});

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: 'search_database',
    description: 'Search the internal database',
    inputSchema: {
      type: 'object',
      properties: { query: { type: 'string' }, limit: { type: 'number', default: 10 } },
      required: ['query']
    }
  }]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === 'search_database') {
    const { query, limit = 10 } = request.params.arguments as any;
    const results = await db.search(query, limit);
    return { content: [{ type: 'text', text: JSON.stringify(results) }] };
  }
  throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${request.params.name}`);
});

await server.connect(new StdioServerTransport());
```

## Claude Code config (settings.json)
```json
{
  "mcpServers": {
    "my-server": {
      "command": "node",
      "args": ["path/to/server/dist/index.js"]
    }
  }
}
```

## Rules
- Each tool: single responsibility
- Always validate input before executing
- Return structured JSON for complex data, plain text for simple
- Errors: use McpError with appropriate ErrorCode
