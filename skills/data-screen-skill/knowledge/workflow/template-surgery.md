# 定向改造模板（Template Surgery）

> 目标：**最小改动**得到客户要的效果，而不是把模板重写一遍。
> 先决定模式，再按锚点顺序改；每一步都可回退。

## 0. 先选模式

| 条件 | 模式 |
|---|---|
| 客户指定这套模板 / 只要 1–2 天 / 不改技术栈 | **R** 原模板 Remix |
| 新项目 / 要长期维护 / 要接真实接口 | **M** 用 starter 重建 |
| 布局很好但 ECharts 2/3 太旧 | **H** 保留 HTML/CSS，替换图表层 |

不确定时选 M。原模板的**布局与信息结构**是资产，代码不是。

## 1. R 模式：原模板改造

### 1.1 复制整个目录（不要只拷 HTML）

```bash
cp -r vendor/dashuju-templates/智慧城市/大数据可视化展板通用模板 screens/my-board
```

相对路径（`css/`、`js/`、`images/`、`fonts/`）全部依赖目录结构。只拷 `index.html` 必然白屏。

### 1.2 先跑基线

```bash
node scripts/serve.mjs screens/my-board
# 浏览器 1920×1080 截图，确认原始状态正常
```
基线不正常（缺图/报错）先修基线，再改内容。

### 1.3 锚点地图

| 要改什么 | 去哪找 |
|---|---|
| 标题 | `<title>`、`.head h1`、`<h1>` |
| 配色 | `css/*.css` 顶部的 `background`、`color`、`border-color`；搜索高频 hex |
| 数值 | 搜索 `class="counter"`、`data-*`、`innerHTML` 赋值、`data:[...]` |
| 图表 | 搜 `echarts.init`、`setOption`、`series`、`option =` |
| 模块增删 | `.mainbox > ul > li`、`.boxall`、`.panel` |
| 缩放 | `html{font-size}`、`$(window).resize`、`transform:scale` |
| 地图 | `china.js`、`registerMap`、`geoCoordMap` |

### 1.4 修改顺序（不要跳）

```
1) 文案/标题/单位
2) 数值与图表 data
3) 主色/背景/面板色
4) 模块增删（保持 flex/grid 比例）
5) 布局微调（间距/字号）
6) 动效与交互
```

先改颜色再改结构，会导致返工；先删模块再调布局，会留下空洞。

### 1.5 换色策略

- **纯 CSS 颜色**：直接替换 hex；用「查找全部 → 替换」保持一致性。
- **切图边框/光效**：PNG 无法改色。方案：
  1. CSS `filter: hue-rotate()`（快，但会连带图片内容偏色）；
  2. 用 `mask-image` + `background:accent` 重着色（推荐，需图片是单色/透明）；
  3. 重画为 CSS（`clip-path` + 渐变 + 伪元素），长期最优。
- **渐变色**：搜 `linear-gradient` / `rgba(`，统一到主题变量。

### 1.6 增删模块

- **删**：删掉对应 `<li>`/`<div class="boxall">`，其余模块 `flex:1` 会自动撑满；检查是否留下 `margin-bottom` 空洞。
- **增**：复制一个同结构面板，改 `id`（必须唯一）、标题、图表初始化；在 `resize` 里确认新图表被纳入（多数模板只 resize 已知实例）。
- **换位置**：只改 DOM 顺序，不改 CSS 宽度；三栏比例在 `.mainbox>ul>li{width:30%}` 一类规则里。

### 1.7 ECharts 版本迁移

| 旧写法（2/3/4） | ECharts 5 |
|---|---|
| `itemStyle:{ normal:{...}, emphasis:{...} }` | `itemStyle:{...}` + `emphasis:{...}` |
| `textStyle` 在 series 顶层 | 移到 `label` / `axisLabel` / `title.textStyle` |
| `grid:{ x, y, x2, y2 }` | `grid:{ left, top, right, bottom }` |
| `legend:{ x, y }` | `legend:{ left, top }` |
| `map` 用 `china.js` 全局注册 | GeoJSON + `echarts.registerMap("china", geo)` |
| `series[i].markPoint.data[].xAxis/yAxis` | 用 `coord:[x,y]` 或 `value` |
| `calculable:true` | 删除（5 不支持） |
| `dataZoom` 的 `start/end` | 保留，但样式属性改为 `textStyle` |

**不要**把 ECharts 2 的 option 直接喂给 5——会静默失败或图表空白。

## 2. M 模式：用 starter 重建

```bash
node scripts/new-screen.mjs --out screens/city-ops --title "XX市城市运行指挥中心" --theme cyan
```

然后按模板的**信息架构**替换 starter 的模块：

| 模板元素 | starter 对应 |
|---|---|
| 顶部标题 + 时钟 | `.top` |
| KPI 翻牌 | `.kpi-row` + `data-bind` |
| 中心地图 | `#chart-map` + `geo` 数据 |
| 左右图表面板 | `.col-left` / `.col-right` 的 `<section class="panel">` |
| 滚动表 | `#ticket-track` + `lists.tickets` |
| 底部播报 | `#ticker-track` + `ticker` |

只改 `data/mock.json` 和面板标题即可得到 70% 的效果；剩下 30% 是配色和装饰。

## 3. H 模式：混合迁移

1. 保留原 `index.html` 的 DOM 结构与 class。
2. 删除原 `echarts*.js` 与 `jquery`（如果只用于图表）。
3. 引入 `vendor/echarts.min.js` + `adapter.js` + `charts.js`。
4. 逐个面板：把原 `echarts.init` 的 option 迁到 `charts.js` 的 builder。
5. 保留原 CSS，但把硬编码颜色换成 CSS 变量。
6. 每迁完一个面板截图对比，避免一次性全改。

**风险**：原 CSS 可能依赖 jQuery 动态加的 class；先 grep `addClass`/`toggleClass`。

## 4. 常见坑

| 现象 | 原因 | 修复 |
|---|---|---|
| 图表空白 | 容器高度 0 / 初始化时隐藏 | 显示后再 `resize()`；父级 `min-height:0` |
| 地图不着色 | 省份名不匹配 | 打印 GeoJSON 的 `properties.name` 对照 |
| 地图偏移 | GCJ-02 / WGS-84 混用 | 统一坐标系 |
| 刷新后滚动表跳回顶部 | `innerHTML` 重建 | 保留 track，只更新行内容 |
| 第二个图表不显示 | `id` 重复 | 全屏唯一 id |
| 颜色改了但边框没变 | 边框是 PNG | mask 重着色或重画 |
| 字体模糊 | rem 产生小数 px | 用整数 px 或 scale 方案 |
| 打印/截图空白 | canvas 未渲染完 | 等 `setOption` 后 `finished` 事件再截图 |
| 移动目录后白屏 | 相对路径断了 | 整目录复制，不要拆文件 |

## 5. 改造后自检

```bash
node scripts/qa.mjs screens/my-board
```

- [ ] 搜索不到原模板的示例文案（`模块标题样式`、`xxx`、`2018年`）
- [ ] 所有 `id` 唯一，所有 `data-bind` 路径存在
- [ ] 图表在 resize 后重排
- [ ] 地图/字体/图标均本地化
- [ ] 1920×1080 截图与设计意图一致
- [ ] 断网后不白屏
- [ ] 原模板 LICENSE 与来源已在 NOTICE 中保留
