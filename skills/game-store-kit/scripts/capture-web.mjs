#!/usr/bin/env node
// Play a web build (or any URL) in headless Chrome and capture frames while playing.
// Usage:
//   node capture-web.mjs --root build/web --out store-assets/work/raw [--play play.mjs]
//        [--landscape] [--w 402 --h 874 --dpr 3] [--duration 90] [--interval 1500] [--selector canvas] [--url http://localhost:5173] [--query debug]
// play.mjs (written per game by Claude) may export:
//   export async function before({ page, ctx })          // before load: seed localStorage save, etc.
//   export async function setup({ page, sleep, w, h })    // get past title screen / tutorial
//   export default async function step({ page, t, i, sleep, w, h, shot }) // called in a loop; `shot(tag)` forces a capture now
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { launch, serve, args, sleep, outDir } from './lib.mjs';

const a = args();
const land = !!a.landscape;
// default viewport = a modern phone screen (402x874 pt @3x = 1206x2622, ~19.5:9) so frames fill the phone mockup exactly
const w = +(a.w || (land ? 874 : 402)), h = +(a.h || (land ? 402 : 874)), dpr = +(a.dpr || 3);
const out = path.resolve(a.out || path.join(outDir(), 'work', 'raw'));
const duration = +(a.duration || 90) * 1000, interval = +(a.interval || 1500);
fs.mkdirSync(out, { recursive: true });

let srv = null, url = a.url;
if (!url) { srv = await serve(a.root || '.'); url = srv.url; }
if (a.query) url += (url.includes('?') ? '&' : '?') + String(a.query).replace(/^\?/, ''); // e.g. --query debug to enable a game's debug hooks
const browser = await launch();
const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dpr, hasTouch: !!a.touch, isMobile: !!a.touch });
const page = await ctx.newPage();
const logs = [];
page.on('console', m => logs.push(`[${m.type()}] ${m.text()}`));
page.on('pageerror', e => logs.push(`[pageerror] ${e.message}`));
let play = { default: defaultStep };
if (a.play) play = await import(pathToFileURL(path.resolve(a.play)).href + '?t=' + Date.now());
// before(): runs before the page loads, e.g. page.addInitScript to seed a save (skip tutorial, unlock content)
if (play.before) await play.before({ page, ctx, sleep, w, h });
await page.goto(url, { waitUntil: 'load', timeout: 120000 });
await sleep(+(a.wait || 3000));

// Warn when the game doesn't fill the viewport (wrong orientation => letterboxed captures)
const fill = await page.evaluate(() => { let best = null; for (const c of document.querySelectorAll('canvas')) { const r = c.getBoundingClientRect(); if (!best || r.width * r.height > best.w * best.h) best = { w: r.width, h: r.height }; } return best; });
if (fill && fill.w * fill.h < 0.6 * w * h) {
  const gameP = fill.h > fill.w;
  console.log(`⚠ ORIENTATION: main canvas is ${Math.round(fill.w)}x${Math.round(fill.h)} in a ${w}x${h} viewport — the game looks ${gameP ? 'PORTRAIT' : 'LANDSCAPE'}. Re-run ${gameP ? 'without --landscape' : 'with --landscape'}.`);
  if (!a['ignore-orientation']) { await browser.close(); srv?.close(); process.exit(3); }
}

let n = 0;
const shot = async (tag = '') => {
  n++;
  const file = path.join(out, `frame-${String(n).padStart(4, '0')}${tag ? '-' + tag.replace(/\W+/g, '_') : ''}.png`);
  const el = a.selector ? await page.$(a.selector) : null;
  await (el ? el.screenshot({ path: file }) : page.screenshot({ path: file }));
  return file;
};

const env = { page, sleep, w, h, shot };
if (play.setup) await play.setup(env);
await shot('start');

const t0 = Date.now();
let lastShot = Date.now(), i = 0;
while (Date.now() - t0 < duration) {
  if (await (play.default || defaultStep)({ ...env, t: Date.now() - t0, i: i++ }) === 'stop') break;
  if (Date.now() - lastShot >= interval) { await shot(); lastShot = Date.now(); }
}
fs.writeFileSync(path.join(out, '_console.log'), logs.join('\n'));
console.log(JSON.stringify({ frames: n, out, size: `${w * dpr}x${h * dpr}`, errors: logs.filter(l => /error/i.test(l)).slice(0, 10) }, null, 2));
await browser.close();
srv?.close();

// Generic fallback: mash a mix of common game inputs. Prefer a real play.mjs.
async function defaultStep({ page, i, sleep, w, h }) {
  const keys = ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'Space', 'KeyA', 'KeyD', 'KeyW', 'Enter', 'KeyZ', 'KeyX'];
  const r = Math.random();
  if (r < 0.45) { const k = keys[(Math.random() * keys.length) | 0]; await page.keyboard.down(k); await sleep(80 + Math.random() * 400); await page.keyboard.up(k); }
  else if (r < 0.8) await page.mouse.click(w * (0.2 + Math.random() * 0.6), h * (0.25 + Math.random() * 0.6));
  else { const x = w / 2, y = h * 0.6; await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + (Math.random() - 0.5) * w * 0.6, y + (Math.random() - 0.5) * h * 0.4, { steps: 8 }); await page.mouse.up(); }
  await sleep(120);
}
