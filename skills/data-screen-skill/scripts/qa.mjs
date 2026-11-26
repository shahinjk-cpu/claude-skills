#!/usr/bin/env node
/**
 * 大屏静态体检：node scripts/qa.mjs [dir] [--json] [--offline]
 * 退出码 1 表示存在 error；warning 不影响退出码。
 */
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const flags = new Set(args.filter((a) => a.startsWith("--")));
const target = path.resolve(args.find((a) => !a.startsWith("--")) || ".");
const asJson = flags.has("--json");
const offline = flags.has("--offline");
const C = process.stdout.isTTY && !process.env.NO_COLOR
  ? { red: "\x1b[31m", yellow: "\x1b[33m", green: "\x1b[32m", dim: "\x1b[2m", bold: "\x1b[1m", reset: "\x1b[0m" }
  : { red: "", yellow: "", green: "", dim: "", bold: "", reset: "" };

const findings = [];
function add(level, file, message, line) {
  findings.push({ level, file: path.relative(target, file) || path.basename(file), message, line });
}

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", ".git", "vendor"].includes(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

function lineOf(text, index) {
  return text.slice(0, index).split("\n").length;
}

function getPath(obj, p) {
  const parts = String(p).replace(/\[(\d+)\]/g, ".$1").split(".").filter(Boolean);
  let cur = obj;
  for (const part of parts) {
    if (cur == null) return { ok: false };
    cur = cur[part];
  }
  return { ok: cur !== undefined && cur !== null, value: cur };
}

const files = walk(target);
const htmls = files.filter((f) => f.endsWith(".html"));
if (!htmls.length) {
  console.error("未找到 HTML 文件：" + target);
  process.exit(2);
}

const PLACEHOLDERS = [
  "模块标题样式", "lorem ipsum", "TODO:", "FIXME", "示例文本", "标题占位",
  "xxx市", "xxx区", "xxxxx", "企业名称1"
];

for (const file of htmls) {
  const html = fs.readFileSync(file, "utf8");

  // 1. 标题
  const title = (html.match(/<title[^>]*>([^<]*)<\/title>/i) || [])[1] || "";
  if (!title.trim() || /^index$/i.test(title.trim())) {
    add("warn", file, "页面 title 为空或为 index，投屏时标签页/收藏名称不可读");
  }

  // 2. lang / viewport
  if (!/<html[^>]+lang=/i.test(html)) add("warn", file, "<html> 缺少 lang 属性");
  if (!/<meta[^>]+name=["']viewport["']/i.test(html)) add("warn", file, "缺少 viewport meta（LED/平板适配可能异常）");

  // 3. 重复 id
  const ids = new Map();
  for (const m of html.matchAll(/\sid=["']([^"']+)["']/g)) {
    const id = m[1];
    if (ids.has(id)) add("error", file, `重复 id="${id}"（第 ${ids.get(id)} 行与第 ${lineOf(html, m.index)} 行）`, lineOf(html, m.index));
    else ids.set(id, lineOf(html, m.index));
  }

  // 4. 占位文案
  const lower = html.toLowerCase();
  for (const p of PLACEHOLDERS) {
    const idx = lower.indexOf(p.toLowerCase());
    if (idx >= 0) add("error", file, `发现未替换的占位文案「${p}」`, lineOf(html, idx));
  }

  // 5. 外部资源
  for (const m of html.matchAll(/<(?:script|link|img|iframe)[^>]+(?:src|href)=["'](https?:\/\/[^"']+)["']/gi)) {
    const level = offline ? "error" : "warn";
    add(level, file, `引用外网资源：${m[1].slice(0, 90)}${offline ? "（离线模式不允许）" : ""}`, lineOf(html, m.index));
  }

  // 6. 内联事件
  const inline = [...html.matchAll(/\son(click|change|mouseover)=/gi)];
  if (inline.length) add("warn", file, `存在 ${inline.length} 处内联事件属性，不利于 CSP 与维护`);

  // 7. alt
  const imgs = [...html.matchAll(/<img\b[^>]*>/gi)];
  const noAlt = imgs.filter((m) => !/\balt=/i.test(m[0]));
  if (noAlt.length) add("warn", file, `${noAlt.length} 张图片缺少 alt`);

  // 8. 本地资源是否存在
  for (const m of html.matchAll(/<(?:script|link|img)[^>]+(?:src|href)=["'](?!https?:|data:|\/\/|#)([^"']+)["']/gi)) {
    const ref = m[1].split("?")[0];
    const abs = path.resolve(path.dirname(file), ref);
    if (!fs.existsSync(abs)) add("error", file, `本地资源不存在：${ref}`, lineOf(html, m.index));
  }

  // 9. data-bind 路径必须在 mock 数据里存在（若存在 data/mock.json）
  const mockPath = path.join(path.dirname(file), "data", "mock.json");
  if (fs.existsSync(mockPath)) {
    let data;
    try { data = JSON.parse(fs.readFileSync(mockPath, "utf8")); }
    catch (e) { add("error", mockPath, "mock.json 不是合法 JSON：" + e.message); }
    if (data) {
      const binds = [...html.matchAll(/data-bind=["']([^"']+)["']/g)];
      for (const m of binds) {
        if (!getPath(data, m[1]).ok) add("error", file, `data-bind 路径在 mock 数据中不存在：${m[1]}`, lineOf(html, m.index));
      }
      const chartEls = [...html.matchAll(/data-chart=["']([^"']+)["']/g)].map((m) => m[1]);
      const chartsJs = path.join(path.dirname(file), "js", "charts.js");
      if (fs.existsSync(chartsJs)) {
        const js = fs.readFileSync(chartsJs, "utf8");
        const registered = new Set([...js.matchAll(/^\s{2,6}([a-zA-Z0-9_]+):\s*build[A-Z]/gm)].map((m) => m[1]));
        for (const c of chartEls) {
          if (!registered.has(c)) add("warn", file, `图表 "${c}" 未在 charts.js 的 REGISTRY 中注册`);
        }
      }
    }
  }
}

// 10. JS 体检
const jsFiles = files.filter((f) => /(^|[\\/])(js|scripts)[\\/].*\.js$/.test(f) && !f.endsWith(".min.js"));
for (const file of jsFiles) {
  const js = fs.readFileSync(file, "utf8");
  if (/console\.log\(/.test(js)) add("warn", file, "包含 console.log（上线前清理或用 debug 开关）");
  if (/fetch\(\s*["'][^"']+["']/.test(js) && !file.endsWith("adapter.js") && !/fetch\(\s*["']\.\/data\//.test(js)) {
    add("warn", file, "直接 fetch 硬编码地址，应统一走 adapter.js");
  }
  if (/\bsetInterval\(/.test(js) && !/document\.hidden|clearInterval/.test(js)) {
    add("warn", file, "setInterval 未处理页面隐藏/清理，长时间投屏可能累积");
  }
}

// 11. 样式体检
const cssFiles = files.filter((f) => f.endsWith(".css"));
let hasReducedMotion = false;
for (const file of cssFiles) {
  const css = fs.readFileSync(file, "utf8");
  if (/prefers-reduced-motion/.test(css)) hasReducedMotion = true;
  if (/@import\s+url\(["']?https?:/i.test(css)) add("warn", file, "CSS @import 外网字体/样式，内网会失效");
}
if (!hasReducedMotion) add("warn", htmls[0], "未发现 prefers-reduced-motion 降级（眩晕敏感/低配投屏）");

// 12. 动效/缩放
const allText = files.filter(f => /\.(html|js|css)$/.test(f) && !f.endsWith(".min.js")).map((f) => fs.readFileSync(f, "utf8")).join("\n");
if (!/transform\s*:\s*scale|scale\(/.test(allText) && !/font-size\s*:\s*[^;]*vw/.test(allText)) {
  add("warn", htmls[0], "未发现等比缩放方案，非 1920 屏幕可能错位");
}
if (!/addEventListener\(\s*["']resize|ResizeObserver/.test(allText)) {
  add("warn", htmls[0], "未监听 resize，窗口/投屏分辨率变化后图表不会重排");
}

// 13. 数据接口
if (!files.some((f) => /adapter\.js$/.test(f))) {
  add("warn", htmls[0], "未发现 adapter.js，外部数据接入需要新增适配层");
}

const errors = findings.filter((f) => f.level === "error");
const warns = findings.filter((f) => f.level === "warn");

if (asJson) {
  console.log(JSON.stringify({ target, errors: errors.length, warnings: warns.length, findings }, null, 2));
} else {
  console.log(`\n${C.bold}Data Screen QA${C.reset} ${C.dim}${target}${C.reset}`);
  console.log(`${C.dim}${htmls.length} html · ${jsFiles.length} js · ${cssFiles.length} css${C.reset}\n`);
  for (const f of findings) {
    const tag = f.level === "error" ? `${C.red}ERROR${C.reset}` : `${C.yellow}WARN ${C.reset}`;
    const loc = f.line ? `:${f.line}` : "";
    console.log(`${tag} ${f.file}${loc}\n      ${f.message}`);
  }
  const summary = `${errors.length} error · ${warns.length} warning`;
  console.log(`\n${errors.length ? C.red : C.green}${summary}${C.reset}\n`);
  if (!findings.length) console.log(`${C.green}全部通过，可以交付。${C.reset}\n`);
}
process.exit(errors.length ? 1 : 0);
