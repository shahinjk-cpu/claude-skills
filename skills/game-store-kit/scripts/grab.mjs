#!/usr/bin/env node
// Grab REAL game art as a transparent PNG: an in-game logo, title, character card... anything with a CSS selector.
// Everything else on the page is hidden, so the element is captured on a transparent background.
// Usage: node grab.mjs --root dist --selector ".logo svg" --out store-assets/brand/logo.png [--scale 4] [--query debug]
//        [--landscape] [--wait 2500] [--play play.mjs  (uses its before() to seed saves)]
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { launch, serve, args, sleep, outDir } from './lib.mjs';

const a = args();
if (!a.selector) { console.error('--selector required'); process.exit(1); }
const land = !!a.landscape, w = land ? 874 : 402, h = land ? 402 : 874;
const out = path.resolve(a.out || path.join(outDir(), 'brand', 'grab.png'));
let srv = null, url = a.url;
if (!url) { srv = await serve(a.root || '.'); url = srv.url; }
if (a.query) url += (url.includes('?') ? '&' : '?') + a.query;
const browser = await launch();
const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: +(a.scale || 4) });
const page = await ctx.newPage();
if (a.play) { const p = await import(pathToFileURL(path.resolve(a.play)).href); if (p.before) await p.before({ page, ctx }); }
await page.goto(url, { waitUntil: 'load' });
await sleep(+(a.wait || 2500));
const ok = await page.evaluate(sel => {
  const el = document.querySelector(sel); if (!el) return false;
  const keep = new Set(); for (let n = el; n; n = n.parentElement) keep.add(n);
  for (const n of document.querySelectorAll('body *')) {
    if (keep.has(n) || el.contains(n)) continue;
    n.style.setProperty('visibility', 'hidden', 'important');
  }
  for (const n of keep) { n.style.setProperty('background', 'transparent', 'important'); n.style.setProperty('box-shadow', 'none', 'important'); }
  document.documentElement.style.background = 'transparent'; document.body.style.background = 'transparent';
  el.style.setProperty('animation', 'none', 'important'); el.querySelectorAll('*').forEach(n => n.style.setProperty('animation-play-state', 'paused', 'important'));
  return true;
}, a.selector);
if (!ok) { console.error('selector not found: ' + a.selector); process.exit(2); }
await sleep(300);
fs.mkdirSync(path.dirname(out), { recursive: true });
// animated elements never become "stable", so clip the page screenshot to the element box instead
const box = await page.evaluate(sel => { const r = document.querySelector(sel).getBoundingClientRect(); return { x: r.x, y: r.y, width: r.width, height: r.height }; }, a.selector);
await page.screenshot({ path: out, omitBackground: true, clip: box, animations: 'disabled' });
console.log('✓ ' + out);
await browser.close(); srv?.close();
