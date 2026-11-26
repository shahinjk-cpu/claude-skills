# 交付与上线

## 1. 交付物清单

```
screens/<name>/
├─ index.html              入口
├─ css/screen.css          设计系统 + 布局
├─ js/adapter.js           数据适配层（不要改内部）
├─ js/charts.js            图表工厂
├─ js/screen.js            装配（时钟/KPI/滚动/交互）
├─ data/mock.json          示例数据（结构与真实接口一致）
├─ data/china.json         地图 GeoJSON（如用到）
├─ vendor/                 ECharts / 字体（离线）
├─ README.md               启动方式 + 接口说明
└─ screenshot-1920x1080.png
```

**必须有**：`README.md`（启动/接口/浏览器要求）、1920×1080 截图、`qa` 通过记录。

## 2. 本地预览

```bash
node scripts/serve.mjs screens/<name>
# → http://localhost:5173/
```

不要双击 `index.html`：`file://` 下 `fetch("./data/mock.json")` 会被 CORS 拦截。

## 3. 静态部署（Nginx）

```nginx
server {
  listen 80;
  server_name screen.example.com;
  root /opt/screen;
  index index.html;

  # 大屏不需要缓存 HTML，静态资源可长缓存
  location / {
    try_files $uri $uri/ /index.html;
    add_header Cache-Control "no-cache";
  }
  location ~* \.(js|css|png|jpg|svg|woff2)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
  }
  # 接口反向代理（避免 CORS）
  location /api/ {
    proxy_pass http://backend:8080/;
    proxy_set_header Host $host;
    proxy_read_timeout 120s;
  }
}
```

**注意**：如果用了 `transform:scale`，Nginx 不影响；如果用了 SSE，需要 `proxy_buffering off;`。

## 4. 内网 / 离线

- 所有第三方资源本地化：ECharts、字体、GeoJSON、图标。
- 不能有 `https://` 的 `<script>/<link>/<img>`（`qa --offline` 会报错）。
- 地图：用本地 GeoJSON；不要依赖百度/高德在线底图。
- 字体：`vendor/fonts/*.woff2` + `@font-face`。
- 时间：如果内网无 NTP，前端用服务器时间（接口返回 `serverTime`），不要用本机时间做业务判断。

## 5. Kiosk / 开机自启

Chrome：

```bat
chrome.exe --kiosk --disable-pinfchqueries --noerrdialogs ^
  --disable-session-crashed-bubble --incognito ^
  "http://localhost:8080/"
```

- 关闭自动更新/休眠/屏保。
- 每天定时重启浏览器（凌晨），避免内存累积。
- 用 `--incognito` 避免缓存旧版本。

## 6. 上线前 10 项

- [ ] 1920×1080 全屏无滚动条
- [ ] 控制台无报错
- [ ] 接口断开时状态灯变红、保留上一帧
- [ ] 刷新 10 次不白屏
- [ ] 连续运行 30 分钟内存稳定
- [ ] 缩放窗口/切换分辨率布局正确
- [ ] 所有占位文案替换
- [ ] 数据单位/口径标注
- [ ] 截图存档
- [ ] README 写完

## 7. 交接说明（可直接发给客户）

> 本大屏为纯静态页面，无需 Node 运行环境。
> 将 `screens/<name>` 整个目录部署到任意静态服务器即可。
> 数据接口在 `index.html` 的 `window.DASHBOARD_CONFIG` 中配置：
> `mode`（rest/sse/ws）、`endpoint`、`pollInterval`。
> 接口返回格式见 `knowledge/data/data-contract.md`，最小只需 `meta.updatedAt` + `kpis`。
> 修改配色：`css/screen.css` 顶部的 6 个变量。
> 修改示例数据：`data/mock.json`。

## 8. 变更管理

- 每次修改大屏 → 截图 + `qa` + 提交，提交信息写清「改了什么/为什么」。
- 破坏性接口变更 → 升 `schemaVersion`，并在 `CHANGELOG.md` 记录。
- 交付版本打 tag（如 `screen-city-ops-v1.0.0`），不要只留一个 `final.zip`。
- 客户现场改的配置（接口地址/标题）单独放 `config.js`，避免和源码混在一起。
