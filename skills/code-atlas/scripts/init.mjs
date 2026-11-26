#!/usr/bin/env node
// code-atlas setup: makes the output folder, copies the viewer, and writes a starter config.json and theme.json
// from what it finds in the repository. Claude then reviews both files and edits them by hand.
//
//   node init.mjs [--root <repo>] [--out <dir>] [--force]
//
// Never overwrites config.json, theme.json or explain/ unless --force. Always refreshes index.html (the viewer).
// Adds the output folder to .git/info/exclude so it is never committed (it contains copies of the code).
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const gitTop = dir => { try { return execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: dir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch { return null; } };
const ROOT = path.resolve(arg('--root', gitTop(process.cwd()) || process.cwd()));
const OUT = path.resolve(arg('--out', path.join(ROOT, 'code-atlas')));
const force = process.argv.includes('--force');
fs.mkdirSync(path.join(OUT, 'explain'), { recursive: true });
fs.copyFileSync(path.join(HERE, '../assets/viewer.html'), path.join(OUT, 'index.html'));

// keep it out of git: local exclude, nothing to commit
const git = gitTop(ROOT);
if (git) { const ex = path.join(git, '.git/info/exclude'), rel = '/' + path.relative(git, OUT).split(path.sep).join('/') + '/'; /* anchored, so other folders with the same name are not hidden */ if (!rel.startsWith('/..')) { fs.mkdirSync(path.dirname(ex), { recursive: true }); const cur = fs.existsSync(ex) ? fs.readFileSync(ex, 'utf8') : ''; if (!cur.split('\n').includes(rel)) fs.appendFileSync(ex, `\n# code atlas (local only, contains copies of the code)\n${rel}\n`); } }

// files
let files = [];
try { files = execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard'], { cwd: ROOT, encoding: 'utf8', maxBuffer: 256e6 }).split('\n').filter(Boolean); }
catch { const walk = d => { for (const e of fs.readdirSync(path.join(ROOT, d), { withFileTypes: true })) { const p = d ? d + '/' + e.name : e.name; if (/^(node_modules|\.git|vendor|dist|build|target|\.venv|venv)$/.test(e.name)) continue; e.isDirectory() ? walk(p) : files.push(p); } }; walk(''); }
const CODE = /\.(js|mjs|cjs|jsx|ts|tsx|vue|svelte|astro|html?|py|go|rs|java|cs|c|h|cpp|cc|hpp|kt|kts|swift|scala|dart|php|rb|lua|ex|exs|sh|bash|css|scss|sql|r|jl|groovy)$|(^|\/)(Makefile|Dockerfile)$/;
const SKIP = /(^|\/)(node_modules|vendor|dist|build|out|target|\.venv|venv|__pycache__|coverage)\/|\.min\.|(^|\/)code-atlas\//;
const code = files.filter(f => CODE.test(f) && !SKIP.test(f));
const langs = {}; code.forEach(f => { const e = f.split('.').pop(); langs[e] = (langs[e] || 0) + 1; });

// ---------- theme: the project's own brand, when it has one ----------
const cssLike = files.filter(f => /\.(css|scss|sass|less)$/.test(f) && !SKIP.test(f)).slice(0, 200);
const tw = files.filter(f => /(^|\/)tailwind\.config\.(js|cjs|mjs|ts)$/.test(f) && !SKIP.test(f));
const themeFiles = files.filter(f => /(^|\/)(theme|tokens|colors|palette|brand)[^/]*\.(json|js|ts|css|scss)$/i.test(f) && !SKIP.test(f)).slice(0, 20);
const colors = [], fontFams = new Map(), fontFiles = [];
for (const f of [...new Set([...cssLike, ...tw, ...themeFiles])]) {
  let t = ''; try { t = fs.readFileSync(path.join(ROOT, f), 'utf8'); } catch { continue; }
  for (const m of t.matchAll(/(--[\w-]+|["']?[\w-]+["']?)\s*:\s*["']?(#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3})\b/g)) colors.push({ name: m[1].replace(/["']/g, ''), hex: expand(m[2]), file: f });
  for (const m of t.matchAll(/font-family\s*:\s*([^;}{]+)/g)) { const fam = m[1].split(',')[0].trim().replace(/["']/g, ''); if (fam && !/^(var|inherit|system-ui|sans-serif|serif|monospace)/.test(fam)) fontFams.set(fam, (fontFams.get(fam) || 0) + 1); }
  for (const m of t.matchAll(/@font-face\s*\{([^}]+)\}/g)) {
    const fam = /font-family\s*:\s*["']?([^;"']+)/.exec(m[1])?.[1]?.trim(), w = /font-weight\s*:\s*([^;]+)/.exec(m[1])?.[1]?.trim(), u = /url\(\s*["']?([^"')]+\.(?:woff2|woff|ttf|otf))["']?\s*\)/.exec(m[1])?.[1];
    if (fam && u && !/^https?:/.test(u)) { const p = path.posix.normalize(path.posix.join(path.posix.dirname(f), u.replace(/^\//, ''))); const abs = u.startsWith('/') ? ['public/', 'static/', ''].map(b => b + u.slice(1)).find(c => fs.existsSync(path.join(ROOT, c))) : p; if (abs && fs.existsSync(path.join(ROOT, abs))) fontFiles.push({ family: fam, weight: w || '400', path: abs }); }
  }
}
function expand(h) { return h.length === 4 ? '#' + [...h.slice(1)].map(c => c + c).join('') : h.toUpperCase(); }
function hsl(hex) { const r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2; let h = 0, s = 0; if (mx !== mn) { const d = mx - mn; s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn); h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h *= 60; } return [h, s, l]; }
function hex([h, s, l]) { const f = n => { const k = (n + h / 30) % 12, a = s * Math.min(l, 1 - l); return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))).toString(16).padStart(2, '0'); }; return ('#' + f(0) + f(8) + f(4)).toUpperCase(); }
const saturated = colors.filter(c => { const [, s, l] = hsl(c.hex); return s > .35 && l > .25 && l < .8; });
const named = saturated.find(c => /(^|-)(primary|brand|accent|main|g)$/.test(c.name.replace(/^--/, '')));
const freq = {}; saturated.forEach(c => freq[c.hex] = (freq[c.hex] || 0) + 1);
const accent = named?.hex || Object.entries(freq).sort((a, b) => b[1] - a[1])[0]?.[0] || null;
const pickVar = re => colors.find(c => re.test(c.name))?.hex;
const fams = [...fontFams.keys()];

// ---------- areas: top folders, or the folders inside a main source folder ----------
const top = f => f.includes('/') ? f.split('/')[0] : '(root)';
let buckets = {}; code.forEach(f => { const k = top(f); (buckets[k] ??= []).push(f); });
const biggest = Object.entries(buckets).sort((a, b) => b[1].length - a[1].length)[0];
if (biggest && biggest[1].length > code.length * .6 && biggest[0] !== '(root)') { // one main folder (src/, app/, lib/): use its sub-folders
  const inner = {}; biggest[1].forEach(f => { const seg = f.split('/'); const k = seg.length > 2 ? seg.slice(0, 2).join('/') : biggest[0] + ' (top)'; (inner[k] ??= []).push(f); });
  delete buckets[biggest[0]]; buckets = { ...inner, ...buckets };
}
let entries = Object.entries(buckets).sort((a, b) => b[1].length - a[1].length);
if (entries.length > 9) { const rest = entries.slice(8).flatMap(e => e[1]); entries = [...entries.slice(0, 8), ['(other)', rest]]; }
const base = hsl(accent || '#3B82F6'), s0 = Math.min(Math.max(base[1], .55), .85), l0 = Math.min(Math.max(base[2], .55), .68);
const ICONS = ['box', 'code', 'book', 'server', 'database', 'globe', 'cog', 'image', 'film', 'wrench', 'upload', 'palette', 'user'];
const areas = entries.map(([k, fs2], i) => {
  const id = k.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '').toLowerCase() || 'root';
  const match = k === '(root)' ? ['^[^/]+$'] : k === '(other)' ? [] : k.endsWith(' (top)') ? [`^${k.replace(' (top)', '')}/[^/]+$`] : [`^${k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/`];
  return { id, name: k === '(root)' ? 'Project root' : k === '(other)' ? 'Everything else' : k.replace(' (top)', ' (top level)'), sub: `${fs2.length} code files`, match, color: hex([(base[0] + i * 360 / entries.length) % 360, s0, l0]), icon: ICONS[i % ICONS.length], place: '' };
}).filter(a => a.match.length || a.id !== 'other');

const write = (f, obj) => { const p = path.join(OUT, f); if (fs.existsSync(p) && !force) return false; fs.writeFileSync(p, JSON.stringify(obj, null, 1) + '\n'); return true; };
const cfgWritten = write('config.json', {
  title: path.basename(ROOT),
  areas,
  content: [],
  exclude: [],
  groupNames: {},
  edges: [],
  lanes: null,
  world: { town: 'Town', neighbourhood: 'neighbourhood', building: 'building', person: 'person' },
  maxFileKB: 300, maxFiles: 4000, groupAt: 12,
});
const themeWritten = write('theme.json', {
  accent: accent || '#3B82F6',
  fonts: { head: fams[0] ? `'${fams[0]}', system-ui, sans-serif` : null, body: fams[1] || fams[0] ? `'${fams[1] || fams[0]}', system-ui, sans-serif` : null, mono: fams.find(f => /mono|code|courier/i.test(f)) ? `'${fams.find(f => /mono|code|courier/i.test(f))}', ui-monospace, monospace` : null },
  fontFiles: fontFiles.slice(0, 12),
  light: { bg: pickVar(/(^--)?(bg|background)$/) || undefined, text: pickVar(/(^--)?(text|foreground|fg)$/) || undefined },
  dark: {},
});
const glossWritten = write('explain/00-glossary.json', { glossary: JSON.parse(fs.readFileSync(path.join(HERE, '../assets/glossary.json'), 'utf8')) });

console.log(JSON.stringify({
  root: ROOT, out: OUT, codeFiles: code.length, languages: langs,
  wrote: { 'index.html': true, 'config.json': cfgWritten, 'theme.json': themeWritten, 'explain/00-glossary.json': glossWritten },
  brand: { accent, accentSource: named ? `${named.name} in ${named.file}` : accent ? 'most used strong colour' : 'none found: neutral blue default', colourCandidates: [...new Map(saturated.map(c => [c.hex, c])).values()].slice(0, 12).map(c => `${c.name} ${c.hex} (${c.file})`), fonts: fams.slice(0, 6), fontFiles: fontFiles.length },
  areas: areas.map(a => `${a.name}: ${a.sub}`),
  next: 'Review config.json (areas, names, content, world) and theme.json, then run scan.mjs.',
}, null, 1));
