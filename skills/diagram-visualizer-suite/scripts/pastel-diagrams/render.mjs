#!/usr/bin/env node
// pastel-diagrams: render Mermaid (.mmd) files in a soft pastel whiteboard style
// to a self-contained HTML page, a crisp SVG, a 3x PNG and an SVG that follows light/dark mode.
//
//   pastel-diagrams <file.mmd | file.md | folder> [more ...] [options]
//
//   --out <folder>        write output here (default: next to each input)
//   --theme <name|path>   pastel (default), mono, corporate, high-contrast, or a theme .json file
//   --dark                use the dark variant of the theme
//   --scale <n>           PNG resolution (default 3)
//   --edges <style>       orthogonal (default: straight lines between side centres) or curved
//   --check               exit with code 2 when the layout check finds problems
//   --json                print the layout reports as JSON instead of text
//   --formats <list>      any of svg,png,html,auto (default: all four)
//   --md                  folders: render ```mermaid blocks in .md files (a .md file given by name always is)
//   --md-image <format>   image the Markdown links to: png (default), svg or auto
//   --list-themes         print the built-in theme names
//
// In a label, write  i:icon-name  (any Lucide icon, https://lucide.dev/icons) to insert an icon.
// Card classes: lav, mint, sky, peach, yellow, grey, decision, ext.
// Optional first line  %% title: My title  sets the title (HTML page, SVG <title>).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { resolveTheme, loadTheme, partnerTheme, listThemes } from "./lib/theme.mjs";
import { measureLayout, problems, warnings, summary } from "./lib/check.mjs";
import { mermaidBlocks, replaceBlocks } from "./lib/markdown.mjs";
import { collectGeometry, routeEdges, applyRoutes } from "./lib/route.mjs";
import { parseNotes, applyNotes } from "./lib/notes.mjs";
import { pkgDir, fontCss, icon, diagramKind, classDefs, mermaidConfig, themeCss } from "./lib/style.mjs";

let puppeteer;
try { ({ default: puppeteer } = await import("puppeteer-core")); pkgDir("mermaid"); }
catch { console.error(`Dependencies missing. Run once:  cd "${path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")}" && npm install`); process.exit(1); }

// ---------- arguments
const HELP = fs.readFileSync(fileURLToPath(import.meta.url), "utf8").split("\n").slice(1, 23).map((l) => l.replace(/^\/\/ ?/, "")).join("\n");
const args = process.argv.slice(2);
const opt = { edges: "orthogonal", out: null, scale: 3, theme: "pastel", dark: false, check: false, json: false, formats: null, md: false, mdImage: "png" };
const FORMATS = ["svg", "png", "html", "auto"];
const inputs = [];
for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--out") opt.out = path.resolve(args[++i]);
  else if (a === "--scale") opt.scale = Number(args[++i]) || 3;
  else if (a === "--theme") opt.theme = args[++i];
  else if (a === "--dark") opt.dark = true;
  else if (a === "--check") opt.check = true;
  else if (a === "--json") opt.json = true;
  else if (a === "--md") opt.md = true;
  else if (a === "--edges") opt.edges = args[++i];
  else if (a === "--md-image") opt.mdImage = args[++i];
  else if (a === "--formats") opt.formats = String(args[++i]).split(",").map((f) => f.trim()).filter(Boolean);
  else if (a === "--list-themes") { console.log(listThemes().join("\n")); process.exit(0); }
  else if (a === "-h" || a === "--help") { console.log(HELP); process.exit(0); }
  else if (a.startsWith("--")) { console.error(`Unknown option ${a}\n\n${HELP}`); process.exit(1); }
  else inputs.push(path.resolve(a));
}
if (!inputs.length) { console.error(HELP); process.exit(1); }
const badFormat = (opt.formats || []).find((f) => !FORMATS.includes(f));
if (badFormat) { console.error(`Unknown format "${badFormat}". Use any of: ${FORMATS.join(",")}`); process.exit(1); }
if (!["orthogonal", "curved"].includes(opt.edges)) { console.error(`--edges must be orthogonal or curved`); process.exit(1); }
if (!["png", "svg", "auto"].includes(opt.mdImage)) { console.error(`--md-image must be png, svg or auto`); process.exit(1); }

let theme, alt;
try {
  const file = resolveTheme(opt.theme, opt.dark);
  theme = loadTheme(file);
  const p = partnerTheme(file);
  alt = p ? loadTheme(p) : null;
} catch (e) { console.error(e.message); process.exit(1); }
const light = theme.dark ? alt : theme, dark = theme.dark ? theme : alt;

const isMd = (f) => /\.(md|markdown)$/i.test(f);
const files = inputs.flatMap((p) => {
  if (!fs.existsSync(p)) { console.error(`Not found: ${p}`); process.exit(1); }
  if (!fs.statSync(p).isDirectory()) return [p];
  return fs.readdirSync(p).filter((f) => (opt.md ? isMd(f) && !/\.rendered\.md$/i.test(f) : f.endsWith(".mmd"))).sort().map((f) => path.join(p, f));
});
if (!files.length) { console.error(`No ${opt.md ? ".md" : ".mmd"} files found.`); process.exit(1); }

// ---------- jobs: one per .mmd file, one per ```mermaid block in a Markdown file
const titleOf = (code, fallback) => (code.match(/^\s*%%\s*title:\s*(.+)$/m) || [, fallback])[1].trim();
const jobs = [], docs = [];
for (const file of files) {
  if (isMd(file)) {
    const text = fs.readFileSync(file, "utf8"), base = path.basename(file).replace(/\.(md|markdown)$/i, "");
    const root = opt.out || path.dirname(file);
    let mdOut = path.join(root, path.basename(file));
    if (path.resolve(mdOut) === path.resolve(file)) mdOut = path.join(root, `${base}.rendered.md`);
    const doc = { file, text, mdOut, root, replacements: [] };
    docs.push(doc);
    for (const b of mermaidBlocks(text)) {
      const name = `${base}-${b.index}`;
      jobs.push({ file, name, code: b.code, dest: path.join(root, "diagrams"), title: titleOf(b.code, `${base} diagram ${b.index}`),
                  formats: opt.formats || ["svg", "png", ...(opt.mdImage === "auto" ? ["auto"] : [])], doc, block: b });
    }
    if (!mermaidBlocks(text).length) console.error(`skip ${path.basename(file)}: no \`\`\`mermaid blocks`);
  } else {
    const name = path.basename(file).replace(/\.mmd$/i, ""), code = fs.readFileSync(file, "utf8");
    jobs.push({ file, name, code, dest: opt.out || path.dirname(file), title: titleOf(code, name), formats: opt.formats || FORMATS });
  }
}

// ---------- browser: CHROME_PATH, or the usual Chrome / Edge / Chromium locations
function findChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const c = {
    darwin: ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
    linux: ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium", "/usr/bin/microsoft-edge"],
    win32: [`${process.env["PROGRAMFILES"]}\\Google\\Chrome\\Application\\chrome.exe`, `${process.env["PROGRAMFILES(X86)"]}\\Google\\Chrome\\Application\\chrome.exe`,
            `${process.env["LOCALAPPDATA"]}\\Google\\Chrome\\Application\\chrome.exe`, `${process.env["PROGRAMFILES(X86)"]}\\Microsoft\\Edge\\Application\\msedge.exe`],
  }[os.platform()] || [];
  const hit = c.find((p) => p && fs.existsSync(p));
  if (!hit) { console.error("No Chrome, Edge or Chromium found. Set CHROME_PATH to the browser executable."); process.exit(1); }
  return hit;
}

// Card classes apply to flowcharts, state and ER diagrams, icons to flowcharts and state diagrams;
// other types reject classDef.
function prep(src, t) {
  const kind = diagramKind(src);
  if (kind === "er") return src + "\n" + classDefs(t) + "\n";
  if (kind !== "flowchart" && kind !== "state") return src;
  return src.replace(/\bi:([a-z0-9-]+)/g, (_, n) => icon(n, t.icon)) + "\n" + classDefs(t) + "\n";
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function html(title, svg, t) {
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<style>${fontCss(t)}
:root{color-scheme:${t.dark ? "dark" : "light"}}
body{margin:0;background:${t.page};font-family:'${t.font}',Inter,sans-serif;color:${t.text}}
main{max-width:1400px;margin:0 auto;padding:32px 16px}
h1{font-size:18px;font-weight:600;margin:0 0 16px}
.card{background:${t.pageCard};border:1px solid ${t.pageBorder};border-radius:16px;padding:24px;overflow-x:auto}
.card svg{max-width:100%;height:auto;display:block;margin:0 auto}
</style></head><body><main><h1>${esc(title)}</h1><div class="card">${svg}</div></main></body></html>`;
}

// One SVG holding the light and dark renders; the visible one follows prefers-color-scheme.
function autoSvg(lightSvg, darkSvg, title, desc) {
  const vb = lightSvg.match(/viewBox="([^"]+)"/)[1].split(/\s+/).map(Number);
  const [w, h] = [Math.ceil(vb[2]), Math.ceil(vb[3])];
  const inner = (s, cls) => `<g class="${cls}">` + s.replace(/^<svg[^>]*>/, (tag) => tag
    .replace(/\s(width|height)="[^"]*"/g, "").replace(/max-width:\s*[\d.]+px;?\s*/, "").replace(/^<svg\b/, `<svg width="${w}" height="${h}"`)) + `</g>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-labelledby="pd-title pd-desc">` +
    `<title id="pd-title">${esc(title)}</title><desc id="pd-desc">${esc(desc)}</desc>` +
    `<style>.pd-dark{display:none}@media (prefers-color-scheme: dark){.pd-light{display:none}.pd-dark{display:inline}}</style>` +
    inner(lightSvg, "pd-light") + inner(darkSvg, "pd-dark") + `</svg>`;
}

// ---------- render
const PAGE = `<!doctype html><html><head><meta charset="utf-8"><style>${fontCss(theme)} body{margin:0;background:#fff}</style>
<script>${fs.readFileSync(path.join(pkgDir("mermaid"), "dist/mermaid.min.js"), "utf8")}</script></head><body><div id="out"></div></body></html>`;

async function render(page, id, code, t, title) {
  const cfg = { ...mermaidConfig(t), themeCSS: themeCss(t) };
  await page.evaluate(async (id, code, cfg, radius) => {
    mermaid.initialize(cfg);
    await document.fonts.ready;
    const { svg } = await mermaid.render(id, code);
    const out = document.getElementById("out");
    out.innerHTML = svg;
    const el = out.querySelector("svg");
    await Promise.all([...el.querySelectorAll("img")].map((i) => (i.complete ? 0 : new Promise((r) => (i.onload = i.onerror = r)))));
    el.querySelectorAll(".node rect:not(.divider)").forEach((r) => { r.setAttribute("rx", radius.node); r.setAttribute("ry", radius.node); });
    el.querySelectorAll(".cluster rect").forEach((r) => { r.setAttribute("rx", radius.cluster); r.setAttribute("ry", radius.cluster); });
    // Group captions in the top-left corner, inset from the border.
    el.querySelectorAll("g.cluster").forEach((g) => {
      const r = g.querySelector(":scope > rect"), l = g.querySelector(":scope > g.cluster-label");
      if (!r || !l) return;
      const inset = Math.max(14, radius.cluster);
      l.setAttribute("transform", `translate(${+r.getAttribute("x") + inset}, ${+r.getAttribute("y") + 12})`);
    });
    el.querySelectorAll("rect.actor").forEach((r) => { r.setAttribute("rx", radius.actor); r.setAttribute("ry", radius.actor); });
  }, id, code, cfg, t.radius);
  // Straight edges between side centres (flowcharts and state diagrams).
  if (opt.edges === "orthogonal" && ["flowchart", "state"].includes(diagramKind(code))) {
    const routes = await routeEdges(await page.$eval("#out svg", collectGeometry));
    await page.$eval("#out svg", applyRoutes, routes, Math.max(6, Math.min(12, t.radius.node)));
  }
  // Sticky notes and stickers from %% note / %% sticker lines.
  const notes = parseNotes(code);
  if (notes.length) {
    const missing = await page.$eval("#out svg", applyNotes, notes, `'${t.font}', system-ui, sans-serif`);
    for (const m of new Set(missing)) console.error(`warn note/sticker: no node "${m}" in ${id.replace(/^d_|_(light|dark)$/g, "")}`);
  }
  return page.evaluate((id, canvas, title) => {
    const el = document.querySelector("#out svg");
    el.style.background = canvas;
    // Accessible name and description (Mermaid adds them itself for accTitle / accDescr).
    const NS = "http://www.w3.org/2000/svg";
    const textOf = (n) => { const w = document.createTreeWalker(n, NodeFilter.SHOW_TEXT), parts = []; while (w.nextNode()) parts.push(w.currentNode.data.trim()); return parts.filter(Boolean).join(" "); };
    let t = el.querySelector(":scope > title"), d = el.querySelector(":scope > desc");
    if (!t) { t = document.createElementNS(NS, "title"); t.id = `${id}-title`; t.textContent = title; el.prepend(t); }
    if (!d) {
      const kind = (el.getAttribute("aria-roledescription") || "diagram").replace(/-v2$/, "").replace(/^flowchart.*/, "flowchart");
      const names = [...new Set([...el.querySelectorAll("g.node, text.actor, g.mindmap-node, g.taskWrapper, g.eventWrapper")]
        .map(textOf).filter(Boolean))];
      d = document.createElementNS(NS, "desc"); d.id = `${id}-desc`;
      d.textContent = `${kind[0].toUpperCase() + kind.slice(1)} diagram${names.length ? ` with ${names.length} parts: ${names.slice(0, 15).join(", ")}${names.length > 15 ? ", ..." : ""}` : ""}.`;
      t.after(d);
    }
    // Grow the canvas if re-routed edges reach past it.
    const vb = el.viewBox.baseVal, bb = el.getBBox(), pad = 12;
    const x0 = Math.min(vb.x, bb.x - pad), y0 = Math.min(vb.y, bb.y - pad);
    const x1 = Math.max(vb.x + vb.width, bb.x + bb.width + pad), y1 = Math.max(vb.y + vb.height, bb.y + bb.height + pad);
    if (x0 < vb.x || y0 < vb.y || x1 > vb.x + vb.width || y1 > vb.y + vb.height) {
      el.setAttribute("viewBox", `${x0} ${y0} ${x1 - x0} ${y1 - y0}`);
      if (el.style.maxWidth) el.style.maxWidth = `${x1 - x0}px`;
    }
    const bg = document.createElementNS(NS, "rect");
    Object.entries({ class: "pd-bg", x: vb.x, y: vb.y, width: vb.width, height: vb.height, fill: canvas }).forEach(([k, v]) => bg.setAttribute(k, v));
    d.after(bg);
    el.setAttribute("role", "img");
    el.setAttribute("aria-labelledby", `${t.id || ""} ${d.id || ""}`.trim());
    return { svg: new XMLSerializer().serializeToString(el), title: t.textContent, desc: d.textContent };
  }, id, t.canvas, title);
}

const browser = await puppeteer.launch({ executablePath: findChrome(), headless: true, args: ["--no-sandbox"] });
let failed = 0, flagged = 0;
const reports = [];
const log = (...m) => { if (!opt.json) console.log(...m); };
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 2400, height: 1600, deviceScaleFactor: opt.scale });
  await page.setContent(PAGE, { waitUntil: "load" });

  for (const job of jobs) {
    const { name, code: raw, dest, title, formats } = job;
    fs.mkdirSync(dest, { recursive: true });
    const id = `d_${name.replace(/\W/g, "_")}`;
    try {
      // Light/dark partner first (for the auto SVG), the chosen theme last so the page shows it for the PNG.
      const other = formats.includes("auto") && light && dark ? (theme === light ? dark : light) : null;
      const o = other && await render(page, `${id}_${other.dark ? "dark" : "light"}`, prep(raw, other), other, title);
      const main = await render(page, `${id}_${theme.dark ? "dark" : "light"}`, prep(raw, theme), theme, title);
      const out = (ext) => path.join(dest, `${name}.${ext}`), written = [];
      if (formats.includes("svg")) { fs.writeFileSync(out("svg"), main.svg); written.push("svg"); }
      if (formats.includes("png")) { await (await page.$("#out svg")).screenshot({ path: out("png"), omitBackground: false }); written.push("png"); }
      if (formats.includes("html")) { fs.writeFileSync(out("html"), html(title, main.svg, theme)); written.push("html"); }
      if (o) { fs.writeFileSync(out("auto.svg"), theme === light ? autoSvg(main.svg, o.svg, main.title, main.desc) : autoSvg(o.svg, main.svg, main.title, main.desc)); written.push("auto.svg"); }
      log(`ok   ${name}  ->  ${path.join(dest, name)}.{${written.join(",")}}`);
      if (job.doc) {
        const ext = opt.mdImage === "auto" ? (o ? "auto.svg" : "svg") : opt.mdImage;
        const rel = path.relative(path.dirname(job.doc.mdOut), out(ext)).split(path.sep).join("/");
        job.doc.replacements.push({ ...job.block, alt: title, src: rel });
      }
      const r = await page.$eval("#out svg", measureLayout, diagramKind(raw));
      const p = problems(r), w = warnings(r);
      if (p.length) flagged++;
      reports.push({ file: job.file, name, ...r, problems: p, warnings: w });
      log(`     check ${summary(r)}`);
      for (const m of [...p, ...w]) log(`       - ${m}`);
    } catch (e) {
      failed++;
      console.error(`FAIL ${name}: ${String(e.message || e).split("\n")[0]}`);
    }
  }
  for (const d of docs) {
    if (!d.replacements.length) continue;
    fs.mkdirSync(path.dirname(d.mdOut), { recursive: true });
    fs.writeFileSync(d.mdOut, replaceBlocks(d.text, d.replacements));
    log(`md   ${path.basename(d.file)}  ->  ${d.mdOut} (${d.replacements.length} diagram${d.replacements.length > 1 ? "s" : ""})`);
  }
} finally {
  await browser.close();
}
if (opt.json) console.log(JSON.stringify(reports, null, 2));
if (flagged && !opt.json) console.log(`\n${flagged} diagram(s) have layout problems. Fix the .mmd (see SKILL.md, "Fix layout problems") and render again.`);
process.exit(failed ? 1 : opt.check && flagged ? 2 : 0);
