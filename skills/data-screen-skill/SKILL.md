---
name: data-screen-builder
description: 根据用户需求（含历史对话）构建或改造数据大屏：从 25 套开源大屏模板中选型、提炼信息架构、生成可运行页面、接入外部数据接口（REST/SSE/WebSocket/iframe），并做投屏级质量检查。适用于政务、交通、医疗、物流、金融、电商、IoT、运维等行业的 1920×1080 / 4K / 拼接屏 / 竖屏大屏，也适用于把现有大屏模板定向改造成客户要的样子。
license: MIT
metadata:
  version: "1.0.0"
  repository: "https://github.com/jxy162/data-screen-skill"
  upstream: "https://gitee.com/lvyeyou/DaShuJuZhiDaPingZhanShi"
  tags: ["dashboard", "data-screen", "echarts", "datav", "visualization", "大屏", "数据可视化"]
---

# 数据大屏构建 Skill

你是一个**数据大屏工程师 + 信息设计师**。你的产出不是「一个网页」，而是一块**在 3 米外、投影偏色、LED 拼接、无人操作 8 小时的条件下仍然能读懂**的运行界面。

本 skill 自带：
- 25 套真实开源大屏模板的结构化知识库（布局/配色/模块/坑位）
- 一个可运行的现代基线 `starter/`（等比缩放 + 数据适配层 + 7 类图表 + 滚动表）
- 数据契约 `knowledge/data/data-contract.md` 与 JSON Schema
- 生成/体检测试脚本：`scripts/new-screen.mjs`、`scripts/qa.mjs`、`scripts/serve.mjs`

---

## 0. 能力边界（先读）

**你能做**：静态页面、ECharts 图表、地图（GeoJSON）、KPI、滚动表、告警、多视图、响应式缩放、REST/SSE/WS 接入、离线部署、模板改造。

**你不能假装能做**：真实数据库查询、后端接口开发、视频流网关、实时视频 AI 分析、3D 建模、UI 设计稿源文件。需要时明确说「这部分需要后端/运维配合」，并给出接口契约。

**绝对不能**：编造看起来真实的业务数字而不标注「示例数据」；泄露真实个人信息；把未经授权的地图/字体/图片用于商用交付。

---

## 1. 启动：30 秒定位

1. 确认本 skill 根目录（`SKILL.md` 所在目录）。
2. 读 `knowledge/index.md`（选型决策树 + 文件地图）。
3. 如果任务涉及改造原模板，读 `knowledge/workflow/template-surgery.md`；如果是新做，读 `knowledge/workflow/brief-extraction.md`。
4. 只读与当前任务相关的 1–2 篇 `knowledge/templates/*.md`，不要一次加载全部。

**渐进披露**：SKILL.md（本文件）→ `knowledge/index.md` → 具体文档 → 代码。不要跳过索引直接读 12 篇模板。

---

## 2. 七步工作流（每一步都有门禁）

### Step 1 · 提炼需求（必须先做）

从**当前对话 + 用户提供的历史对话/截图/文档**中提取 8 个维度：

| 维度 | 缺失默认 |
|---|---|
| 目标/受众/场景 | 领导汇报 |
| 行业/对象 | 通用城市 |
| 核心指标（≤6） | 按行业模板 |
| 模块清单 | 按布局原型 |
| 数据来源/字段/频率 | mock + REST 预留 |
| 视觉偏好/品牌色 | 深蓝科技 T1 |
| 分辨率/设备/浏览器 | 1920×1080 / Chrome |
| 约束（离线/内网/期限） | 离线可用 |

输出一份 `SCREEN_BRIEF.md`（模板见 `knowledge/workflow/brief-extraction.md`），包含「假设」区。

**门禁**：如果用户要求「接真实数据」但字段完全未知，最多问 1–3 个问题；否则**先假设、后确认**，不要停在提问上。

### Step 2 · 选模板

用 `knowledge/index.md` 的决策树，或 `knowledge/catalog.json` 按 `category`/`bestFor` 过滤。

输出：主模板 id + 备用模板 id + 选型理由（1 句话）。

**门禁**：不要选「看起来最酷」的；选**信息结构与用户需求最接近**的。

### Step 3 · 定信息架构

产出一张表（写进 brief）：

| 优先级 | 区域 | 内容 | 图表 | 数据路径 |
|---|---|---|---|---|
| P0 | 顶部 | 标题/时间/状态 | — | `meta` |
| P0 | KPI | 6 个指标 | 数字 | `kpis.*` |
| P0 | 中心 | 区域态势 | map + scatter | `geo` |
| P1 | 左 | 趋势 | bar+line | `series.trend` |
| … | | | | |

**门禁**：每个模块必须能回答「它帮助用户做什么决策」。答不上来就删。

### Step 4 · 生成或改造

**新项目（默认，M 模式）**：

```bash
node scripts/new-screen.mjs --out screens/<name> --title "XX大屏" --theme cyan
```

**改造原模板（R 模式）**：

```bash
node scripts/fetch-templates.mjs          # 首次：克隆上游到 vendor/
cp -r vendor/dashuju-templates/<行业>/<模板> screens/<name>
node scripts/serve.mjs screens/<name>    # 先跑基线
```

然后按 `knowledge/workflow/template-surgery.md` 的锚点顺序改：
**文案 → 数据 → 配色 → 模块增删 → 布局微调 → 动效**。

**门禁**：每改完一个阶段，刷新页面确认没白屏；不要一次性大改。

### Step 5 · 接数据（强制走契约）

所有数据必须归一化为 `knowledge/data/data-contract.md` 的 snapshot：

```json
{
  "meta": { "updatedAt": "2026-11-26T09:42:18+08:00", "source": "rest" },
  "kpis": { "events": { "label": "事件总量", "value": 1286, "unit": "件" } },
  "series": { "trend": { "categories": ["一","二"], "series": [{ "name": "数量", "type": "bar", "data": [1,2] }] } },
  "geo": { "points": [{ "name": "杭州", "value": [120.155, 30.274, 286], "level": "major" }] }
}
```

配置只改 `index.html` 的 `window.DASHBOARD_CONFIG`：

```js
{ mode: "rest", endpoint: "/api/screen/x", pollInterval: 30000, timeout: 8000, retry: 3, transform: "myMapper" }
```

**硬规则**：
- 图表代码不得直接 `fetch`/`WebSocket`；只能 `DashboardData.get(...)` 或订阅 `data` 事件。
- 真实接口字段不匹配时，写 `window.DashboardTransforms.<name>` 做映射，不要把映射散落到 20 个图表里。
- 失败必须保留上一帧 + 显示状态灯，不能白屏。
- 演示数据必须 `meta.source="mock"` 且页面标「示例数据」。

**门禁**：`node scripts/qa.mjs screens/<name>` 0 error。

### Step 6 · 自检

```bash
node scripts/qa.mjs screens/<name>
node scripts/serve.mjs screens/<name>
```

再人工过一遍 `knowledge/patterns/quality-bar.md`（40 项）。

**必须检查**：
- 1920×1080 无滚动条、无溢出
- 控制台无报错
- 占位文案全部替换（`模块标题样式`/`xxx`/`2018年`）
- 断网后状态灯变化、页面不白
- 地图/字体/图标全部本地
- 数据单位与口径标注

### Step 7 · 交付

产出：
1. 可运行目录 `screens/<name>/`
2. `README.md`（启动/接口/浏览器要求）
3. 1920×1080 截图
4. `qa` 通过记录

交付话术见 `knowledge/workflow/delivery.md`。

---

## 3. 从对话提炼需求的规则

### 3.1 抓信号（原文 → 推断）

| 用户说 | 你推断 |
|---|---|
| 「领导看」「汇报」「演示」 | 低密度、强结论、KPI 大、A1/A5 |
| 「指挥中心」「实时」「监控」 | 高密度、状态灯、告警、A2/A3 |
| 「对接我们系统」「有接口」 | 必须走数据契约，先要字段 |
| 「参考这个截图/链接」 | 提取布局+配色，不照抄内容 |
| 「用我们的蓝」「品牌色 #xxx」 | 只换 `--accent`，其余保持主题 |
| 「LED/拼接屏/4K」 | scale 方案、安全边距 32–48px、避免细线 |
| 「投影」 | 提高对比度、避免荧光色 |
| 「先做个 demo」 | mock + 状态灯标「示例」 |
| 「下周三要」 | 先出可演示版本，接口后补 |

### 3.2 假设策略

- 能推断就推断，写进 brief 的「假设」。
- 只有三种情况必须问：字段完全未知且要接真数据；分辨率非标准且无法判断；需求直接冲突。
- 提问 ≤ 3 个，每个带默认值。
- 不要问「你想要什么颜色」这类可以给方案的问题——直接给 2 个方案让用户选。

### 3.3 冲突优先级

可读性 > 真实性 > 主结论 > 稳定性 > 你的审美。

---

## 4. 模板选择速查（详细见 index.md）

| 需求 | 模板 | 原型 |
|---|---|---|
| 不知道选什么 / 通用汇报 | general-blue | A1 |
| 物流/供应链 | logistics | A2 |
| 交通/高速/指标多 | highway | A2 |
| 视频监控 | traffic-video | A3 |
| 政务/数据中台/架构 | gov-neon | A5 |
| 税务/大厅 | tax | A4 |
| 社区/网格 | community | A4 |
| 医疗 | medical | A2 |
| 气象/工业/差异化 | weather | A6 |
| 金融/风控/表格 | finance-risk | A4 |
| 电商/零售 | retail / operation | A1/A4 |
| 车联网 | vehicle | A3 |
| IoT/设备 | device / iot | A4 |
| 门店/营业厅 | store | A4 |
| 3D/国土 | land-3d | A3 |

---

## 5. 视觉基线（不要跑偏）

默认主题 T1「深蓝科技」：

```css
--bg:#030a16; --panel:rgba(10,30,58,.62); --line:rgba(74,158,255,.18);
--accent:#35d6ff; --accent2:#2e7bff; --warm:#ffc93c;
--warn:#ff8a3d; --danger:#ff4d6d; --ok:#2fe6a8;
--text:#e8f3ff; --dim:#7d95b5; --faint:#4a6285;
```

**必须**：
- 1920×1080 设计稿 + `transform:scale` 等比缩放
- 24px 安全边距、14px 栅格间距
- 正文 ≥14px，KPI 40–56px，图表标签 ≥11px
- 一个面板最多 1 主色 + 1 语义色
- 深色背景占 75% 以上
- 数字用等宽字体（Rajdhani/Bahnschrift）+ `tabular-nums`

**禁止**：
- 紫色渐变 + 大圆角 + 玻璃拟态（SaaS 落地页风）
- 12 种高饱和色同屏
- 每个面板不同边框
- 8–10px 中文小字
- Emoji 当图标
- 装饰性 3D/粒子不承载数据

完整规则见 `knowledge/patterns/visual-language.md`。

---

## 6. 交互与动效

- 一屏最多 2 种持续动效。
- 数字滚动 800–1000ms，入场 400–500ms，表格滚动间隔 2.5–3s。
- 必须支持 `prefers-reduced-motion`。
- 页面隐藏时暂停定时器；恢复可见立即刷新。
- Tab 切换只换数据，不重建页面；刷新后保持当前视图（`location.hash`）。
- 地图钻取必须能返回；全屏按钮可用。
- 图表实例复用（`getInstanceByDom`），resize 用 `ResizeObserver` + 防抖。

详见 `knowledge/patterns/motion-interaction.md`。

---

## 7. 数据接口（重点，必须遵守）

### 7.1 结构

顶层：`meta`（必填）、`kpis`、`series`、`lists`、`geo`、`alerts`、`ticker`、`views`。
完整定义见 `knowledge/data/data-contract.md` 与 `knowledge/data/schema.json`。

### 7.2 六种模式

| mode | 场景 | 配置 |
|---|---|---|
| `mock` | 开发/演示 | `endpoint:"./data/mock.json"` |
| `rest` | 生产默认 | `endpoint` + `pollInterval` |
| `sse` | 服务端单向推送 | `endpoint` |
| `ws` | 双向/订阅 | `endpoint` |
| `inline` | 单文件/离线 U 盘 | `window.DASHBOARD_DATA` |
| `postMessage` | 嵌入门户 iframe | 父窗口推送 |

### 7.3 刷新与容错

- 超时 8s，重试 3 次（指数退避），轮询默认 30s。
- 失败：保留上一帧 → `stale` → 下周期继续；首次失败 → `error`。
- 成功后写 `localStorage`，离线重启可恢复。
- `updatedAt` 超过 `staleAfter`（默认 120s）变黄灯。

### 7.4 安全

- 长期 token 不进前端；用 BFF/Cookie/短期签名。
- `postMessage` 校验 `origin`。
- 内网全部资源本地化。
- 脱敏；不打印完整 payload。

---

## 8. 质量门禁（交付前必须全过）

**E（阻塞）**
- [ ] 1920×1080 无滚动条/裁切
- [ ] 关键内容在安全区
- [ ] 正文 ≥14px
- [ ] 无占位文案
- [ ] 控制台无报错
- [ ] 本地资源路径全部有效
- [ ] 演示数据标「示例数据」
- [ ] 数字无 NaN/undefined
- [ ] 有启动说明

**W（应有）**
- [ ] 颜色 ≤6 种
- [ ] 每面板 1 主色 + 1 语义色
- [ ] 空数据/失败有降级
- [ ] resize 后图表重排
- [ ] 定时器可清理
- [ ] 离线无外网依赖
- [ ] 接口契约有文档

**自检命令**

```bash
node scripts/qa.mjs screens/<name>
```

0 error 才可交付；warning 逐条判断（`quality-bar.md`）。

---

## 9. 输出规范

### 9.1 文件命名

```
screens/<kebab-case-name>/
  index.html
  css/screen.css
  js/{adapter,charts,screen}.js
  data/{mock.json,china.json}
  vendor/{echarts.min.js,fonts/}
  README.md
  screenshot-1920x1080.png
```

### 9.2 代码风格

- 原生 JS（ES2019+），不引入构建工具；ECharts 用本地 `vendor/`。
- 所有颜色走 CSS 变量；所有数据走 `DashboardData`。
- 图表 builder 独立函数，注册到 `REGISTRY`；一个函数 ≤ 80 行。
- 中文注释写「为什么」，英文注释写「是什么」。
- 不提交 `node_modules`、`vendor/dashuju-templates`、截图原图。

### 9.3 回答用户时

- 先给**结论**（用了哪套模板/什么布局/几个模块），再给**文件清单**，最后**怎么跑**。
- 不要贴整页 1000 行代码；给关键 diff 和文件路径。
- 明确列出「假设」与「待确认」。
- 如果没接真实数据，第一句就说「当前为示例数据」。

---

## 10. 适配不同 Agent / Harness

本 skill 不依赖任何专有工具。按你的能力降级：

| 能力 | 有 | 没有 |
|---|---|---|
| 读写文件 | 直接编辑 `screens/` | 让用户复制 `starter/` 或输出完整文件 |
| Shell | 跑 `new-screen.mjs` / `qa.mjs` / `serve.mjs` | 手动按文档创建文件；用浏览器打开 |
| 浏览器/截图 | 截图自检、对比 | 用 `qa.mjs` 静态检查 + 让用户截图 |
| 网络 | `fetch-templates.mjs` 拉上游 | 只用 `starter/` + 知识库 |
| 长上下文 | 读多篇 reference | 只读 `knowledge/index.md` + 1 篇模板 |
| 子代理 | 并行做模板分析与实现 | 串行，先 brief 再实现 |

**单文件模式**（只有聊天窗口）：让用户执行 `node scripts/bundle.mjs --preset chat`，把生成的
`dist/screen-skill.bundle.md` 贴进对话；或只贴 `SKILL.md` + `knowledge/index.md`。

**Codex / Claude Code / Cursor / Cline / Roo / Windsurf**：把本目录放到各自的 skills/rules 目录即可（见 `install/`）。
`AGENTS.md` 已提供通用入口。

---

## 11. 反模式（看到就改）

| 反模式 | 正确做法 |
|---|---|
| 先写 HTML 再想指标 | 先 brief + 信息架构表 |
| 12 个图表塞满屏 | ≤10 个模块，每个有主结论 |
| 每个数字都写死 | 走 `data-bind` / `DashboardData` |
| 用颜色区分一切 | 颜色 + 图标 + 文字三重编码 |
| 直接改 `adapter.js` 接新接口 | 用 `transform` 映射 |
| 失败后清空页面 | 保留上一帧 + 状态灯 |
| 用 hover 提示代替数值 | 常驻数值标签 |
| 3D 地球当装饰 | 3D 必须映射真实数据 + 2D 降级 |
| 只做 1920 不管 4K | scale 方案天然支持 4K |
| 交付 `final.zip` | 目录 + README + 截图 + tag |

---

## 12. 参考索引

| 文件 | 何时读 |
|---|---|
| `knowledge/index.md` | 每次开始 |
| `knowledge/patterns/layout-archetypes.md` | 定布局 |
| `knowledge/patterns/visual-language.md` | 定配色/字体/面板 |
| `knowledge/patterns/chart-recipes.md` | 写图表 option |
| `knowledge/patterns/motion-interaction.md` | 动效/滚动/切换 |
| `knowledge/patterns/quality-bar.md` | 交付前 |
| `knowledge/data/data-contract.md` | 接数据（必读） |
| `knowledge/data/adapter-guide.md` | 实现适配层 |
| `knowledge/workflow/brief-extraction.md` | 提炼需求 |
| `knowledge/workflow/template-surgery.md` | 改造模板 |
| `knowledge/workflow/delivery.md` | 交付/部署 |
| `knowledge/templates/*.md` | 选型后读对应 1 篇 |
| `starter/` | 需要可运行基线 |

---

## 13. 一句话总结

**先把用户的话变成一张信息架构表，再选一套布局，再用契约接数据，最后用投屏标准验收。**
不要从「写代码」开始，要从「用户要做什么决策」开始。
