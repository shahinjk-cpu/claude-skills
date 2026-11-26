---
name: d3-advanced-data-viz
description: >-
  Builds interactive, mathematically precise data visualizations, network graphs,
  and custom SVG charts using D3.js, Chart.js, Recharts, and Plotly. Inspired by
  chrisvoncsefalvay/claude-d3js-skill. Use when visualizing complex datasets,
  scientific graphs, or building interactive charts for dashboards.
---

# Advanced Data Visualization & D3.js Master

Inspired by `chrisvoncsefalvay/claude-d3js-skill`.

## 1. Visualization Selection Matrix
- **Correlations & Distributions**: Scatter plots with regression lines, Violin plots, Box plots (`Plotly` / `D3.js`).
- **Hierarchies & Trees**: Treemaps, Sunburst charts, Collapsible Tree diagrams.
- **Networks & Graphs**: Force-directed graphs (nodes & links) with drag-and-zoom.
- **Geographic & Spatial**: Choropleth maps with TopoJSON / GeoJSON and tooltip overlays.

## 2. D3.js & SVG Polish Rules
1. **Responsive SVG ViewBox**:
   - Always use `viewBox="0 0 width height"` and `preserveAspectRatio="xMidYMid meet"` so visualizations scale cleanly on mobile and high-DPI displays.
2. **Accessible Tooltips**:
   - Position floating tooltips relative to the container using pointer events; include full datum details with tabular numbers.
3. **Smooth Color Gradients & Contrast**:
   - Use perceptually uniform colormaps (Viridis, Plasma, Magma, Cividis) for continuous data so colors remain distinct and accessible to color-blind users.
