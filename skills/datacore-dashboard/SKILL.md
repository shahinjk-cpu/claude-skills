---
name: datacore-dashboard
description: >-
  Full-screen HUD telemetry dashboard, live metric gauges, high-frequency canvas charts, and dark terminal aesthetic.
---

# Datacore Dashboard & Live Telemetry

Architecture for high-density, real-time developer dashboards, server monitoring HUDs, and terminal aesthetics.

## Design Philosophy
- **Dark Space Palette**: Zinc-950 background, Zinc-900 panels, 1px subtle Zinc-800 borders.
- **Data Density**: Compact metrics, tabular numerals (`font-mono`, `tabular-nums`), minimal padding.
- **Real-Time Streaming**: Server-Sent Events (SSE) or WebSockets directly bound to Canvas or SVG charts.
