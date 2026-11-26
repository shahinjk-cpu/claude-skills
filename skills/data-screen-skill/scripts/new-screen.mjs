#!/usr/bin/env node
/**
 * 从 starter 生成一个新大屏工程。
 * 用法：node scripts/new-screen.mjs --out screens/city-ops --title "XX市城市运行指挥中心" --theme cyan
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(__dirname, "..");

function arg(name, fallback) {
  const i = process.argv.indexOf("--" + name);
  return i >= 0 && process.argv[i + 1] && !process.argv[i + 1].startsWith("--") ? process.argv[i + 1] : fallback;
}
const has = (name) => process.argv.includes("--" + name);

const out = path.resolve(arg("out", "screens/new-screen"));
const title = arg("title", "城市运行数据大屏");
const subtitle = arg("subtitle", "CITY OPERATIONS DASHBOARD");
const theme = arg("theme", "cyan");
const mode = arg("mode", "mock");
const endpoint = arg("endpoint", "./data/mock.json");

if (!has("force") && fs.existsSync(out) && fs.readdirSync(out).length) {
  console.error(`目标目录已存在且非空：${out}\n加 --force 覆盖，或换 --out。`);
  process.exit(1);
}

function copy(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name);
    const d = path.join(dst, e.name);
    if (e.isDirectory()) copy(s, d);
    else fs.copyFileSync(s, d);
  }
}

fs.rmSync(out, { recursive: true, force: true });
copy(path.join(repo, "starter"), out);

const htmlPath = path.join(out, "index.html");
let html = fs.readFileSync(htmlPath, "utf8");
html = html
  .replace(/<title[^>]*>[^<]*<\/title>/, `<title id="document-title">${title}</title>`)
  .replace(/<h1 id="screen-title">[^<]*<\/h1>/, `<h1 id="screen-title">${title}</h1>`)
  .replace(/<p id="screen-subtitle">[^<]*<\/p>/, `<p id="screen-subtitle">${subtitle}</p>`)
  .replace(/data-theme="[^"]*"/, `data-theme="${theme}"`)
  .replace('mode: "mock"', `mode: "${mode}"`)
  .replace('endpoint: "./data/mock.json"', `endpoint: "${endpoint}"`)
  .replace('data-mode="mock"', `data-mode="${mode}"`);
fs.writeFileSync(htmlPath, html, "utf8");

const mockPath = path.join(out, "data", "mock.json");
if (fs.existsSync(mockPath)) {
  const mock = JSON.parse(fs.readFileSync(mockPath, "utf8"));
  mock.meta.screen = title;
  mock.meta.source = mode;
  fs.writeFileSync(mockPath, JSON.stringify(mock, null, 2) + "\n", "utf8");
}

console.log(`
  ✔ 已生成 ${path.relative(process.cwd(), out)}

  下一步：
    1. node scripts/serve.mjs ${path.relative(repo, out)}
    2. 修改 index.html 中的 DASHBOARD_CONFIG 接入真实接口
    3. 修改 data/mock.json 调整演示数据（结构与真实接口保持一致）
    4. node scripts/qa.mjs ${path.relative(repo, out)}
`);
