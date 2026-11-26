#!/usr/bin/env node
/**
 * 合并「人工提炼元数据」与「上游代码扫描结果」，生成 knowledge/catalog.json。
 * vendor 不存在时只输出 meta（技能仍可用，只是缺少扫描字段）。
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const meta = JSON.parse(fs.readFileSync(path.join(repo, "knowledge", "catalog.meta.json"), "utf8"));
const vendor = path.join(repo, "vendor", "dashuju-templates");

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

function extract(screen) {
  const main = path.join(vendor, screen.path);
  if (!fs.existsSync(main)) return null;
  const dir = path.dirname(main);
  const files = walk(dir);
  const html = fs.readFileSync(main, "utf8");
  const css = files.filter((f) => f.endsWith(".css")).map((f) => fs.readFileSync(f, "utf8")).join("\n");
  const appJs = files
    .filter((f) => f.endsWith(".js") && !/echarts|jquery|\.min\.|china\.js|area_|guangdong|rem\.js/i.test(path.basename(f)))
    .map((f) => fs.readFileSync(f, "utf8"))
    .join("\n");
  const series = [...new Set([...appJs.matchAll(/type\s*:\s*["'](bar|line|pie|map|scatter|effectScatter|radar|gauge|funnel|graph|heatmap|treemap|pictorialBar|sankey|lines|bar3D|scatter3D|map3D|surface)["']/g)].map((m) => m[1]))];
  const colors = Object.entries(
    [...css.matchAll(/#([0-9a-f]{6})\b/gi)].reduce((acc, m) => {
      const k = m[1].toLowerCase();
      acc[k] = (acc[k] || 0) + 1;
      return acc;
    }, {})
  ).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k]) => "#" + k);
  const sizes = files.reduce((a, f) => a + fs.statSync(f).size, 0);
  const echartsFile = files.find((f) => /echarts[^\\/]*\.js$/.test(path.basename(f)) && !/gl/i.test(path.basename(f)));
  let echartsVersion = null;
  if (echartsFile) {
    const full = fs.readFileSync(echartsFile, "utf8");
    const m = full.match(/version["']?\s*[:=]\s*["'](\d+\.\d+\.\d+)/i)
      || full.match(/echarts(?:\.min)?\.js[^\n]{0,80}v?(\d+\.\d+\.\d+)/i)
      || full.match(/["'](\d+\.\d+\.\d+)["']\s*,\s*["']?version/i);
    if (m) echartsVersion = m[1];
  }
  return {
    scanned: {
      mainHtml: screen.path,
      htmlCount: files.filter((f) => f.endsWith(".html")).length,
      sizeMB: +(sizes / 1048576).toFixed(1),
      echartsVersion,
      seriesTypes: series,
      cssTopColors: colors,
      hasInlineData: /data\s*:\s*\[/.test(html + appJs)
    }
  };
}

let scannedCount = 0;
const screens = meta.screens.map((s) => {
  const scanned = fs.existsSync(vendor) ? extract(s) : null;
  if (scanned) {
    scannedCount++;
    if (!scanned.scanned.echartsVersion) {
      const m = (s.stack || []).join(" ").match(/ECharts\s*(\d+\.\d+(?:\.\d+)?)/i);
      if (m) scanned.scanned.echartsVersion = m[1];
    }
  }
  return { ...s, ...(scanned || { scanned: null }) };
});

const out = {
  ...meta,
  generatedAt: new Date().toISOString(),
  vendorAvailable: fs.existsSync(vendor),
  screens
};

const target = path.join(repo, "knowledge", "catalog.json");
fs.writeFileSync(target, JSON.stringify(out, null, 2) + "\n", "utf8");
console.log(`✔ knowledge/catalog.json 已生成：${screens.length} 套模板，${scannedCount} 套含源码扫描结果`);
console.log(fs.existsSync(vendor) ? "" : "  提示：运行 node scripts/fetch-templates.mjs 可补齐源码扫描字段。");
