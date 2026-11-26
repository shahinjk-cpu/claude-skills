# Changelog

## v1.0.0 — 2026-11-26

首个版本。

### 知识库
- 整理 Gitee `DaShuJuZhiDaPingZhanShi` 的 12 个行业、25 套大屏模板
- 生成 `knowledge/catalog.json`（含 ECharts 版本、图表类型、配色、体积等扫描字段）
- 12 篇模板拆解：结构、配色、模块→图表映射、改造锚点、坑位
- 6 种布局原型 A1–A6
- 视觉语言、20+ 图表配方、动效交互、40 项交付质量线

### 数据接口
- 统一数据契约 v1.0（meta / kpis / series / lists / geo / alerts / ticker / views）
- JSON Schema
- 零依赖 adapter：mock / REST / SSE / WebSocket / inline / postMessage
- 超时、重试、指数退避、stale 状态、localStorage 兜底、状态灯

### 工具
- `starter/`：1920×1080 等比缩放、6 KPI、地图、7 类图表、滚动工单、播报、预警
- `scripts/new-screen.mjs`：一键生成新工程
- `scripts/qa.mjs`：静态体检（重复 id、占位文案、资源、绑定路径、离线依赖）
- `scripts/serve.mjs`：零依赖预览服务器
- `scripts/fetch-templates.mjs`：拉取上游模板
- `scripts/build-catalog.mjs`：生成目录
- `scripts/bundle.mjs`：打包单文件 prompt（min / chat / full）

### 文档
- `SKILL.md`：跨 harness 的 7 步工作流
- `AGENTS.md`、`install/`：Claude Code / Codex / Cursor / Cline / 通用 prompt
- 需求提炼、模板改造、交付部署三篇流程文档

### 已知限制
- 上游模板为 2018–2019 年技术栈（jQuery + ECharts 2/3/4），知识库以「借鉴布局」为主
- 3D/视频流/第三方地图授权需项目侧确认
- 预览图为压缩缩略图，不替代原模板
