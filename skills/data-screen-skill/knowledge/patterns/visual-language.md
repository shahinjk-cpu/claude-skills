# 视觉语言：配色、字体、面板、纹理

> 从 25 套模板里提炼出的共性 + 现代修正。目标不是「炫」，而是**在 3 米外、投影偏色、LED 亮度不均的条件下仍然可读**。

## 1. 六套可直接用的主题

### T1 深蓝科技（默认，覆盖 90% 场景）

```css
--bg-0:#030a16; --bg-1:#061428; --bg-2:#08203c;
--panel:rgba(10,30,58,.62);
--line:rgba(74,158,255,.18);
--accent:#35d6ff; --accent-2:#2e7bff;
--warm:#ffc93c; --warn:#ff8a3d; --danger:#ff4d6d; --ok:#2fe6a8;
--text:#e8f3ff; --dim:#7d95b5; --faint:#4a6285;
```
来源：general-blue `#000d4a + #02a6b5 + #399bff + #ffeb7b`；logistics `#071a33 + #0e94ea`。

### T2 藏青金融

```css
--bg-0:#080a1c; --bg-1:#0c0f2b; --panel:rgba(16,22,56,.7);
--accent:#487bff; --accent-2:#003bcf; --warm:#ffc93c;
--text:#f2f5ff; --dim:#9aa6cc;
```
特点：低饱和、无霓虹、表格优先。来源：finance-risk。

### T3 荧光终端（差异化最强）

```css
--bg-0:#000; --bg-1:#050505;
--accent:#d8ff3e; --accent-2:#9bbf00; --danger:#ff2b2b;
--text:#e9ffcf; --dim:#7f8f63;
--font-num:"OCR A", "DIN Alternate", ui-monospace;
```
特点：1px 细线、全大写英文、无圆角、无渐变。来源：weather。

### T4 电光政务

```css
--bg-0:#020a18; --accent:#00a8ff; --accent-2:#56a4ff;
--warm:#aeff00; --danger:#fd4275;
```
特点：大面积留白 + 中心关系图。荧光绿只做强调。来源：gov-neon。

### T5 青绿物流

```css
--bg-0:#071a33; --accent:#0e94ea; --accent-2:#00c2ff;
--warm:#ffc000; --magenta:#ff3dbe; --ok:#009f95;
```
特点：六边形纹理、切角边框、强中心地图。来源：logistics、community。

### T6 浅色舆情

```css
--bg-0:#f5f8fc; --panel:#ffffff; --line:#dce6f2;
--accent:#337ab7; --danger:#d9534f; --ok:#3c763d;
--text:#243447; --dim:#5b7091;
```
特点：适合亮环境、网页端；投 LED 时需提高对比度。来源：opinion。

## 2. 颜色使用规则

| 角色 | 占比 | 用法 |
|---|---|---|
| 背景 | 75–85% | 近黑/深蓝，带轻微渐变或纹理，不要纯 #000（除 T3） |
| 结构线 | 10% | `rgba(accent,.12–.25)` 的 1px 边框、分隔线 |
| 主强调 | 5% | 标题竖条、关键数字、主折线、选中态 |
| 语义色 | <5% | 红=告警、橙=预警、绿=正常、黄=关注 |
| 中性文字 | — | 正文 `#e8f3ff`，次要 `#7d95b5`，辅助 `#4a6285` |

**一条铁律**：一个面板里最多 1 个主色 + 1 个语义色 + 中性灰。
饼图/多系列最多 6 色，超过就合并为「其他」。

**语义色不要混用**：
- 红 = 故障/重大/下降（负向）
- 橙 = 预警/超时
- 黄 = 关注/目标
- 绿/青 = 正常/完成（正向）
- 紫/品红 = 只作品类区分，不做状态

**色弱友好**：红绿同时出现时，必须配图标/文字/形状（如 ▲▼、●○），不能只靠颜色。

## 3. 字体

```css
--font-cn: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", "Source Han Sans SC", sans-serif;
--font-num: "Rajdhani", "Bahnschrift", "DIN Alternate", "Arial Narrow", ui-monospace, monospace;
```

| 用途 | 字号 | 字重 | 备注 |
|---|---|---|---|
| 主标题 | 28–40px | 600 | 字间距 2–4px，可加轻微光晕 |
| 面板标题 | 16–18px | 600 | 左侧 2px 竖条 + 英文小标 |
| KPI 数字 | 40–56px | 600 | 等宽数字 `font-variant-numeric: tabular-nums` |
| KPI 标签 | 12–14px | 400 | `--dim` |
| 图表轴/图例 | 11–12px | 400 | 不要小于 10px |
| 表格正文 | 12–14px | 400 | 行高 1.4；投屏建议 14px |
| 英文辅助 | 9–11px | 500 | 全大写 + 2px 字距，降低存在感 |

**数字字体**：优先 `Rajdhani`（OFL，已随 starter 提供）、`Bahnschrift`（Windows 自带）、`DIN Alternate`（macOS）。
不要用 `DS-Digital` 做正文——只在纯数字翻牌上用，且必须提供 fallback。

**中文标题**：可用「优设标题黑」「阿里巴巴普惠体」「思源黑体 Heavy」。**商用字体务必确认授权**；不确定就用系统字体 + 字重/字距营造质感。

## 4. 面板anatomy（可直接复制）

```html
<section class="panel">
  <header class="panel-hd">
    <h2>事件趋势</h2>
    <span class="panel-en">EVENT TREND</span>
    <div class="panel-tools">…</div>
  </header>
  <div class="panel-bd"><div class="chart" id="chart-trend"></div></div>
</section>
```

```css
.panel{
  position:relative; display:flex; flex-direction:column; min-height:0;
  background:linear-gradient(180deg,rgba(10,30,58,.62),rgba(7,22,44,.78));
  border:1px solid rgba(74,158,255,.18);
}
/* 左上 / 右下角标 */
.panel::before,.panel::after{
  content:""; position:absolute; width:12px; height:12px; border-color:var(--accent); border-style:solid;
}
.panel::before{ left:-1px; top:-1px; border-width:1px 0 0 1px; }
.panel::after{ right:-1px; bottom:-1px; border-width:0 1px 1px 0; }
.panel-hd{
  height:42px; display:flex; align-items:center; gap:10px; padding:0 12px;
  background:linear-gradient(90deg,rgba(53,214,255,.10),transparent 60%);
  border-bottom:1px solid rgba(74,158,255,.12);
}
.panel-hd h2{ font-size:17px; padding-left:9px; position:relative; }
.panel-hd h2::before{ content:""; position:absolute; left:0; top:3px; bottom:3px; width:2px; background:var(--accent); box-shadow:0 0 8px var(--accent); }
```

**变体**：
- 切角面板：`clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px))`，配 1px 描边需用双层元素或 `filter: drop-shadow`。
- 顶部标题条：面板标题做成梯形/斜切，适合 A2/A6。
- 无边框：只用背景色差 + 4px 左侧色条，适合 A4 低密度。

## 5. 背景与纹理

| 纹理 | 做法 | 适用 |
|---|---|---|
| 细网格 | 两组 `linear-gradient` 1px，48px 间隔，透明度 3–5% | 通用 |
| 点阵 | `radial-gradient(circle, rgba(...) 1px, transparent 1px) 0 0/22px 22px` | 终端风、地图底 |
| 六边形 | SVG pattern 或 CSS `clip-path` 重复 | 物流、政企 |
| 星云/光斑 | 2–3 个 `radial-gradient` 大光斑，透明度 6–12% | A5、展厅 |
| 扫描线 | `repeating-linear-gradient(0deg, rgba(255,255,255,.03) 0 1px, transparent 1px 3px)` | 终端风，慎用 |
| 雷达环 | 绝对定位的圆环 + 旋转动画（15–30s） | 中心地图背后 |

**禁忌**：背景图整张 4K JPG（>2MB、拉伸模糊、换色困难）。用 CSS 渐变 + 轻量 SVG/PNG 叠加，控制在 300KB 内。

## 6. 光效与渐变

```css
/* 标题光晕：只加在标题和 KPI 数字上 */
text-shadow: 0 0 18px rgba(53,214,255,.45);

/* 主数字渐变 */
background:linear-gradient(180deg,#fff,#9fe8ff);
-webkit-background-clip:text; color:transparent;

/* 折线面积 */
areaStyle:{ color:new echarts.graphic.LinearGradient(0,0,0,1,[
  {offset:0,color:"rgba(53,214,255,.28)"},{offset:1,color:"rgba(53,214,255,0)"}]) }
```
**克制**：一屏最多 2 处强光晕（标题 + 主 KPI）。每个面板都发光 = 没有重点。

## 7. 明确不要做

- ❌ 紫蓝渐变 + 大圆角 + 玻璃拟态（SaaS 落地页风，不像大屏）
- ❌ 12 种高饱和颜色同屏（尤其饼图）
- ❌ 每个面板都用不同的边框样式
- ❌ 中文用 8–10px 小字「显得精致」（投屏就是看不清）
- ❌ 用 Emoji 当图标
- ❌ 大面积纯白背景 + 细灰字（亮环境下对比度不足）
- ❌ 装饰性 3D 地球/粒子，不承载任何数据
- ❌ 动效满屏飞（数据滚动 + 地图涟漪 + 飞线 + 扫光 + 翻牌同时开）

## 8. 10 分钟换肤清单

1. 改 `--bg-0/1/2`、`--accent`、`--accent-2`、`--warm` 五个变量。
2. 检查 6 类图表配色是否只用了主题色 + 语义色。
3. 检查标题光晕与背景光斑是否同色系。
4. 截图看整体明度：背景应占 75% 以上面积。
5. 用灰度截图检查层级：去掉颜色后，是否还能分清标题/数字/正文。
6. 投屏实测：3 米外能否读清面板标题和 KPI 标签。
