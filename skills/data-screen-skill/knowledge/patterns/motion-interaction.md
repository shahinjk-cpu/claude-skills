# 动效与交互

> 大屏动效的唯一目的是**引导注意力**，不是展示技术。
> 一个屏同时最多 2 种持续动效（例如：地图涟漪 + 表格滚动）。

## 1. 时长与缓动

| 场景 | 时长 | 缓动 |
|---|---|---|
| KPI 数字滚动 | 800–1000ms | `cubic-bezier(.22,.61,.36,1)` |
| 面板入场 | 400–500ms | 同上，位移 ≤ 8px |
| 视图切换 | 300–450ms | 淡入 + 轻微上移 |
| 表格整行滚动 | 500–600ms | ease-in-out，间隔 2.5–3s |
| 地图飞线 | 3–5s 循环 | linear |
| 呼吸/脉冲 | 2s 循环 | ease-in-out |
| 悬停反馈（网页端） | 150–200ms | ease |

**不要**：> 1s 的入场动画、弹簧回弹、旋转 360° 的装饰、每次数据刷新都重新播放入场。

## 2. 数字滚动（KPI）

```js
function animateNumber(el, from, to, fmt, dur = 900) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    el.textContent = fmt(to); return;
  }
  const start = performance.now();
  (function frame(now) {
    const p = Math.min(1, (now - start) / dur);
    const e = 1 - Math.pow(1 - p, 3);       // easeOutCubic
    el.textContent = fmt(from + (to - from) * e);
    if (p < 1) requestAnimationFrame(frame);
  })(performance.now());
}
```

**要点**
- 记录上一次的值，刷新时从旧值滚到新值，而不是从 0 开始。
- 格式化函数必须固定小数位，否则宽度跳动。
- 容器用 `font-variant-numeric: tabular-nums` + 固定宽度。
- 数据缺失时显示 `--`，不要显示 `NaN`。

## 3. 滚动表格（工单/告警/排行）

```js
function autoScroll(track, viewport, rowH, interval = 2800) {
  let offset = 0;
  let timer = null;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  function tick() {
    if (document.hidden || reduce) return;
    const visible = Math.floor(viewport.clientHeight / rowH);
    if (track.children.length <= visible) return;
    offset += rowH;
    track.style.transition = "transform .55s cubic-bezier(.22,.61,.36,1)";
    track.style.transform = `translateY(-${offset}px)`;
    setTimeout(() => {
      track.style.transition = "none";
      track.appendChild(track.firstElementChild);  // 首行移到末尾
      offset = 0;
      track.style.transform = "translateY(0)";
      void track.offsetHeight;                     // 强制 reflow
    }, 570);
  }
  timer = setInterval(tick, interval);
  return () => clearInterval(timer);
}
```

**变体**
- 无缝循环：把数据复制两份，用 `translateY` 连续滚动，到一半时归零（适合固定行高、无需交互）。
- 分组轮播：每页 N 行，整页淡入淡出（适合排行，一屏 5 名 → 下一页）。
- 新数据插入：在顶部插入一行并高亮 2s，再恢复（适合实时告警）。

**坑**
- 数据刷新时 `innerHTML = ...` 会重置滚动位置 → 重新绑定前先销毁定时器。
- 行高必须固定（`height:32px`），不要用 padding 撑开。
- 表格行数少于可视行数时不要滚动，否则会「空转」。

## 4. 跑马灯（播报）

```js
function marquee(track, speed = 45) {           // px/s
  const half = track.scrollWidth / 2;
  let x = 0, last = performance.now(), paused = false;
  track.parentElement.addEventListener("mouseenter", () => paused = true);
  track.parentElement.addEventListener("mouseleave", () => paused = false);
  (function step(now) {
    const dt = Math.min(64, now - last); last = now;
    if (!paused && !document.hidden) {
      x = (x + dt * speed / 1000) % half;
      track.style.transform = `translateX(${-x}px)`;
    }
    requestAnimationFrame(step);
  })(performance.now());
}
```
内容必须复制两份；`half` 在字体加载后重新计算一次。

## 5. 视图切换 / 钻取

大屏常见三种：
1. **顶部 Tab 切换数据集**（总览/交通/安全/民生）——最稳，A1/A2 常用。
2. **点击地图省份钻取**——需要二级 GeoJSON + 返回按钮 + 面包屑。
3. **定时轮播多页**——每 15–30s 自动切，任意点击暂停。

```js
// Tab：只换图表数据，不销毁页面
nav.addEventListener("click", e => {
  const view = e.target.closest("[data-view]")?.dataset.view;
  if (!view) return;
  charts.setView(view);          // 内部 setOption(notMerge:true)
  history.replaceState(null, "", `#${view}`);   // 刷新后保持
});
```

**钻取要点**
- 地图钻取后必须能返回上一级（面包屑 + Esc）。
- 二级页数据懒加载，失败时保留一级并提示，不要白屏。
- 定时轮播时，用户一旦交互就暂停自动切换（避免「刚看到就被切走」）。

## 6. 全屏 / Kiosk / 自动刷新

| 能力 | 实现 | 备注 |
|---|---|---|
| 全屏 | `document.documentElement.requestFullscreen()` | 需用户手势触发；F11 也可 |
| 隐藏鼠标 | `cursor:none`（5s 无操作后） | 展厅模式 |
| 自动刷新 | `setInterval` + 页面可见性 | 页面隐藏时暂停，回来立即刷新一次 |
| 防息屏 | Wake Lock API（可选） | 需 HTTPS；失败静默 |
| 开机自启 | 浏览器 kiosk 模式 / 桌面快捷方式 | 交付文档里写清楚 |

## 7. 缩放与重排

```js
let raf = null;
function onResize() {
  cancelAnimationFrame(raf);
  raf = requestAnimationFrame(() => {
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.setProperty("--s", s);
    setTimeout(() => charts.resizeAll(), 60);   // 等布局稳定
  });
}
addEventListener("resize", onResize);
```

- 图表容器必须有确定宽高（`height:100%` 且父级 `min-height:0`），否则 ECharts 高度为 0。
- Flex/Grid 子项要加 `min-height:0`，否则内容会撑破容器。
- 字体加载完成后调用一次 `resize()`（`document.fonts.ready.then(...)`）。

## 8. 可访问性与眩晕

- 全局支持 `prefers-reduced-motion: reduce`：关闭滚动、涟漪、入场。
- 闪烁频率 < 3Hz（癫痫安全线）。
- 不要用全屏闪白/闪红做告警；用局部色块 + 文字。
- 关键信息不能只靠动画出现（动画失败时也要可见）。

## 9. 交互清点（交付前）

- [ ] Tab 可点击、有选中态、刷新后保持
- [ ] 地图可钻取且可返回
- [ ] 表格滚动可读、悬停暂停（网页端）
- [ ] 全屏按钮可用
- [ ] 数据刷新不闪屏、不清空
- [ ] 断网/接口失败有状态提示（不白屏）
- [ ] 10 分钟无人操作不会卡死/内存暴涨
- [ ] 双屏/投屏切换分辨率后布局正确
