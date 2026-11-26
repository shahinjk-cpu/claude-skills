// Shared helpers: launch Chrome, tiny static server.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';

export async function launch() {
  const tries = [{ channel: 'chrome' }, { channel: 'msedge' }, {}];
  let lastErr;
  for (const opt of tries) {
    try { return await chromium.launch({ headless: true, ...opt, args: ['--autoplay-policy=no-user-gesture-required', '--allow-file-access-from-files'] }); }
    catch (e) { lastErr = e; }
  }
  throw new Error('No Chrome/Chromium found. Install Google Chrome or run `npx playwright install chromium`.\n' + lastErr);
}

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.svg': 'image/svg+xml', '.webp': 'image/webp',
  '.wasm': 'application/wasm', '.mp3': 'audio/mpeg', '.ogg': 'audio/ogg', '.wav': 'audio/wav', '.ttf': 'font/ttf', '.otf': 'font/otf',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.data': 'application/octet-stream', '.unityweb': 'application/octet-stream', '.pck': 'application/octet-stream' };

export function serve(root) {
  root = path.resolve(root);
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    let f = path.join(root, p);
    if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
    if (!fs.existsSync(f)) { res.writeHead(404); return res.end('404'); }
    let ext = path.extname(f).toLowerCase();
    const headers = { 'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp' };
    if (ext === '.gz') { headers['Content-Encoding'] = 'gzip'; headers['Content-Type'] = MIME[path.extname(f.slice(0, -3))] || 'application/octet-stream'; }
    if (ext === '.br') { headers['Content-Encoding'] = 'br'; headers['Content-Type'] = MIME[path.extname(f.slice(0, -3))] || 'application/octet-stream'; }
    res.writeHead(200, headers);
    fs.createReadStream(f).pipe(res);
  });
  return new Promise(r => server.listen(0, '127.0.0.1', () => r({ url: `http://127.0.0.1:${server.address().port}/`, close: () => server.close() })));
}

export function args(argv = process.argv.slice(2)) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) { const k = a.slice(2); const v = argv[i + 1]; if (v === undefined || v.startsWith('--')) o[k] = true; else { o[k] = v; i++; } }
    else o._.push(a);
  }
  return o;
}

export const sleep = ms => new Promise(r => setTimeout(r, ms));

// The game project the user is working in. All output goes to <projectRoot>/store-assets.
// Order: $GSK_PROJECT, nearest parent that already has store-assets/, nearest project marker, else cwd.
export function projectRoot(start = process.cwd()) {
  if (process.env.GSK_PROJECT) return path.resolve(process.env.GSK_PROJECT);
  const markers = ['.git', 'package.json', 'pubspec.yaml', 'project.godot', 'ProjectSettings', 'settings.gradle', 'settings.gradle.kts', 'app.json'];
  const up = test => { let d = path.resolve(start); for (;;) { if (test(d)) return d; const p = path.dirname(d); if (p === d) return null; d = p; } };
  const home = process.env.HOME && path.resolve(process.env.HOME);
  return up(d => fs.existsSync(path.join(d, 'store-assets', 'brand.json')))
      || up(d => d !== home && markers.some(m => fs.existsSync(path.join(d, m))))
      || path.resolve(start);
}
export const outDir = () => path.join(projectRoot(), 'store-assets');
