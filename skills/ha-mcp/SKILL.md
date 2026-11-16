---
name: ha-mcp
description: >
  Home Assistant Model Context Protocol (MCP) server. Controls smart home entities, reads sensor states, triggers scenes and automations, and queries energy metrics via natural language.
metadata:
  version: "1.0.0"
  category: backend_api
  triggers: ha-mcp, home assistant, smart home mcp, iot agent, home assistant api
---

# Home Assistant MCP — Smart Home Agent Bridge

Connects AI agents to Home Assistant via the official Home Assistant MCP server protocol. Inspects entity registries, queries states, calls services, and triggers automations.

## Available Tools
- `ha_get_states()`: List all sensors, lights, switches, and climate devices.
- `ha_call_service(domain, service, service_data)`: Turn devices on/off, adjust temperatures, trigger scenes.
- `ha_get_history(entity_id, days)`: Retrieve historical sensor metrics and energy consumption.

## Configuration in MCP
```json
{
  "mcpServers": {
    "homeassistant": {
      "command": "uvx",
      "args": ["ha-mcp"],
      "env": {
        "HASS_URL": "http://homeassistant.local:8123",
        "HASS_TOKEN": "YOUR_LONG_LIVED_ACCESS_TOKEN"
      }
    }
  }
}
```
