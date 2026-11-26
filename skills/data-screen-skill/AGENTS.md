# AGENTS.md

本仓库是一个 **agent-agnostic** 的数据大屏构建 skill。

## 如果你要「使用」这个 skill

先读 `SKILL.md`，再按需读 `knowledge/index.md`。不要一次加载全部文档。

最小工作流：

1. 从对话提炼 brief（`knowledge/workflow/brief-extraction.md`）
2. 选模板（`knowledge/index.md` 决策树）
3. 用 `node scripts/new-screen.mjs --out screens/<name> --title "<标题>"` 生成基线
4. 改 `data/mock.json` + `css/screen.css` + `js/charts.js`
5. 接数据：只改 `index.html` 的 `DASHBOARD_CONFIG`，用 `transform` 映射字段
6. 跑 `node scripts/qa.mjs screens/<name>`，0 error 再交付
7. 写 `screens/<name>/README.md` + 1920×1080 截图

## 硬规则

- 图表代码不得直接 `fetch` / `WebSocket`，统一走 `DashboardData`。
- 演示数据必须标「示例数据」；不得编造真实业务数字。
- 不得把长期 token 写进前端。
- 所有资源（ECharts/字体/GeoJSON）必须可本地化。
- 改原模板时整目录复制，不要只拷 HTML。
- 每次修改大屏都要跑 `qa.mjs`。

## 如果你要「维护」这个仓库

- 知识库改动后，更新 `CHANGELOG.md`。
- `knowledge/catalog.meta.json` 是人工数据源；`knowledge/catalog.json` 由 `scripts/build-catalog.mjs` 生成。
- 新增模板：在 `catalog.meta.json` 加条目 → 跑 `fetch-templates.mjs` → `build-catalog.mjs` → 在对应 `knowledge/templates/*.md` 补章节。
- 新增图表配方：写进 `knowledge/patterns/chart-recipes.md`，并在 `starter/js/charts.js` 注册。
- 提交信息用中文/英文均可，说明「改了什么/为什么」。

## 目录

见 `README.md` 的「目录」一节。
