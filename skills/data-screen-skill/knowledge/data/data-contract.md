# 统一数据契约（External Data Contract）

> 这是本 skill 的**接口层标准**。任何后端（Java/Python/Node/Go）、任何数据源（REST/WS/SSE/文件/父窗口）
> 只要输出符合本契约的 snapshot，前端图表代码**一行都不用改**。

## 1. 五条原则

1. **视图只读快照**：页面永远只消费一个 `snapshot` 对象，不关心它从哪来。
2. **数值即数字**：`value` 必须是 number，单位放在 `unit`/`meta`，不要返回 `"12.3万"`。
3. **路径稳定**：字段名是契约的一部分，改字段 = 破坏性变更，需要升版本。
4. **失败不白屏**：保留上一帧数据，标记 `stale`，展示状态灯。
5. **演示可识别**：mock 数据必须带 `meta.source = "mock"`，页面显示「示例数据」。

## 2. 顶层结构

```jsonc
{
  "meta": {
    "schemaVersion": "1.0",
    "screen": "城市运行指挥中心",
    "updatedAt": "2026-11-26T09:42:18+08:00",
    "source": "rest",              // mock | rest | sse | ws | inline | postMessage
    "note": "可选：口径说明"
  },
  "kpis":    { "<id>": { "label": "", "value": 0, "unit": "", "delta": 0, "trend": "up|down|flat", "precision": 0 } },
  "series":  { "<key>": { "unit": "", "categories": [], "series": [], "items": [] } },
  "lists":   { "<key>": { "columns": [], "rows": [] } },
  "geo":     { "hub": {}, "points": [], "lines": [] },
  "alerts":  [],
  "ticker":  [],
  "views":   { "<viewId>": { "trend": {}, "types": {}, "rank": {} } }
}
```

只有 `meta` 是强制的；其余按页面需要提供。缺失的模块显示「暂无数据」。

## 3. 各字段规范

### 3.1 meta

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schemaVersion` | string | 建议 | `1.0`；前端可据此做兼容 |
| `screen` | string | 建议 | 页面名称 |
| `updatedAt` | string | **是** | ISO 8601，**必须带时区**（`+08:00` 或 `Z`） |
| `source` | string | 是 | 数据来源类型 |
| `note` | string | 否 | 口径、免责声明 |

> `updatedAt` 用于「数据延迟」判断：前端超过 `staleAfter`（默认 120s）未更新会变黄灯。

### 3.2 kpis

```json
"kpis": {
  "events":   { "label": "今日事件总量", "value": 1286, "unit": "件", "delta": 6.4, "trend": "up", "precision": 0 },
  "resolved": { "label": "已办结", "value": 1043, "unit": "件", "delta": 4.1, "rate": 81.1 }
}
```

- **id 稳定**：`events` 不要改成 `eventCount`，否则绑定全断。
- `value` 数字；`delta` 为百分比数值（`6.4` 表示 +6.4%），前端加 `+` 号。
- 额外字段（`rate`、`critical`）可自由扩展，前端按 `data-bind="kpis.resolved.rate"` 取。

### 3.3 series

**时序型**（折线/柱/复合）：

```json
"trend": {
  "unit": "件",
  "categories": ["11/20", "11/21", "11/22"],
  "series": [
    { "name": "受理", "type": "bar",  "data": [158, 176, 164] },
    { "name": "办结", "type": "line", "data": [141, 160, 152] }
  ]
}
```

**分类型**（饼/环/雷达）：

```json
"types": { "items": [ { "name": "市容环境", "value": 386 } ] },
"radar": {
  "indicators": [ { "name": "响应速度", "max": 100 } ],
  "series": [ { "name": "本月", "value": [92, 88, 96, 84, 90] } ]
}
```

**单值型**（仪表盘/进度）：

```json
"gauge": { "value": 81.1, "label": "按时办结率", "unit": "%" },
"resource": { "items": [ { "name": "网格员", "done": 286, "idle": 56 } ] }
```

### 3.4 lists

```json
"lists": {
  "tickets": {
    "columns": ["time", "title", "area", "status"],
    "rows": [
      { "time": "09:41", "title": "文三路与教工路口积水", "area": "西湖区", "status": "处置中" }
    ]
  }
}
```

- 行对象优于数组（字段自解释、易扩展）。
- 前端最多渲染 20 行，滚动展示；接口可返回更多。
- 长文本前端做省略号 + `title` 提示。

### 3.5 geo

```json
"geo": {
  "hub": { "name": "杭州", "coord": [120.155, 30.274] },
  "points": [
    { "name": "杭州", "value": [120.155, 30.274, 286], "level": "critical" }
  ],
  "lines": [
    { "fromName": "杭州", "toName": "上海", "coords": [[120.155, 30.274], [121.473, 31.23]] }
  ]
}
```

- `value` 的顺序固定为 `[经度, 纬度, 数值]`。
- `level`：`normal | major | critical`，前端映射颜色与涟漪大小。
- 坐标系：GeoJSON 与点位必须一致（GCJ-02 对中国地图，WGS-84 对 GPS 原始数据）。

### 3.6 alerts / ticker

```json
"alerts": [
  { "level": "critical", "title": "钱塘江水位超警戒", "area": "上城区", "type": "防汛", "time": "09:40" }
],
"ticker": ["<b>09:42</b> 全市平均到场时间 <b>6.4 分钟</b>。"]
```

`ticker` 允许有限 HTML（`<b>`），后端必须转义用户输入。

### 3.7 views（可选，多视图）

```json
"views": {
  "traffic": {
    "trend": { "categories": [], "series": [] },
    "types": { "items": [] },
    "rank":  { "items": [] }
  }
}
```

前端切换 Tab 时优先使用 `views.<id>`，缺失则回退到顶层同名数据。

## 4. 数据模式（mode）

| mode | 传输 | 适用 | 配置 |
|---|---|---|---|
| `mock` | 本地 JSON | 开发/演示 | `endpoint:"./data/mock.json"` |
| `rest` | HTTP GET + 轮询 | 大多数生产接口 | `endpoint`、`pollInterval`、`headers` |
| `sse` | EventSource 单向推送 | 实时性要求高、只读 | `endpoint` |
| `ws` | WebSocket 双向 | 需要订阅/指令 | `endpoint` |
| `inline` | 页面内 `window.DASHBOARD_DATA` | 服务端渲染/单文件交付 | 无 |
| `postMessage` | 父窗口推送 | 嵌入门户/iframe | 监听 `message` |

## 5. 刷新与状态机

```
idle → loading → live ──(失败)──→ stale ──(成功)──→ live
                     └──(首次失败)──→ error
```

- **轮询**：默认 30s；页面隐藏时暂停，恢复可见立即刷新。
- **超时**：默认 8s，`AbortController` 取消。
- **重试**：默认 3 次，指数退避 1.5s → 3s → 6s。
- **缓存**：成功后写 `localStorage`（按 pathname），离线重启可恢复上一帧。
- **不闪屏**：刷新时不清空 DOM；`setOption` 用合并模式。

## 6. 后端接入示例

**REST（推荐）**

```http
GET /api/screen/city-ops
Authorization: Bearer <短期令牌>
→ 200 application/json  （即上面的 snapshot）
```

**SSE**

```
GET /api/screen/city-ops/stream
Content-Type: text/event-stream
data: {"meta":{...},"kpis":{...}}

```

**WebSocket**

```json
// client → server（订阅）
{ "type": "subscribe", "screen": "city-ops", "interval": 5000 }
// server → client（快照）
{ "type": "snapshot", "payload": { "meta": {}, "kpis": {} } }
```

**父窗口（iframe 嵌入）**

```js
iframe.contentWindow.postMessage({ type: "dashboard:data", payload: snapshot }, "https://screen.example");
```

## 7. 把任意后端映射到契约

后端字段通常不是契约结构。**在 adapter 的 transform 里做一次映射**，不要把映射散落在图表代码里。

```js
window.DashboardTransforms = {
  crm(raw) {
    return {
      meta: { schemaVersion: "1.0", updatedAt: raw.ts, source: "rest", screen: "客户运营" },
      kpis: {
        customers: { label: "客户总数", value: raw.data.total, unit: "人" },
        newToday:  { label: "今日新增", value: raw.data.today, unit: "人" }
      },
      series: {
        trend: {
          unit: "人",
          categories: raw.data.days,
          series: [{ name: "新增", type: "bar", data: raw.data.counts }]
        }
      }
    };
  }
};
// config: { transform: "crm" }
```

映射层要处理：
- 字符串数字 → number（`Number(x)`，`NaN` 归 0）
- 时间戳（秒/毫秒）→ ISO 字符串
- 枚举 → 中文标签 / 语义 level
- 缺失字段 → 空数组 / `null`（不要 `undefined`）
- 单位换算（元 → 万元）在一处完成并写进 `unit`

## 8. 安全

- **不要把长期 token 写进前端**。用同域 BFF / Cookie / 短期签名 URL。
- CORS 只允许大屏域名；`postMessage` 必须校验 `evt.origin`（starter 里有注释）。
- 内网部署时所有第三方资源本地化：ECharts、字体、GeoJSON、图标。
- 日志不要打印完整 payload（可能含个人信息）。
- 演示数据必须脱敏/虚构；真实项目遵循《个人信息保护法》与行业数据分级。

## 9. 版本兼容

- 新增字段 = 兼容；删除/改名字段 = 破坏性变更 → `schemaVersion` 升到 `1.1`/`2.0`。
- 前端应容忍未知字段（忽略）和缺失可选字段（降级）。
- `catalog.json` 的 `version` 与本契约独立；升级时在 `CHANGELOG.md` 记录。

## 10. 最小可用 payload

```json
{
  "meta": { "updatedAt": "2026-11-26T09:42:18+08:00", "source": "rest" },
  "kpis": { "total": { "label": "总量", "value": 1286, "unit": "件" } },
  "series": { "trend": { "categories": ["一","二","三"], "series": [{ "name": "数量", "type": "bar", "data": [1,2,3] }] } }
}
```

只要这个结构，`starter` 就能跑起来；其余模块自动降级。
