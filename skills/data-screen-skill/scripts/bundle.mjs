#!/usr/bin/env node
/**
 * 把 skill 打包成单文件 prompt，供只能聊天、不能读文件的 Agent 使用。
 * 用法：node scripts/bundle.mjs --preset chat|full|min [--out dist/x.md]
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const arg = (n, d) => {
  const i = process.argv.indexOf("--" + n);
  return i > 0 ? process.argv[i + 1] : d;
};

const presets = {
  min: ["SKILL.md", "knowledge/index.md", "knowledge/data/data-contract.md"],
  chat: [
    "SKILL.md",
    "knowledge/index.md",
    "knowledge/workflow/brief-extraction.md",
    "knowledge/workflow/template-surgery.md",
    "knowledge/patterns/layout-archetypes.md",
    "knowledge/patterns/visual-language.md",
    "knowledge/patterns/chart-recipes.md",
    "knowledge/patterns/motion-interaction.md",
    "knowledge/patterns/quality-bar.md",
    "knowledge/data/data-contract.md",
    "knowledge/data/adapter-guide.md",
    "knowledge/workflow/delivery.md",
    "knowledge/templates/01-general-blue.md",
    "knowledge/templates/02-logistics.md",
    "knowledge/templates/03-traffic.md",
    "knowledge/templates/04-gov.md",
    "knowledge/templates/05-medical.md",
    "knowledge/templates/06-weather-terminal.md",
    "knowledge/templates/07-finance.md",
    "knowledge/templates/08-ecommerce.md",
    "knowledge/templates/09-iot-vehicle.md",
    "knowledge/templates/10-ops-device.md",
    "knowledge/templates/11-store.md",
    "knowledge/templates/12-construction-land.md"
  ]
};

const preset = arg("preset", "chat");
let files = presets[preset];
if (!files) {
  console.error("未知 preset：" + preset + "（可选 min / chat / full）");
  process.exit(1);
}
if (preset === "full") {
  files = ["SKILL.md"];
  const walk = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (p.endsWith(".md")) files.push(path.relative(repo, p));
    }
  };
  walk(path.join(repo, "knowledge"));
}

const out = path.resolve(repo, arg("out", `dist/screen-skill.${preset}.md`));
fs.mkdirSync(path.dirname(out), { recursive: true });

let text = `<!-- 由 scripts/bundle.mjs 生成 · preset=${preset} · 请勿手改 -->\n\n`;
for (const f of files) {
  const p = path.join(repo, f);
  if (!fs.existsSync(p)) continue;
  text += `\n\n<!-- ===== ${f} ===== -->\n\n`;
  text += fs.readFileSync(p, "utf8");
}

fs.writeFileSync(out, text, "utf8");
const kb = (Buffer.byteLength(text) / 1024).toFixed(0);
console.log(`✔ ${path.relative(repo, out)} · ${files.length} 个文件 · ${kb}KB`);
console.log("  用法：把整个文件贴进对话，或在系统提示中引用。");
