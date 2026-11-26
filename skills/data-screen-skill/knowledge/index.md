# 数据大屏知识库 · 总索引

> 来源：Gitee 开源项目 [DaShuJuZhiDaPingZhanShi](https://gitee.com/lvyeyou/DaShuJuZhiDaPingZhanShi)（MIT，作者 Lang / lvyeyou），
> 共 12 个行业、25 套可运行模板，抓取于 2026-11-26，commit `75a203b`。
> 本知识库不是源码副本，而是**结构化拆解**：布局、配色、模块、图表写法、改造步骤、坑位。

## 0. 先看这里：三条使用路径

| 你的任务 | 读什么 | 产出 |
|---|---|---|
| 从 0 做一个大屏 | `workflow/brief-extraction.md` → `patterns/layout-archetypes.md` → 对应 `templates/*.md` → `starter/` | 新工程目录 |
| 改造一套现有模板 | `workflow/template-surgery.md` → 对应 `templates/*.md` | 在原模板目录上定向修改 |
| 接真实数据 | `data/data-contract.md` → `data/adapter-guide.md` | `adapter.js` + 接口映射 |

不确定选哪套模板时，用下面的决策树，不要从头读 12 篇文档。

## 1. 30 秒选型决策树

```
用户要什么？
├─ 通用汇报 / 城市总览 / 不知道选什么
│   → general-blue（A1 三栏中心地图，最好改）
├─ 物流 / 快递 / 供应链
│   → logistics（A2，中心流向地图 + 强切角）
├─ 交通 / 高速 / 交警 / 大量实时指标
│   → highway（A2，信息密度最高）
├─ 视频监控 / 安防 / 卡口
│   → traffic-video（A3，视频宫格 + 资源树）
├─ 政务 / 数据中台 / 系统架构
│   → gov-neon（A5，低密度叙事，中心关系图）
├─ 税务 / 大厅 / 渠道监控
│   → tax（A4，网格卡片）
├─ 社区 / 网格 / 街道
│   → community（A4，中心社区地图）
├─ 医疗 / 医院 / 卫健
│   → medical（A2，三栏 + 洁净青）
├─ 气象 / 环境 / 工业监控
│   → weather（A6，荧光终端风，视觉差异化最强）
├─ 金融 / 风控 / 信用评级
│   → finance-risk（A4，表格为主，严谨藏青）
├─ 电商 / 零售 / 运营
│   → retail（A1，经营看板）或 operation（A4，增长看板）
├─ 车联网 / 新能源 / 车队
│   → vehicle（A3，全屏地图 + 浮层）
├─ IoT / 设备 / 运维
│   → device（A4，大色块 KPI）或 ops-map（A3，真实底图）
├─ 门店 / 营业厅 / 连锁
│   → store（A4，排行榜 + 效能）
└─ 需要 3D / 展厅冲击力
    → land-3d（A3，ECharts GL 3D 地图）
```

## 2. 布局原型（Archetype）

| 代号 | 名称 | 适用 | 代表模板 |
|---|---|---|---|
| A1 | 三栏 · 中心地图 | 通用、区域态势、汇报 | general-blue、retail、tourism |
| A2 | 三栏 · 左中右多面板 | 高信息密度、指挥中心 | highway、logistics、medical |
| A3 | 全屏 GIS 底图 · 浮层卡片 | 空间为主、点位/轨迹 | vehicle、ops-map、land-3d |
| A4 | 网格卡片 · KPI + 图表 | 经营分析、统计、设备 | tax、device、store、stats |
| A5 | 低密度叙事 · 中心主视觉 | 架构/关系/汇报型 | gov-neon |
| A6 | 硬边终端风 · 仪表盘 | 气象、工业、差异化展厅 | weather、ops-ring |

详细尺寸、CSS 骨架、断点策略见 `patterns/layout-archetypes.md`。

## 3. 视觉主题速查

| 主题 | 背景 | 主色 | 强调色 | 适合 |
|---|---|---|---|---|
| 深蓝科技（默认） | `#030a16 → #061428` | `#35d6ff` | `#ffc93c` | 90% 的政务/城市/交通 |
| 藏青金融 | `#0c0f2b` | `#003bcf` / `#487bff` | `#ffffff` | 银行、风控、评级 |
| 荧光终端 | `#000000` | `#d8ff3e` | `#fff45c` | 气象、工业、展厅 |
| 电光政务 | `#020a18` | `#00a8ff` | `#aeff00` | 数据中台、系统架构 |
| 青绿物流 | `#071a33` | `#0e94ea` | `#ffc000` | 物流、供应链 |
| 浅色舆情 | `#ffffff` / `#f5f8fc` | `#337ab7` | `#d9534f` | 亮环境投屏、网页端 |

完整配色、字体、面板质感、纹理与禁忌见 `patterns/visual-language.md`。

## 4. 文件地图

```
knowledge/
├─ index.md                  ← 你在这里
├─ catalog.json              机器可读目录（25 套，含扫描字段）
├─ catalog.meta.json         人工提炼元数据（选型用）
├─ templates/                12 篇模板拆解（按视觉家族分组）
├─ patterns/
│  ├─ layout-archetypes.md   A1-A6 布局骨架 + CSS
│  ├─ visual-language.md     配色/字体/面板/纹理/禁忌
│  ├─ chart-recipes.md       ECharts 5 图表配方（20+）
│  ├─ motion-interaction.md  数字滚动/表格轮播/视图切换
│  └─ quality-bar.md         交付前 40 项检查
├─ data/
│  ├─ data-contract.md       统一数据契约（必读）
│  ├─ adapter-guide.md       6 种数据源接入指南
│  └─ schema.json            JSON Schema
└─ workflow/
   ├─ brief-extraction.md    从对话提炼需求
   ├─ template-surgery.md    定向改造模板
   └─ delivery.md            交付物清单与话术
```

## 5. 三种改造模式

| 模式 | 何时用 | 做法 | 风险 |
|---|---|---|---|
| **R · Remix 原模板** | 客户指定要这套、时间紧 | 整目录复制 → 替换文案/数据/配色 → 保留原技术栈 | 老 ECharts 2/3 API、切图改色难 |
| **M · Modern 重建**（默认推荐） | 新项目、要长期维护 | 用 `starter/` 的现代基线，按模板的布局/配色重画 | 需要重新实现视觉细节 |
| **H · Hybrid 混合** | 原模板布局值钱、技术栈太旧 | 保留 HTML 结构，替换图表层与数据层 | 两套逻辑易冲突，需逐个面板迁移 |

默认选 M：starter 已内置等比缩放、数据适配层、6 类图表、滚动表、状态灯，
比 2019 年的 jQuery + ECharts 4 更可靠，也更容易被 AI 精准修改。

## 6. 三条硬规则

1. **数据与视图分离**：图表只读 `DashboardData`，不直接碰网络（见 `data/data-contract.md`）。
2. **先结构后像素**：先定 KPI / 模块 / 图表类型，再调颜色和装饰；反过来一定返工。
3. **示例数据必须可识别**：所有假数据在页面状态灯标 `示例数据`，绝不把编造数字当真实业务。

## 7. 上游模板的已知技术债

- ECharts 版本混杂：2.2.7 / 3.7.3 / 4.0.3 / 4.0.4 / 4.1，部分 `echarts-all.js` 含旧地图包。
- 布局方案混杂：`html{font-size:width/20}` 的 rem、`transform:scale`、固定 px、flex 四种并存。
- 大量视觉依赖切图（PNG 边框/切角/光效），换色需要重新出图；现代做法用 CSS `clip-path` + 渐变 + 伪元素。
- 地图依赖 `china.js`（ECharts 2/4 专用），ECharts 5 需改为 GeoJSON + `registerMap`。
- 无数据层抽象，数值直接写死在 HTML/JS 中；这是改造时工作量最大的部分。

这些不是否定原模板——它们的**布局与信息组织**非常成熟，正是本知识库要复用的部分。
