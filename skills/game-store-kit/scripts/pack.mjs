#!/usr/bin/env node
// Final step: leave only what's needed to publish on Google Play, and keep the sources hidden for the next run.
//   store-assets/
//     play-store/     icon-512.png  feature-graphic-1024x500.png  screenshots/   -> upload in Play Console
//     android-icon/   foreground.png  background.png  (1024)  -> Android Studio Image Asset / Unity Player Settings icon
//     splash/         key-art splash: 1080x1920, 1920x1080, 2732x2732
//     capacitor-assets/  only when asked (brand.capacitorAssets): sources for npx @capacitor/assets generate
//     .kit/           (hidden) brand.json, plan.json, icon sources, logo/sprites/items, play script, key-art page,
//                     and only the frames the kit uses -> the next run restores it and keeps the exact same look
// Usage:
//   node pack.mjs [--dir store-assets]            pack (default)
//   node pack.mjs --restore [--dir store-assets]  start of a new run: move .kit/ back so build.mjs works again
//   node pack.mjs --no-kit                        pack without keeping sources (next run starts from scratch)
//   node pack.mjs --full                          keep everything visible (only drop work/build scratch)
import fs from 'node:fs';
import path from 'node:path';
import { args, outDir } from './lib.mjs';

const a = args();
const dir = path.resolve(a.dir || outDir());
const R = p => path.join(dir, p);
const KIT = R('.kit');
const OUTPUTS = new Set(['play-store', 'capacitor-assets', 'android-icon', 'splash', '.kit']);
const move = (from, to) => { fs.mkdirSync(path.dirname(to), { recursive: true }); fs.rmSync(to, { recursive: true, force: true }); fs.renameSync(from, to); };

// ------------------------------------------------------------------ restore
if (a.restore) {
  if (!fs.existsSync(KIT)) { console.log('No .kit in ' + dir + ' (first run): nothing to restore.'); process.exit(0); }
  const walk = (d, base = '') => { for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const relp = path.join(base, e.name), src = path.join(d, e.name);
    if (e.isDirectory()) walk(src, relp); else move(src, R(relp));
  } };
  walk(KIT);
  fs.rmSync(KIT, { recursive: true, force: true });
  console.log('Restored sources from .kit into ' + dir + ' (brand.json, plan.json, icon/, brand/, work/). Reuse them for the same look.');
  process.exit(0);
}

if (!fs.existsSync(R('play-store'))) { console.error('No play-store/ in ' + dir + ' — run build.mjs first'); process.exit(1); }

// ------------------------------------------------------------------ full: keep everything visible
if (a.full) {
  fs.rmSync(R('work/build'), { recursive: true, force: true });
  report('full');
  process.exit(0);
}

// ------------------------------------------------------------------ collect sources into .kit
if (!a['no-kit']) {
  const keep = new Set();
  for (const f of ['brand.json', 'plan.json', 'listing.json']) if (fs.existsSync(R(f))) keep.add(f);
  for (const d of ['icon', 'brand']) if (fs.existsSync(R(d))) keep.add(d);
  // play scripts, key-art pages, helper scripts written for this game
  if (fs.existsSync(R('work'))) for (const f of fs.readdirSync(R('work'))) if (/\.(mjs|js|html|txt)$/.test(f) && !f.startsWith('.')) keep.add('work/' + f);
  // only the frames/images the plan actually uses
  const plan = fs.existsSync(R('plan.json')) ? JSON.parse(fs.readFileSync(R('plan.json'), 'utf8')) : {};
  const scan = v => { if (typeof v === 'string') { if (/^work\//.test(v) && fs.existsSync(R(v))) keep.add(v); }
    else if (Array.isArray(v)) v.forEach(scan); else if (v && typeof v === 'object') Object.values(v).forEach(scan); };
  scan(plan);
  fs.rmSync(KIT, { recursive: true, force: true });
  for (const p of keep) move(R(p), path.join(KIT, p));
}

// ------------------------------------------------------------------ delete everything else
for (const e of fs.readdirSync(dir)) if (!OUTPUTS.has(e)) fs.rmSync(R(e), { recursive: true, force: true });
report(a['no-kit'] ? 'no-kit' : 'kit');

function report(mode) {
  const list = []; const walk = d => { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const f = path.join(d, e.name); e.isDirectory() ? walk(f) : list.push([path.relative(dir, f), fs.statSync(f).size]); } };
  walk(dir);
  const shown = list.filter(([f]) => !f.startsWith('.kit')), kit = list.filter(([f]) => f.startsWith('.kit'));
  for (const [f, s] of shown.sort()) console.log(`  ${f}  ${(s / 1024).toFixed(0)} KB`);
  const mb = l => (l.reduce((t, x) => t + x[1], 0) / 1e6).toFixed(1);
  console.log(`Packed ${dir}: ${shown.length} files (${mb(shown)} MB)` + (kit.length ? ` + hidden .kit/ ${kit.length} files (${mb(kit)} MB) for consistent reruns` : '') + (mode === 'full' ? ' [full]' : ''));
}
