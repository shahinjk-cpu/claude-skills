#!/usr/bin/env node
// Drive an Android emulator/device to play a game and capture frames (Unity APKs, or any APK).
// Coordinates accept pixels or percentages of the screen ("50%" "80%"), so plans work on any device.
//
//   node droid.mjs boot [--avd NAME] [--headless]          start (or reuse) an emulator, print screen info
//   node droid.mjs install <app.apk>                         install (replaces the existing install)
//   node droid.mjs launch <package> [--wait 40]              start fresh and wait until the game is drawing
//   node droid.mjs shot <out.png> [--view]                   screenshot; --view also writes <out>.view.png
//                                                            (small copy with a % grid, for Claude to look at)
//   node droid.mjs tap X Y | swipe X1 Y1 X2 Y2 [MS] | hold X Y [MS] | key NAME | text "abc"
//   node droid.mjs step <action...> --out DIR [--frames 3] [--gap 400]
//                                                            do one action, then capture frames of the result
//                                                            (the look -> decide -> act loop for games without hooks)
//   node droid.mjs play --plan plan.txt --out DIR [--duration 90] [--interval 1.2]
//                                                            loop a scripted plan while capturing in the background
//   node droid.mjs demo on|off                               clean status bar (9:41, full battery, no notifications)
//   node droid.mjs stop                                      shut down an emulator this tool started
// plan.txt lines: tap X Y | swipe X1 Y1 X2 Y2 MS | hold X Y MS | key NAME | text abc | wait MS | shot TAG | repeat N { ... }
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn, spawnSync } from 'node:child_process';
import { args, sleep, outDir } from './lib.mjs';

const SDK = process.env.ANDROID_HOME || process.env.ANDROID_SDK_ROOT ||
  (process.platform === 'darwin' ? path.join(os.homedir(), 'Library/Android/sdk')
    : process.platform === 'win32' ? path.join(process.env.LOCALAPPDATA || '', 'Android/Sdk') : path.join(os.homedir(), 'Android/Sdk'));
const exe = process.platform === 'win32' ? '.exe' : '';
const ADB = which('adb') || path.join(SDK, 'platform-tools', 'adb' + exe);
const EMU = which('emulator') || path.join(SDK, 'emulator', 'emulator' + exe);
const STATE = path.join(os.tmpdir(), 'game-store-kit-emulator.json');
const a = args();
const [cmd, ...rest] = a._;

function which(c) { const r = spawnSync(process.platform === 'win32' ? 'where' : 'which', [c], { encoding: 'utf8' }); return r.status === 0 ? r.stdout.split(/\r?\n/)[0].trim() : null; }
function adb(...a) { const r = spawnSync(ADB, a, { encoding: 'utf8', maxBuffer: 64 << 20 }); if (r.error) throw r.error; return (r.stdout || '').trim(); }
function adbBuf(...a) { const r = spawnSync(ADB, a, { maxBuffer: 256 << 20 }); return r.stdout; }
const sh = (...a) => adb('shell', ...a);
const online = () => spawnSync(ADB, ['get-state'], { encoding: 'utf8' }).stdout?.trim() === 'device';

let _size;
function size() {
  if (_size) return _size;
  const m = sh('wm', 'size').match(/(\d+)x(\d+)\s*$/m); let [w, h] = m ? [+m[1], +m[2]] : [1080, 2400];
  const rot = +((sh('dumpsys', 'input').match(/SurfaceOrientation:\s*(\d)/) || [])[1] || 0);
  if (rot % 2 === 1) [w, h] = [h, w];   // landscape game: coordinates follow the current rotation
  return (_size = { w, h, rot });
}
const px = (v, axis) => { const s = String(v); return s.endsWith('%') ? Math.round(parseFloat(s) / 100 * (axis === 'x' ? size().w : size().h)) : Math.round(+s); };

async function act(cmd, p) {
  switch (cmd) {
    case 'tap': return sh('input', 'tap', px(p[0], 'x'), px(p[1], 'y'));
    case 'swipe': return sh('input', 'swipe', px(p[0], 'x'), px(p[1], 'y'), px(p[2], 'x'), px(p[3], 'y'), p[4] || 250);
    case 'hold': return sh('input', 'swipe', px(p[0], 'x'), px(p[1], 'y'), px(p[0], 'x'), px(p[1], 'y'), p[2] || 800);
    case 'key': return sh('input', 'keyevent', /^\d+$/.test(p[0]) ? p[0] : 'KEYCODE_' + String(p[0]).toUpperCase().replace(/^KEYCODE_/, ''));
    case 'text': return sh('input', 'text', String(p.join(' ')).replace(/ /g, '%s'));
    case 'wait': return sleep(+p[0] || 500);
    default: throw new Error('unknown action ' + cmd);
  }
}

// visible system bars (status bar, navigation/gesture bar) as edge rects; empty when the game runs full screen
let _bars, _barsAt = 0;
function bars() {
  if (_bars && Date.now() - _barsAt < 4000) return _bars;
  const out = sh('dumpsys', 'window'); const seen = new Set(); _bars = [];
  for (const m of out.matchAll(/InsetsSource id=(\w+) type=(statusBars|navigationBars) frame=\[(\d+),(\d+)\]\[(\d+),(\d+)\] visible=(true|false)/g)) {
    if (seen.has(m[1])) continue; seen.add(m[1]);
    if (m[7] === 'true') _bars.push({ type: m[2], l: +m[3], t: +m[4], r: +m[5], b: +m[6] });
  }
  _barsAt = Date.now(); return _bars;
}
// crop box (l,t,r,b) of the screen minus visible bars on its edges
function cropBox() {
  const s = size(), W = s.w, H = s.h; let l = 0, t = 0, r = s.w, b = s.h;
  for (const x of bars()) {
    if (x.t === 0 && x.b < H / 3) t = Math.max(t, x.b);              // top bar
    else if (x.b === H && x.t > H * 2 / 3) b = Math.min(b, x.t);     // bottom bar
    else if (x.l === 0 && x.r < W / 3) l = Math.max(l, x.r);         // left (landscape)
    else if (x.r === W && x.l > W * 2 / 3) r = Math.min(r, x.l);     // right (landscape)
  }
  return [l, t, r, b];
}
function screencap(file, crop = !a['no-crop']) {
  const buf = adbBuf('exec-out', 'screencap', '-p');
  if (!buf || buf.length < 1000) throw new Error('screencap failed');
  fs.mkdirSync(path.dirname(path.resolve(file)), { recursive: true });
  fs.writeFileSync(file, buf);
  if (crop) {
    const [l, t, r, b] = cropBox(); const s = size();
    if (l || t || r !== s.w || b !== s.h)
      spawnSync('python3', ['-c', 'import sys\nfrom PIL import Image\nim=Image.open(sys.argv[1]); im.crop(tuple(map(int,sys.argv[2:6]))).save(sys.argv[1])', file, l, t, r, b]);
  }
  return file;
}
// small preview with a 10% grid so coordinates can be read off the image
function view(file) {
  const out = file.replace(/\.png$/, '.view.png');
  const py = `
import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert('RGB'); W = 540 if im.width < im.height else 960
im = im.resize((W, round(im.height * W / im.width))); d = ImageDraw.Draw(im, 'RGBA')
for i in range(1, 10):
    x = im.width * i // 10; y = im.height * i // 10
    d.line([(x, 0), (x, im.height)], fill=(255, 0, 255, 110), width=1); d.line([(0, y), (im.width, y)], fill=(255, 0, 255, 110), width=1)
    d.text((x + 2, 2), f'{i*10}%', fill=(255, 0, 255, 255)); d.text((2, y + 2), f'{i*10}%', fill=(255, 0, 255, 255))
im.save(sys.argv[2])`;
  const r = spawnSync('python3', ['-c', py, file, out], { encoding: 'utf8' });
  return r.status === 0 ? out : null;
}
// average brightness spread of a frame (0 = flat black/blank)
function contentScore(file) {
  const r = spawnSync('python3', ['-c', 'import sys\nfrom PIL import Image, ImageStat\nim=Image.open(sys.argv[1]).convert("L").resize((90,160))\nprint(sum(ImageStat.Stat(im).stddev))', file], { encoding: 'utf8' });
  return +r.stdout || 0;
}

// small, fast signature of a frame to tell "still the same picture" from "something changed"
function sig(file) {
  const r = spawnSync('python3', ['-c', 'import sys\nfrom PIL import Image\nprint(",".join(map(str,Image.open(sys.argv[1]).convert("L").resize((12,24)).tobytes())))', file], { encoding: 'utf8' });
  return (r.stdout || '').trim().split(',').map(Number);
}
const differ = (x, y) => !x || !y || x.length !== y.length ? true : Math.sqrt(x.reduce((t, v, i) => t + (v - y[i]) ** 2, 0) / x.length) > 6;
const OUT = d => path.resolve(d || path.join(outDir(), 'work', 'raw'));
// highest existing frame number, so new frames never overwrite earlier ones
const lastIndex = d => fs.readdirSync(d).reduce((m, f) => Math.max(m, +((f.match(/^frame-(\d+)/) || [])[1] || 0)), 0);

if (cmd === 'boot') {
  if (!online()) {
    const avd = a.avd || spawnSync(EMU, ['-list-avds'], { encoding: 'utf8' }).stdout.split(/\r?\n/).find(Boolean);
    if (!avd) { console.error('No device connected and no AVD found. Create one in Android Studio > Device Manager.'); process.exit(1); }
    const flags = ['-avd', avd, '-no-snapshot-save', '-no-boot-anim', '-no-audio', ...(a.headless ? ['-no-window'] : [])];
    const p = spawn(EMU, flags, { detached: true, stdio: 'ignore' }); p.unref();
    fs.writeFileSync(STATE, JSON.stringify({ startedByKit: true, avd }));
    console.log(`Booting ${avd}${a.headless ? ' (headless)' : ''}...`);
    adb('wait-for-device');
    while (sh('getprop', 'sys.boot_completed') !== '1') await sleep(1500);
    await sleep(2500);
  }
  const s = size();
  console.log(JSON.stringify({ device: adb('get-serialno'), android: sh('getprop', 'ro.build.version.release'), sdk: +sh('getprop', 'ro.build.version.sdk'), screen: `${s.w}x${s.h}`, density: +((sh('wm', 'density').match(/(\d+)\s*$/) || [])[1] || 0) }));
} else if (cmd === 'install') {
  if (!rest[0] || !fs.existsSync(rest[0])) { console.error('APK not found: ' + rest[0]); process.exit(1); }
  if (/\.aab$/i.test(rest[0])) { console.error('An .aab cannot be installed directly: ask for an APK (Unity: Build Settings > uncheck "Build App Bundle").'); process.exit(1); }
  const r = spawnSync(ADB, ['install', '-r', '-g', rest[0]], { encoding: 'utf8' });
  const msg = ((r.stdout || '') + (r.stderr || '')).trim();
  if (/NO_MATCHING_ABIS/.test(msg)) { console.error(`The APK has no native code for this emulator (${sh('getprop', 'ro.product.cpu.abilist')}). Unity: Player Settings > Other Settings > Target Architectures: enable ARM64 (also required by Google Play), rebuild.`); process.exit(1); }
  if (/UPDATE_INCOMPATIBLE|INCONSISTENT_CERTIFICATES/.test(msg)) { console.error('An install with a different signing key is already on the device. Uninstall it first: adb uninstall <package>'); process.exit(1); }
  if (r.status !== 0 || !/Success/.test(msg)) { console.error(msg); process.exit(1); }
  console.log('Success');
} else if (cmd === 'launch') {
  const pkg = rest[0]; const wait = +(a.wait || 40) * 1000;
  sh('am', 'force-stop', pkg);
  sh('monkey', '-p', pkg, '-c', 'android.intent.category.LAUNCHER', '1');
  // ready = the app has focus, the screen moved on from the first picture (system/engine splash, "Made with Unity",
  // loading) and then stayed stable for 2 checks; or it stayed stable for 5 checks (games without a splash)
  const t0 = Date.now(); let focused = false, drawing = false, first = null, prev = null, stable = 0, changed = false;
  const tmp = path.join(os.tmpdir(), 'gsk-launch.png');
  while (Date.now() - t0 < wait) {
    focused ||= sh('dumpsys', 'window').split('\n').some(l => /mCurrentFocus|mFocusedApp/.test(l) && l.includes(pkg));
    if (focused) {
      try {
        screencap(tmp, false); const g = sig(tmp);
        if (!first) first = g; else if (differ(g, first)) changed = true;
        stable = prev && !differ(g, prev) ? stable + 1 : 0; prev = g;
        drawing = contentScore(tmp) > 25;
        if (drawing && ((changed && stable >= 2) || stable >= 5)) break;
      } catch { }
    }
    await sleep(800);
  }
  _size = null; const s = size();
  console.log(JSON.stringify({ package: pkg, focused, drawing, secondsToFirstFrame: ((Date.now() - t0) / 1000).toFixed(1), screen: `${s.w}x${s.h}`, orientation: s.w > s.h ? 'landscape' : 'portrait' }));
  if (!focused) { console.error('The app did not come to the foreground. Is the package name right? (adb shell pm list packages | grep <name>)'); process.exit(2); }
} else if (cmd === 'shot') {
  const f = screencap(path.resolve(rest[0] || 'shot.png'));
  console.log(f + (a.view ? '\nview: ' + view(f) : ''));
} else if (['tap', 'swipe', 'hold', 'key', 'text'].includes(cmd)) {
  await act(cmd, rest);
} else if (cmd === 'step') {
  // e.g. node droid.mjs step tap 50% 80% --out raw --frames 3 --gap 400
  const out = OUT(a.out); fs.mkdirSync(out, { recursive: true });
  const n0 = lastIndex(out);
  await act(rest[0], rest.slice(1));
  const frames = [];
  for (let i = 0; i < +(a.frames || 2); i++) { await sleep(+(a.gap || 400)); frames.push(screencap(path.join(out, `frame-${String(n0 + i + 1).padStart(4, '0')}.png`))); }
  const last = frames[frames.length - 1];
  console.log(frames.join('\n') + (a.view !== false ? '\nview: ' + view(last) : ''));
} else if (cmd === 'play') {
  const out = OUT(a.out); fs.mkdirSync(out, { recursive: true });
  const lines = fs.readFileSync(a.plan, 'utf8').split(/\r?\n/).map(l => l.trim()).filter(l => l && !l.startsWith('#'));
  const end = Date.now() + +(a.duration || 90) * 1000, interval = +(a.interval || 1.2) * 1000;
  let n = lastIndex(out), busy = false;
  const shot = tag => { n++; return screencap(path.join(out, `frame-${String(n).padStart(4, '0')}${tag ? '-' + tag : ''}.png`)); };
  const timer = setInterval(() => { if (busy) return; busy = true; try { shot(); } catch { } busy = false; }, interval);
  const run = async (ls) => {
    for (let i = 0; i < ls.length && Date.now() < end; i++) {
      const [c, ...p] = ls[i].split(/\s+/);
      if (c === 'repeat') { // repeat N { ... }
        let depth = 0, j = i; const body = [];
        for (j = i + 1; j < ls.length; j++) { if (ls[j].startsWith('repeat')) depth++; if (ls[j] === '}') { if (depth-- === 0) break; } body.push(ls[j]); }
        for (let k = 0; k < +p[0] && Date.now() < end; k++) await run(body);
        i = j; continue;
      }
      if (c === 'shot') shot(p[0]); else await act(c, p);
    }
  };
  while (Date.now() < end) await run(lines);
  clearInterval(timer);
  console.log(JSON.stringify({ frames: n, out }));
} else if (cmd === 'demo') {
  const on = rest[0] !== 'off';
  const demo = (...e) => sh('am', 'broadcast', '-a', 'com.android.systemui.demo', '-e', 'command', ...e);
  if (on) {
    sh('settings', 'put', 'global', 'sysui_demo_allowed', '1');
    demo('enter'); demo('clock', '-e', 'hhmm', '0941'); demo('battery', '-e', 'level', '100', '-e', 'plugged', 'false');
    demo('network', '-e', 'wifi', 'show', '-e', 'level', '4'); demo('network', '-e', 'mobile', 'show', '-e', 'level', '4', '-e', 'datatype', 'none');
    demo('notifications', '-e', 'visible', 'false');
  } else demo('exit');
  console.log('demo mode ' + (on ? 'on' : 'off'));
} else if (cmd === 'stop') {
  const st = fs.existsSync(STATE) ? JSON.parse(fs.readFileSync(STATE, 'utf8')) : {};
  if (st.startedByKit && online()) { adb('emu', 'kill'); console.log('emulator stopped'); } else console.log('left running (not started by game-store-kit)');
  fs.rmSync(STATE, { force: true });
} else {
  console.log(fs.readFileSync(new URL(import.meta.url), 'utf8').split('\n').filter(l => l.startsWith('//')).map(l => l.slice(3)).join('\n'));
}
