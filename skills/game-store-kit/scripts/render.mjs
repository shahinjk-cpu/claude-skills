#!/usr/bin/env node
// Render HTML templates or SVG files to exact-size PNGs with headless Chrome.
// Usage: node render.mjs jobs.json [--brand store-assets/brand.json]
// jobs.json: [{ "template": "screenshot" | "feature" | "splash" | "/abs/or/rel/file.html|.svg",
//               "out": "store-assets/play-store/screenshots/phone-01.png", "w": 1080, "h": 1920, "data": {...} }]
// Built-in templates live in ../templates/<name>.html and receive window.BRAND and window.JOB.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, args, outDir } from './lib.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const a = args();
const jobsFile = path.resolve(a._[0]);
const jobs = JSON.parse(fs.readFileSync(jobsFile, 'utf8'));
const brandPath = path.resolve(a.brand || path.join(outDir(), 'brand.json'));
const brand = fs.existsSync(brandPath) ? JSON.parse(fs.readFileSync(brandPath, 'utf8')) : {};
const base = path.dirname(brandPath); // relative asset paths in data/brand resolve from store-assets/

// turn any relative path-looking string into file:// URL so templates can load it
const fix = v => {
  if (typeof v === 'string' && /\.(png|jpe?g|webp|svg|gif|ttf|otf|woff2?)$/i.test(v) && !/^(https?|file|data):/.test(v)) {
    const p = path.isAbsolute(v) ? v : path.resolve(base, v);
    return pathToFileURL(p).href;
  }
  if (Array.isArray(v)) return v.map(fix);
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, fix(x)]));
  return v;
};

const browser = await launch();
for (const job of jobs) {
  const ctx = await browser.newContext({ viewport: { width: job.w, height: job.h }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => m.type() === 'error' && errs.push(m.text()));
  let target = job.template;
  if (!/[\/.]/.test(target)) target = path.join(here, '..', 'templates', target + '.html');
  else target = path.resolve(base, target);
  if (target.endsWith('.svg')) {
    const svg = fs.readFileSync(target, 'utf8');
    await page.setContent(`<html><body style="margin:0;background:${job.data?.background || 'transparent'}"><div style="width:${job.w}px;height:${job.h}px">${svg.replace(/<\?xml[^>]*>/, '').replace(/<svg/, '<svg width="100%" height="100%" preserveAspectRatio="xMidYMid meet"')}</div></body></html>`);
  } else {
    await page.addInitScript(([b, j]) => { window.BRAND = b; window.JOB = j; }, [fix(brand), fix({ ...job, ...(job.data || {}) })]);
    await page.goto(pathToFileURL(target).href, { waitUntil: 'networkidle' });
  }
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }))); if (window.READY) await window.READY; });
  const out = path.resolve(job.out);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  await page.screenshot({ path: out, omitBackground: !!job.transparent, clip: { x: 0, y: 0, width: job.w, height: job.h } });
  console.log(`✓ ${path.relative(process.cwd(), out)} ${job.w}x${job.h}${errs.length ? '  ⚠ ' + errs.join(' | ') : ''}`);
  await ctx.close();
}
await browser.close();
