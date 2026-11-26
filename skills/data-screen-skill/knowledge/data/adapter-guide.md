# 数据适配层实现指南

> 适配层文件：`starter/js/adapter.js`（零依赖，约 300 行）。
> 复制到新项目后**只需改 `index.html` 里的 `DASHBOARD_CONFIG`**，不要改 adapter 内部。

## 1. 配置项

```js
window.DASHBOARD_CONFIG = {
  mode: "rest",                       // mock | rest | sse | ws | inline | postMessage
  endpoint: "/api/screen/city-ops",   // 接口地址
  pollInterval: 30000,                // 轮询间隔 ms；0 = 只加载一次
  timeout: 8000,                      // 单次请求超时
  retry: 3,                           // 失败重试次数（指数退避）
  retryBaseDelay: 1500,
  headers: { "X-Client": "screen" },  // 不要放长期 token
  withCredentials: false,             // Cookie 鉴权时设 true
  transform: "crm",                   // 可选：window.DashboardTransforms.crm
  staleAfter: 120000,                 // 超过多久标记 stale
  debug: false
};
```

## 2. 六种模式

### 2.1 mock（开发/演示）

```js
{ mode: "mock", endpoint: "./data/mock.json" }
```
- 必须通过 HTTP 访问（`node scripts/serve.mjs`），`file://` 下 `fetch` 会被 CORS 拦截。
- `mock.json` 就是契约快照，改数据不改代码。

### 2.2 rest（生产默认）

```js
{ mode: "rest", endpoint: "https://api.example.com/screen/ops", pollInterval: 15000 }
```
- GET，`Accept: application/json`。
- 失败：重试 3 次 → 保留上一帧 → 状态变 `stale` → 下个周期继续。
- 如果后端只支持 POST：在 `adapter.js` 的 `fetchJson` 里改 `method:"POST"` 和 `body`，或加一个 BFF 转发。

### 2.3 sse（服务端推送）

```js
{ mode: "sse", endpoint: "/api/screen/ops/stream" }
```
服务端格式：

```
Content-Type: text/event-stream
Cache-Control: no-cache

data: {"meta":{"updatedAt":"2026-11-26T09:42:18+08:00","source":"sse"},"kpis":{...}}

```
- 每条 `data:` 都是一个完整快照（不是增量），避免前端合并逻辑。
- 断线由浏览器自动重连；`onerror` 里只更新状态，不要手动重建。
- Nginx 需要 `proxy_buffering off; proxy_read_timeout 3600s;`。

### 2.4 ws（双向）

```js
{ mode: "ws", endpoint: "wss://api.example.com/ws/screen" }
```
- 连上后建议发订阅消息（当前 adapter 未内置，可在 `connectWs` 的 `onopen` 里加）。
- 断线自动重连（指数退避，最多 15s）。
- 心跳：服务端每 30s 发 ping，或前端每 25s 发 `{"type":"ping"}`。

### 2.5 inline（单文件交付）

```html
<script>window.DASHBOARD_DATA = { "meta": {...}, "kpis": {...} };</script>
<script>window.DASHBOARD_CONFIG = { mode: "inline" };</script>
```
适合：离线 U 盘交付、演示机无网络、服务端模板直接注入。

### 2.6 postMessage（嵌入门户）

父页面：

```js
const frame = document.getElementById("screen");
frame.addEventListener("load", () => {
  frame.contentWindow.postMessage({ type: "dashboard:data", payload: snapshot }, "https://screen.example.com");
});
// 子页面就绪后会发 { type: "dashboard:ready" }
window.addEventListener("message", e => {
  if (e.origin !== "https://screen.example.com") return;
  if (e.data?.type === "dashboard:ready") sendSnapshot();
});
```
**必须校验 origin**，否则任意站点可注入数据。

## 3. 图表如何取数

```js
// 单值
DashboardData.get("kpis.events.value");           // 1286
// 数组/对象
DashboardData.get("series.trend.categories");    // ["11/20", ...]
// 默认值
DashboardData.get("kpis.extra.rate", 0);
// 订阅
DashboardData.on("data", ({ snapshot }) => render(snapshot));
DashboardData.on("status", s => setStatusLight(s.status));
```

DOM 绑定（starter 的写法，零 JS 即可展示 KPI）：

```html
<span data-bind="kpis.events.value" data-format="int">0</span>
```
支持格式：`int` `dec1` `pct` `pct1` `min` `wan` `money` `time`。

## 4. 新增一种数据源

以「GraphQL」为例，只改 adapter：

```js
// 1) 加 mode
if (config.mode === "graphql") {
  fetchJson(config.endpoint).then(commit).catch(fail);
  return;
}
// 2) fetchJson 里把 GET 改成 POST + query
// 3) 在 transform 里把 data.screen 映射成快照
```
不要在 `charts.js` / `screen.js` 里加分支。

## 5. 鉴权

| 方式 | 做法 | 注意 |
|---|---|---|
| 同域 Cookie | `withCredentials:true` | 需要 CORS `Access-Control-Allow-Credentials` |
| Bearer | 由 BFF 注入，前端不存 | 长期 token 禁止写死 |
| 短期签名 | 后端返回带 `expires` 的 URL | 过期前刷新 |
| 内网白名单 | Nginx `allow/deny` | 最简单，适合专网 |

## 6. 联调自测

```bash
# 1) 接口返回是否符合契约
curl -s http://localhost:8080/api/screen/ops | node -e "
let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{
  const j=JSON.parse(s);
  console.log('meta.updatedAt:', j.meta?.updatedAt);
  console.log('kpis:', Object.keys(j.kpis||{}).join(','));
  console.log('series:', Object.keys(j.series||{}).join(','));
})"

# 2) 校验 JSON Schema（需 ajv）
npx ajv-cli validate -s knowledge/data/schema.json -d snapshot.json

# 3) 页面静态体检
node scripts/qa.mjs screens/ops
```

## 7. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 页面一直「连接中」 | `file://` 打开 / CORS | 用 `serve.mjs`；后端加 CORS |
| 状态灯红、无数据 | 接口 401/500 | 看 Network；检查 token/路径 |
| 有数据但图表空 | 路径不匹配 | `DashboardData.get("series.trend")` 打印 |
| 刷新后闪一下 | `innerHTML` 重建 | 改为 `setOption` 合并更新 |
| 地图偏移 | 坐标系不一致 | 统一 GCJ-02 或 WGS-84 |
| 数据延迟灯常亮 | `updatedAt` 没带时区/没更新 | 后端每次返回当前时间 |
| 内存持续上涨 | 定时器/实例未清理 | `destroy()` + `clearInterval` |

## 8. 生产建议

- 接口做**聚合**：一次返回整屏快照，避免 15 个并发请求。
- 服务端缓存 5–15s，防止大屏轮询打爆数据库。
- 返回体控制在 200KB 内；大列表做分页/截断。
- 加 `ETag` / `Last-Modified`，未变化返回 304。
- 监控：大屏在线数、接口 P95、数据延迟、JS 错误。
