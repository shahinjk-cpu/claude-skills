#!/usr/bin/env node
// code-atlas scanner: reads every code file in a repository (any language) and writes <out>/data.js for viewer.html.
//
//   node scan.mjs [--root <repo>] [--out <dir>] [--stamp] [--generic]
//
//   --root    repository to map (default: the git top level of the current folder, else the current folder)
//   --out     output folder (default: <root>/code-atlas). Holds config.json, theme.json, explain/, index.html, data.js
//   --stamp   record the current code hash on explanations that have none (run right after writing explanations)
//   --generic skip the optional precise parsers (TypeScript, Python ast) and use the plain-text reader everywhere
//
// How it reads code: a plain-text reader that works for any language (brace matching for C-like languages,
// indentation for Python-like ones, `end` matching for Ruby/Lua/Elixir, script blocks for Vue/Svelte/Astro/HTML).
// When the TypeScript compiler or python3 happen to be available it uses them for JS/TS and Python, which is
// more exact. Calls between files are matched by name and marked approximate when they are only a guess.
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { execFileSync } from 'child_process';
import { createRequire } from 'module';

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const flag = k => process.argv.includes(k);
const gitTop = dir => { try { return execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: dir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch { return null; } };
const ROOT = path.resolve(arg('--root', gitTop(process.cwd()) || process.cwd()));
const OUT = path.resolve(arg('--out', path.join(ROOT, 'code-atlas')));
const OUT_REL = path.relative(ROOT, OUT).split(path.sep).join('/');
const posix = p => p.split(path.sep).join('/');
const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');
const hash = s => crypto.createHash('sha1').update(s.replace(/\s+/g, ' ').trim()).digest('hex').slice(0, 10);
const reEsc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const CFG_PATH = path.join(OUT, 'config.json');
if (!fs.existsSync(CFG_PATH)) { console.error(`No ${CFG_PATH}. Run init.mjs first (it writes a starter config).`); process.exit(1); }
const CFG = JSON.parse(fs.readFileSync(CFG_PATH, 'utf8'));
const MAX_KB = CFG.maxFileKB ?? 300, MAX_FILES = CFG.maxFiles ?? 4000, GROUP_AT = CFG.groupAt ?? 12;

// ---------- optional precise parsers ----------
let ts = null;
if (!flag('--generic')) for (const base of [ROOT, process.cwd()]) { try { ts = createRequire(path.join(base, 'package.json'))('typescript'); break; } catch {} }
if (!ts && !flag('--generic')) { try { const g = execFileSync('npm', ['root', '-g'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); ts = createRequire(path.join(g, 'x.js'))('typescript'); } catch {} }
let PYTHON = null;
if (!flag('--generic')) for (const p of ['python3', 'python']) { try { execFileSync(p, ['-c', 'import ast'], { stdio: 'ignore' }); PYTHON = p; break; } catch {} }

// ---------- 1. which files ----------
// Never shown: dependencies, builds, generated or minified code, lockfiles, binaries, and anything that looks like a secret.
const DEFAULT_EXCLUDE = [
  '(^|/)(node_modules|vendor|bower_components|dist|build|out|target|bin|obj|coverage|\\.next|\\.nuxt|\\.svelte-kit|\\.astro|\\.venv|venv|env|__pycache__|\\.git|\\.idea|\\.vscode|\\.gradle|Pods|DerivedData)/',
  '(^|/)\\.env(\\.|$)', '\\.(pem|key|p12|pfx|crt|cer|keystore|jks)$', '(^|/)(id_rsa|id_ed25519)', '(secret|credential|password)s?[^/]*$',
  '(^|/)(package-lock\\.json|yarn\\.lock|pnpm-lock\\.yaml|Cargo\\.lock|Gemfile\\.lock|poetry\\.lock|composer\\.lock|go\\.sum|bun\\.lockb)$',
  '\\.min\\.(js|css)$', '\\.(map|snap)$', '(^|/)(generated|__generated__|gen)/',
];
const EXCLUDE = [...DEFAULT_EXCLUDE, ...(CFG.exclude || [])].map(r => new RegExp(r));
if (OUT_REL && !OUT_REL.startsWith('..')) EXCLUDE.push(new RegExp('^' + reEsc(OUT_REL) + '/'));
function listFiles() {
  try { return execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard'], { cwd: ROOT, encoding: 'utf8', maxBuffer: 256e6 }).split('\n').filter(Boolean); }
  catch { const out = []; const walk = d => { for (const e of fs.readdirSync(path.join(ROOT, d), { withFileTypes: true })) { const p = d ? d + '/' + e.name : e.name; if (EXCLUDE.some(r => r.test(p + (e.isDirectory() ? '/' : '')))) continue; e.isDirectory() ? walk(p) : out.push(p); } }; walk(''); return out; }
}
const LANG = { // extension -> family used by the plain-text reader
  js: 'js', mjs: 'js', cjs: 'js', jsx: 'js', ts: 'js', tsx: 'js', mts: 'js', cts: 'js',
  vue: 'sfc', svelte: 'sfc', astro: 'sfc', html: 'sfc', htm: 'sfc',
  py: 'py', pyw: 'py', go: 'go', rs: 'rust', java: 'c', cs: 'c', c: 'c', h: 'c', cpp: 'c', cc: 'c', cxx: 'c', hpp: 'c', hh: 'c', m: 'c', mm: 'c',
  kt: 'kotlin', kts: 'kotlin', swift: 'swift', scala: 'scala', sc: 'scala', dart: 'c', groovy: 'c', gradle: 'c', php: 'php',
  rb: 'ruby', rake: 'ruby', lua: 'lua', ex: 'elixir', exs: 'elixir', sh: 'sh', bash: 'sh', zsh: 'sh', ps1: 'c', r: 'r', R: 'r', jl: 'ruby',
  css: 'style', scss: 'style', sass: 'style', less: 'style', sql: 'plain', graphql: 'plain', gql: 'plain', proto: 'plain', tf: 'plain', hcl: 'plain',
};
const extOf = f => { const b = path.posix.basename(f); if (b === 'Makefile' || b === 'makefile' || b === 'GNUmakefile') return 'make'; if (b === 'Dockerfile') return 'docker'; if (b === 'package.json' && !f.includes('/')) return 'pkg'; return b.includes('.') ? b.split('.').pop() : ''; };
const INCLUDE = (CFG.include || []).map(r => new RegExp(r)); // extra non-code files to show as boxes (settings files, schemas)
const isCode = f => LANG[extOf(f)] || ['make', 'docker', 'pkg'].includes(extOf(f)) || INCLUDE.some(r => r.test(f));
const all = listFiles().filter(f => !EXCLUDE.some(r => r.test(f)) && fs.existsSync(path.join(ROOT, f)));
const skipped = [];
let codeFiles = all.filter(f => {
  if (!isCode(f)) return false;
  const st = fs.statSync(path.join(ROOT, f));
  if (st.size > MAX_KB * 1024) { skipped.push(`${f} (over ${MAX_KB} KB)`); return false; }
  const head = fs.readFileSync(path.join(ROOT, f)).subarray(0, 4096);
  if (head.includes(0)) { skipped.push(`${f} (binary)`); return false; }
  const txt = head.toString('utf8');
  if (/(^|\n)[^\n]{2000,}/.test(txt) && !/\n/.test(txt.slice(0, 2000))) { skipped.push(`${f} (minified)`); return false; }
  return true;
});
if (codeFiles.length > MAX_FILES) { skipped.push(`${codeFiles.length - MAX_FILES} more files (over maxFiles ${MAX_FILES}; narrow "exclude" in config.json)`); codeFiles = codeFiles.slice(0, MAX_FILES); }

// ---------- 2. areas, content boxes, groups ----------
const nodes = new Map(), edges = [];
const addNode = n => { nodes.set(n.id, n); return n; };
const addEdge = (from, to, kind, approx) => { if (from && to && from !== to) edges.push(approx ? { from, to, kind, approx: true } : { from, to, kind }); };
const areas = (CFG.areas || []).map(a => ({ ...a, re: (a.match || []).map(r => new RegExp(r)) }));
const areaOf = f => areas.find(a => a.re.some(r => r.test(f)))?.id || 'other';
const contents = (CFG.content || []).map(c => ({ ...c, re: (c.match || []).map(r => new RegExp(r)) }));
const contentOf = f => contents.find(c => c.re.some(r => r.test(f)));
codeFiles = codeFiles.filter(f => !contentOf(f));
const usedAreas = new Set([...codeFiles.map(areaOf), ...contents.map(c => c.area)]);
const areaList = [...areas, ...(usedAreas.has('other') && !areas.some(a => a.id === 'other') ? [{ id: 'other', name: 'Everything else', sub: 'files no area claims', icon: 'box' }] : [])].filter(a => usedAreas.has(a.id));
areaList.forEach(a => addNode({ id: 'area:' + a.id, kind: 'area', name: a.name, sub: a.sub || '' }));
const fileSet = new Set(codeFiles);
for (const f of codeFiles) { const code = read(f); addNode({ id: f, kind: 'file', name: path.posix.basename(f), path: f, parent: 'area:' + areaOf(f), lang: extOf(f), code, lines: code.split('\n').length }); }
for (const c of contents) { const files = all.filter(f => c.re.some(r => r.test(f))); if (files.length) addNode({ id: c.id, kind: 'content', name: c.name, parent: 'area:' + c.area, files, what: c.what || '' }); }
// Big containers get folder groups, again and again, so no screen shows more than about a dozen boxes.
function groupUp(parentId, members) {
  if (members.length <= GROUP_AT) return;
  const dirs = members.map(n => n.path.split('/').slice(0, -1));
  let common = 0; while (dirs.every(d => d.length > common && d[common] === dirs[0][common])) common++;
  const by = new Map(); for (const n of members) { const seg = n.path.split('/'); const key = seg.length - 1 > common ? seg.slice(0, common + 1).join('/') : null; if (!by.has(key)) by.set(key, []); by.get(key).push(n); }
  if (by.size === 1 && by.has(null)) return; // all in one folder: nothing to split
  for (const [dir, list] of by) {
    if (dir === null || list.length < 2) continue;
    const gid = 'group:' + dir, g = addNode({ id: gid, kind: 'group', name: (CFG.groupNames || {})[dir] || path.posix.basename(dir), path: dir + '/', parent: parentId });
    list.forEach(n => n.parent = gid); groupUp(g.id, list);
  }
}
for (const a of areaList) groupUp('area:' + a.id, [...nodes.values()].filter(n => n.parent === 'area:' + a.id && n.kind === 'file'));

// ---------- 3. reading code: functions, calls, imports ----------
const KEYWORDS = new Set('if else for foreach while do switch case catch try finally return new delete typeof sizeof instanceof await yield throw function def class struct enum interface fn func fun match when elif except with lambda using lock synchronized defer go select super this self print println printf echo require include import export from in of and or not is'.split(' '));
const COMMON = new Set('get set init main run start stop open close read write add remove update create make build load save parse format log push pop map filter reduce call apply bind then catch next done send emit on off test describe it expect assert render handle setup toString equals hashCode length size'.split(' '));
function braceEnd(L, from, startCol) { // the line where the block opened at/after (from, startCol) closes; skips strings and comments
  let depth = 0, seen = false, inS = null, block = false;
  for (let i = from; i < L.length && i < from + 4000; i++) {
    const s = L[i]; let j = i === from ? startCol : 0;
    for (; j < s.length; j++) {
      const c = s[j], n = s[j + 1];
      if (block) { if (c === '*' && n === '/') { block = false; j++; } continue; }
      if (inS) { if (c === '\\') { j++; continue; } if (c === inS) inS = null; continue; }
      if (c === '/' && n === '/') break; if (c === '#' && /^\s*#/.test(s) && !seen) break;
      if (c === '/' && n === '*') { block = true; j++; continue; }
      if (c === '"' || c === "'" || c === '`') { inS = c; continue; }
      if (c === '{') { depth++; seen = true; } else if (c === '}') { depth--; if (seen && depth === 0) return i; }
    }
    if (inS !== '`') inS = null; // most string kinds end at the line end
    if (!seen && i > from + 2) return -1; // no block (a declaration without a body)
  }
  return -1;
}
const DECL = {
  go: [/^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*[[(]/],
  rust: [/^\s*(?:pub(?:\([^)]*\))?\s+)?(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+"[^"]*"\s+)?fn\s+([A-Za-z_]\w*)/],
  kotlin: [/^\s*(?:[\w@]+\s+)*fun\s+(?:<[^>]*>\s*)?(?:[\w.]+\.)?([A-Za-z_]\w*)\s*\(/],
  swift: [/^\s*(?:[\w@]+\s+)*func\s+([A-Za-z_]\w*)/],
  scala: [/^\s*(?:[\w]+\s+)*def\s+([A-Za-z_]\w*)/],
  php: [/^\s*(?:(?:public|private|protected|static|final|abstract)\s+)*function\s+&?([A-Za-z_]\w*)\s*\(/],
  js: [/^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\(/, /^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*(?::\s*[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)/, /^\s*(?:(?:public|private|protected|static|async|get|set|override|readonly)\s+)*([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\([^)]*\)\s*(?::\s*[^{]+)?\{\s*$/, /^\s*([A-Za-z_$][\w$]*)\s*:\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)/],
  c: [/^\s*(?:[\w<>\[\],.?@:*&~]+\s+)+?\**([A-Za-z_~][\w]*)\s*\([^;]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:throws\s+[\w.,\s]+)?(?:->\s*[\w<>:,*&\s]+)?\s*(?:\{.*)?$/],
  sh: [/^\s*(?:function\s+)?([A-Za-z_][\w-]*)\s*\(\)\s*\{?\s*$/, /^\s*function\s+([A-Za-z_][\w-]*)\s*\{?\s*$/],
};
DECL.c.push(...DECL.php); DECL.kotlin.push(/^\s*(?:[\w@]+\s+)*fun\s+([A-Za-z_]\w*)/);
const GO_TYPE = /^\s*type\s+([A-Za-z_]\w*)\s+(?:struct|interface)\b/;
const CLASS_RE = /^\s*(?:(?:export|public|private|protected|internal|abstract|final|sealed|static|data|open|partial|pub(?:\([^)]*\))?|default)\s+)*(?:class|struct|interface|enum|trait|object|record|protocol|extension|impl(?:<[^>]*>)?)\s+([A-Za-z_]\w*)/;
function genericScan(text, fam, offset = 0) {
  const L = text.split('\n'), fns = [];
  const push = (name, start, end, cls) => fns.push({ name, short: name, start: start + 1 + offset, end: end + 1 + offset, s0: start, e0: end, cls: !!cls });
  if (['js', 'go', 'rust', 'kotlin', 'swift', 'scala', 'php', 'c', 'sh'].includes(fam)) {
    for (let i = 0; i < L.length; i++) {
      const s = L[i]; if (/^\s*(\/\/|\*|#(?!!)|--)/.test(s)) continue;
      const cm = fam !== 'sh' && (CLASS_RE.exec(s) || (fam === 'go' && GO_TYPE.exec(s)));
      if (cm) { const col = s.indexOf('{') >= 0 ? s.indexOf('{') : 0, e = braceEnd(L, i, col); if (e >= i) push(cm[1], i, e, true); continue; }
      for (const re of DECL[fam] || []) {
        const m = re.exec(s); if (!m || KEYWORDS.has(m[1])) continue;
        if (fam === 'c' && (/;\s*$/.test(s) || /^\s*(return|else|new|throw|case)\b/.test(s) || /=\s*[^=]/.test(s.split('(')[0]))) continue;
        const col = Math.max(0, s.indexOf(m[1])), e = braceEnd(L, i, col);
        if (e >= i) { push(m[1], i, e); break; }
        if ((fam === 'js' || fam === 'kotlin' || fam === 'scala') && /=>|=\s*$|=\s*\S/.test(s)) { let j = i; while (j < L.length - 1 && j < i + 60 && !/;\s*$/.test(L[j]) && L[j + 1].trim() && /^\s/.test(L[j + 1])) j++; push(m[1], i, j); break; } // arrow or expression body without braces
        if (fam === 'scala' || fam === 'kotlin') { if (/=\s*\S/.test(s)) { push(m[1], i, i); break; } } // one-line `def f = ...`
      }
    }
  } else if (fam === 'py') {
    for (let i = 0; i < L.length; i++) {
      const m = /^(\s*)(?:async\s+)?(def|class)\s+([A-Za-z_]\w*)/.exec(L[i]); if (!m) continue;
      const ind = m[1].length; let e = i;
      for (let j = i + 1; j < L.length; j++) { if (!L[j].trim() || /^\s*#/.test(L[j])) continue; if (L[j].match(/^\s*/)[0].length <= ind) break; e = j; }
      push(m[3], i, e, m[2] === 'class');
    }
  } else if (['ruby', 'lua', 'elixir', 'r'].includes(fam)) {
    const RE = { ruby: /^(\s*)(def|class|module)\s+(?:self\.)?([\w:?!=]+)/, lua: /^(\s*)(?:local\s+)?(function)\s+([\w.:]+)/, elixir: /^(\s*)(defp?|defmodule|defmacro)\s+([\w.?!]+)/, r: /^(\s*)([\w.]+)\s*(<-|=)\s*function\s*\(/ }[fam];
    for (let i = 0; i < L.length; i++) {
      const m = RE.exec(L[i]); if (!m) continue;
      if (fam === 'r') { const e = braceEnd(L, i, L[i].indexOf('function')); if (e >= i) push(m[2], i, e); continue; }
      const ind = m[1].length; let e = i;
      if (fam === 'elixir' && /,\s*do:/.test(L[i])) { push(m[3], i, i, false); continue; }
      for (let j = i + 1; j < L.length; j++) if (/^\s*end\b/.test(L[j]) && L[j].match(/^\s*/)[0].length === ind) { e = j; break; }
      if (e === i && fam === 'ruby' && /\bend\s*$/.test(L[i]) === false) { /* endless def or one-liner */ }
      push(m[3].split(/[.:]/).pop(), i, e, ['class', 'module', 'defmodule'].includes(m[2]));
    }
  }
  // names: methods inside classes become "Class › method"; functions inside functions keep the outer name too
  fns.sort((a, b) => a.s0 - b.s0 || b.e0 - a.e0);
  for (const f of fns) { const outer = fns.filter(o => o !== f && o.s0 <= f.s0 && o.e0 >= f.e0 && (o.s0 < f.s0 || o.e0 > f.e0)).sort((a, b) => (a.e0 - a.s0) - (b.e0 - b.s0))[0]; if (outer) f.outer = outer; }
  for (const f of fns) { const chainN = []; for (let o = f.outer; o; o = o.outer) chainN.unshift(o.short); f.name = [...chainN, f.short].join(' › '); }
  for (const f of fns) { f.code = L.slice(f.s0, f.e0 + 1).join('\n'); f.calls = f.cls ? new Set() : callsIn(f.code); } // a class box does not call; its methods do
  // code that runs by itself: everything outside functions and classes that is not an import/comment/blank line
  const inside = new Set(); fns.filter(f => !f.outer).forEach(f => { for (let i = f.s0; i <= f.e0; i++) inside.add(i); });
  const loose = L.map((s, i) => ({ s, i })).filter(({ s, i }) => !inside.has(i) && s.trim() && !/^\s*(\/\/|#|\*|\/\*|--|import\b|from\s+\S+\s+import|package\b|using\b|use\b|require(_relative)?\b|include\b|#include|namespace\b|module\b|export\s*\{|}\s*$|\)\s*$|]\s*$|<\/?\w|<\?php|\?>|(private|public|protected|end)\s*$|(\w+\s+)?"[^"]*"\s*$)/.test(s));
  if (loose.length && fam !== 'style' && !(fam === 'c' && loose.every(x => /^\s*[\w.]+\s*;?\s*$/.test(x.s)))) {
    const code = loose.map(x => x.s).join('\n');
    fns.unshift({ name: '(runs on load)', short: '(runs on load)', start: loose[0].i + 1 + offset, end: loose.at(-1).i + 1 + offset, code, calls: callsIn(code), top: true });
  }
  return fns;
}
function callsIn(code) {
  const s = new Set();
  for (const m of code.matchAll(/(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(/g)) if (!KEYWORDS.has(m[1])) s.add(m[1]); // lookbehind, so f(g(x)) finds both f and g
  for (const m of code.matchAll(/([A-Za-z_$][\w$]*)\s*(?:\.|->|::)\s*([A-Za-z_$][\w$]*)\s*\(/g)) s.add(m[1] + '.' + m[2]);
  for (const m of code.matchAll(/[)\]]\s*(?:\.|->)\s*([A-Za-z_$][\w$]*)\s*\(/g)) s.add(m[1]); // a().b(): chained calls
  return s;
}
const IMPORT_RES = [
  /^\s*import\s+(?:type\s+)?(?:[\w*{}\s,$]+\s+from\s+)?['"]([^'"]+)['"]/, /^\s*export\s+(?:[\w*{}\s,$]+\s+)?from\s+['"]([^'"]+)['"]/, /require(?:_relative)?\s*\(?\s*['"]([^'"]+)['"]/, /import\(\s*['"]([^'"]+)['"]\s*\)/,
  /^\s*from\s+(\.*[\w.]*)\s+import\b/, /^\s*import\s+(?:static\s+)?([\w.]+)(?:\s+as\s+\w+)?\s*;?\s*$/, /^\s*#\s*include\s+"([^"]+)"/, /^\s*use\s+([\w\\:]+)/, /^\s*using\s+([\w.]+)\s*;/,
  /^\s*(?:import\s+)?(?:\w+\s+)?"([\w.\-/]+)"\s*$/, /^\s*import\s+"([\w.\-/]+)"/, /^\s*(?:source|\.)\s+["']?([\w./-]+\.sh)/, /^\s*@import\s+(?:url\()?['"]([^'"]+)['"]/,
  /<script[^>]+src=["']([^"']+)["']/, /<link[^>]+href=["']([^"']+\.css)["']/,
];
const filesNoExt = new Map(); // "src/utils/date" -> file, for suffix matching of import paths
for (const f of codeFiles) { const k = f.replace(/\.[^./]+$/, ''); if (!filesNoExt.has(k)) filesNoExt.set(k, f); const idx = k.replace(/\/(index|__init__|mod)$/, ''); if (idx !== k && !filesNoExt.has(idx)) filesNoExt.set(idx, f); }
const byDir = new Map(); for (const f of codeFiles) { const d = path.posix.dirname(f); if (!byDir.has(d)) byDir.set(d, []); byDir.get(d).push(f); }
function resolveImport(from, spec) {
  if (!spec || /^[a-z]+:\/\//.test(spec)) return [];
  let s = spec.replace(/^['"]|['"]$/g, '');
  if (s.startsWith('./') || s.startsWith('../')) { // relative path: with or without its extension
    const exact = path.posix.normalize(path.posix.join(path.posix.dirname(from), s));
    if (fileSet.has(exact)) return [exact];
    const hit = filesNoExt.get(exact) || filesNoExt.get(exact.replace(/\.[^./]+$/, '')); return hit ? [hit] : [];
  }
  if (/^\.+\w/.test(s)) { const up = s.match(/^\.+/)[0].length; let d = path.posix.dirname(from); for (let i = 1; i < up; i++) d = path.posix.dirname(d); s = path.posix.join(d, s.slice(up).replace(/\./g, '/')); const hit = filesNoExt.get(s); return hit ? [hit] : []; }
  s = s.replace(/^[@~]\//, '').replace(/\\|::/g, '/').replace(/^\//, '');
  const dotted = /^[\w]+(\.[\w]+)+$/.test(s) && !/\.(js|ts|py|go|rb|css|sh|php|h|hpp)$/.test(s) ? s.replace(/\./g, '/') : s;
  for (const cand of [dotted, s]) {
    const noext = cand.replace(/\.(js|jsx|ts|tsx|mjs|cjs|vue|svelte|astro|py|rb|go|php|h|hpp|css|scss|sh)$/, '');
    if (filesNoExt.has(noext)) return [filesNoExt.get(noext)];
    // module paths often start with the project's own name (shop/api/handlers): drop leading parts, keep at least two
    const segs = noext.split('/');
    for (let i = 1; i <= segs.length - 2; i++) { const t2 = segs.slice(i).join('/'); if (filesNoExt.has(t2)) return [filesNoExt.get(t2)]; if (byDir.has(t2)) return byDir.get(t2).slice(0, 6); }
    const suf = [...filesNoExt.keys()].filter(k => k.endsWith('/' + noext)); if (suf.length === 1) return [filesNoExt.get(suf[0])];
    const dirs = [...byDir.keys()].filter(d => d === noext || d.endsWith('/' + noext)); if (dirs.length === 1) return byDir.get(dirs[0]).slice(0, 6); // Go/Java packages are folders
  }
  return [];
}
function importsOf(f, text) { const out = []; for (const l of text.split('\n')) for (const re of IMPORT_RES) { const m = re.exec(l); if (m) { out.push(m[1]); break; } } return out; }

// precise JS/TS through the TypeScript compiler, when available
function tsScan(file, text, lineOffset, label) {
  const sf = ts.createSourceFile(file + '.tsx', text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const fns = [], line = pos => sf.getLineAndCharacterOfPosition(pos).line + 1 + lineOffset;
  const calls = node => { const s = new Set(); const v = n => { if (ts.isCallExpression(n) || ts.isNewExpression(n)) { const e = n.expression; if (e && ts.isIdentifier(e)) s.add(e.text); else if (e && ts.isPropertyAccessExpression(e) && ts.isIdentifier(e.expression)) s.add(e.expression.text + '.' + e.name.text); else if (e && ts.isPropertyAccessExpression(e)) s.add(e.name.text); } ts.forEachChild(n, v); }; v(node); return s; };
  const nameOf = n => { if ((ts.isFunctionDeclaration(n) || ts.isFunctionExpression(n) || ts.isClassDeclaration(n)) && n.name) return n.name.text; if ((ts.isArrowFunction(n) || ts.isFunctionExpression(n)) && n.parent) { if (ts.isVariableDeclaration(n.parent) && ts.isIdentifier(n.parent.name)) return n.parent.name.text; if (ts.isPropertyAssignment(n.parent) && ts.isIdentifier(n.parent.name)) return n.parent.name.text; } if ((ts.isMethodDeclaration(n) || ts.isGetAccessor(n)) && n.name && ts.isIdentifier(n.name)) return n.name.text; return null; };
  const walk = (n, owner) => {
    const isFn = ts.isFunctionDeclaration(n) || ts.isArrowFunction(n) || ts.isFunctionExpression(n) || ts.isMethodDeclaration(n) || ts.isClassDeclaration(n);
    const name = isFn ? nameOf(n) : null;
    if (name && (!owner || ts.isClassDeclaration(n) || n.getText(sf).split('\n').length > 2 || ts.isFunctionDeclaration(n) || ts.isMethodDeclaration(n))) {
      const fn = { name: owner ? owner.name + ' › ' + name : name, short: name, start: line(n.getStart(sf)), end: line(n.end), code: (n.parent && ts.isVariableDeclaration(n.parent) ? n.parent.parent : n).getText(sf), calls: ts.isClassDeclaration(n) ? new Set() : calls(n), cls: ts.isClassDeclaration(n) };
      fns.push(fn); ts.forEachChild(n, c => walk(c, fn)); return;
    }
    ts.forEachChild(n, c => walk(c, owner));
  };
  walk(sf, null);
  const loose = sf.statements.filter(s => !ts.isImportDeclaration(s) && !ts.isFunctionDeclaration(s) && !ts.isClassDeclaration(s) && !ts.isTypeAliasDeclaration(s) && !ts.isInterfaceDeclaration(s) && !(ts.isVariableStatement(s) && s.declarationList.declarations.every(d => d.initializer && (ts.isArrowFunction(d.initializer) || ts.isFunctionExpression(d.initializer)))));
  const looseText = loose.map(s => s.getText(sf)).join('\n');
  if (loose.length && looseText.trim()) { const c = new Set(); loose.forEach(s => calls(s).forEach(x => c.add(x))); fns.unshift({ name: label || '(runs on load)', short: label || '(runs on load)', start: line(loose[0].getStart(sf)), end: line(loose.at(-1).end), code: looseText, calls: c, top: true }); }
  return fns;
}
const scanJs = (file, text, off, label) => { if (ts) { try { return tsScan(file, text, off, label); } catch {} } const r = genericScan(text, 'js', off); if (label) r.filter(f => f.top).forEach(f => { f.name = f.short = label; }); return r; };

const PY = String.raw`
import ast, json, sys
out = {}
for f in sys.argv[1:]:
    try:
        src = open(f, encoding='utf8').read(); t = ast.parse(src)
    except Exception:
        out[f] = None; continue
    lines = src.split('\n'); fns = []
    def calls(node):
        s = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Name): s.add(n.func.id)
                elif isinstance(n.func, ast.Attribute):
                    s.add(n.func.attr)
                    if isinstance(n.func.value, ast.Name): s.add(n.func.value.id + '.' + n.func.attr)
        return sorted(s)
    def visit(node, owner):
        for c in ast.iter_child_nodes(node):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = (owner + ' › ' if owner else '') + c.name
                start = c.decorator_list[0].lineno if getattr(c, 'decorator_list', None) else c.lineno
                fns.append({'name': name, 'short': c.name, 'start': start, 'end': c.end_lineno, 'code': '\n'.join(lines[start-1:c.end_lineno]), 'calls': calls(c), 'cls': isinstance(c, ast.ClassDef)})
                visit(c, name)
    visit(t, None)
    top = [s for s in t.body if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)) and not (isinstance(s, ast.Expr) and isinstance(getattr(s, 'value', None), ast.Constant))]
    if top:
        fns.insert(0, {'name': '(runs on load)', 'short': '(runs on load)', 'start': top[0].lineno, 'end': top[-1].end_lineno, 'code': '\n'.join('\n'.join(lines[s.lineno-1:s.end_lineno]) for s in top), 'calls': sorted(set().union(*[set(calls(s)) for s in top])), 'top': True})
    out[f] = fns
print(json.dumps(out))
`;

const scanned = {};
const pyFiles = codeFiles.filter(f => LANG[extOf(f)] === 'py');
let pyOut = {};
if (PYTHON && pyFiles.length) { for (let i = 0; i < pyFiles.length; i += 200) { try { Object.assign(pyOut, JSON.parse(execFileSync(PYTHON, ['-I', '-c', PY, ...pyFiles.slice(i, i + 200)], { cwd: ROOT, encoding: 'utf8', maxBuffer: 256e6 }))); } catch {} } }
for (const f of codeFiles) {
  const text = nodes.get(f).code, fam = LANG[extOf(f)], res = { fns: [], imports: importsOf(f, text), uses: new Set() };
  try {
    if (fam === 'js') res.fns = scanJs(f, text, 0);
    else if (fam === 'py') res.fns = pyOut[f] ? pyOut[f].map(x => ({ ...x, calls: new Set(x.cls ? [] : x.calls) })) : genericScan(text, 'py');
    else if (fam === 'sfc') {
      // Vue / Svelte / Astro / HTML: frontmatter and <script> blocks are code; capitalised tags show which components it uses
      const fm = /^---\n([\s\S]*?)\n---/.exec(text); let k = 0;
      if (fm) res.fns.push(...scanJs(f, fm[1], 1, '(build-time setup)'));
      for (const m of text.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
        if (/\bsrc=/.test(m[1]) || !m[2].trim() || /type=["']application\/(ld\+)?json/.test(m[1])) continue;
        const off = text.slice(0, m.index + m[0].indexOf('>') + 1).split('\n').length - 1, r = scanJs(f, m[2], off, '(browser script)');
        r.filter(x => x.top).forEach(x => { x.name = x.short = `(script ${++k})`; }); res.fns.push(...r);
        res.imports.push(...importsOf(f, m[2]));
      }
      const tpl = (fm ? text.slice(fm[0].length) : text).replace(/<script\b[\s\S]*?<\/script>/g, '');
      for (const t of tpl.matchAll(/<([A-Z][A-Za-z0-9]*)[\s/>]/g)) res.uses.add(t[1]);
    }
    else if (fam === 'sh') { res.fns = genericScan(text, 'sh'); const names = res.fns.filter(x => !x.top).map(x => x.short); res.fns.forEach(x => names.forEach(nm2 => { if (nm2 !== x.short && new RegExp(`(^|[\\s;&|(])${reEsc(nm2)}(\\s|$|;)`, 'm').test(x.code)) x.calls.add(nm2); })); } // shell calls have no brackets
    else if (fam && fam !== 'style' && fam !== 'plain') res.fns = genericScan(text, fam);
    else if (extOf(f) === 'make') { const L = text.split('\n'); L.forEach((l, i) => { const m = /^([A-Za-z0-9_.-]+)\s*:(?!=)/.exec(l); if (m && m[1] !== '.PHONY') { let e = i; while (e + 1 < L.length && /^\t/.test(L[e + 1])) e++; res.fns.push({ name: 'make ' + m[1], short: m[1], start: i + 1, end: e + 1, code: L.slice(i, e + 1).join('\n'), calls: new Set() }); } }); }
    else if (extOf(f) === 'pkg') { try { const pkg = JSON.parse(text), L = text.split('\n'); for (const [k2, v] of Object.entries(pkg.scripts || {})) { const ln = L.findIndex(l => l.includes(`"${k2}":`)) + 1; res.fns.push({ name: 'npm run ' + k2, short: k2, start: ln, end: ln, code: `"${k2}": "${v}"`, calls: new Set() }); } } catch {} }
  } catch (e) { res.fns = []; res.error = String(e).slice(0, 200); }
  scanned[f] = res;
}

// ---------- 4. boxes and wires ----------
const fnId = (f, name) => f + '#' + name;
const globalByName = new Map(); // function name -> ids across the repo (for approximate cross-file calls)
for (const f of codeFiles) {
  const s = scanned[f], seen = {};
  for (const fn of s.fns) {
    let name = fn.name; if (seen[name]) name += ` (${++seen[name]})`; else seen[name] = 1;
    fn.id = fnId(f, name);
    addNode({ id: fn.id, kind: 'fn', name, short: fn.short, parent: f, start: fn.start, end: Math.max(fn.start, fn.end), code: fn.code, hash: hash(fn.code), top: !!fn.top, cls: !!fn.cls });
    if (!fn.top && !fn.cls && fn.short.length >= 3 && !COMMON.has(fn.short)) { if (!globalByName.has(fn.short)) globalByName.set(fn.short, []); globalByName.get(fn.short).push(fn.id); }
  }
}
const pkgScripts = scanned['package.json'] ? Object.fromEntries(scanned['package.json'].fns.map(x => [x.short, x.id])) : {};
for (const f of codeFiles) {
  const s = scanned[f], local = new Map(); s.fns.forEach(fn => { if (!local.has(fn.short)) local.set(fn.short, fn.id); });
  const imported = new Set(); for (const spec of s.imports) for (const t of resolveImport(f, spec)) if (t !== f) { imported.add(t); addEdge(f, t, /\.(css|scss|sass|less)$/.test(t) ? 'styles' : 'imports'); }
  for (const fn of s.fns) for (const c of fn.calls) {
    const name = c.includes('.') ? c.split('.').pop() : c;
    if (local.has(name) && local.get(name) !== fn.id) { addEdge(fn.id, local.get(name), 'calls'); continue; }
    const g = globalByName.get(name); if (!g) continue;
    const inImported = g.filter(id => imported.has(id.split('#')[0]));
    if (inImported.length === 1) addEdge(fn.id, inImported[0], 'calls');
    else if (g.length === 1 && g[0].split('#')[0] !== f) addEdge(fn.id, g[0], 'calls', true); // only one function in the repo has this name
  }
  if (s.uses.size) for (const tag of s.uses) { const hits = codeFiles.filter(x => path.posix.basename(x).replace(/\.\w+$/, '') === tag && (imported.has(x) || !imported.size)); if (hits.length === 1) addEdge(f, hits[0], 'shows'); }
}
// scripts that start other scripts: file names on lines that really run something
const byBase = new Map(); for (const f of codeFiles) { const b = path.posix.basename(f); byBase.set(b, byBase.has(b) ? null : f); }
const runLines = (f, code) => { const L = code.split('\n'); if (/\.(sh|bash|zsh)$|Makefile$|Dockerfile$/.test(f)) return L.filter(l => !/^\s*(#|echo\b)/.test(l)).join('\n'); return L.filter((_, i) => L.slice(Math.max(0, i - 3), i + 1).some(l => /subprocess|execFileSync|execSync|spawn|os\.system|popen|exec\.Command|Runtime\.getRuntime|Process\.Start|system\(|`[^`]*`/.test(l))).join('\n'); };
for (const f of codeFiles) for (const fn of scanned[f].fns) {
  const text = /"npm run|^"[\w:-]+":/.test(fn.code) && f === 'package.json' ? fn.code : runLines(f, fn.code);
  for (const [b, t] of byBase) if (t && t !== f && b.length > 4 && !/^(index|main|data|config|utils?|types?|constants?)\./.test(b) && text.includes(b)) addEdge(fn.id, t, 'runs');
  for (const m of text.matchAll(/npm run ([\w:-]+)/g)) if (pkgScripts[m[1]]) addEdge(fn.id, pkgScripts[m[1]], 'runs');
}
for (const e of CFG.edges || []) addEdge(e.from, e.to, e.kind || 'uses');

// ---------- 5. explanations and the beginner / story layers ----------
const EXDIR = path.join(OUT, 'explain'); fs.mkdirSync(EXDIR, { recursive: true });
const DEFAULT_JOBS = { boss: { name: 'Boss', what: 'Starts things and gives the orders. Nothing calls it; you do, by running it.' }, worker: { name: 'Worker', what: 'Does one job when the boss asks, then hands back the result.' }, helper: { name: 'Helper', what: 'A small tool that several others use, like a calculator on the desk.' }, ingredients: { name: 'Ingredients', what: 'Not code: the words and data the code reads.' }, decoration: { name: 'Decoration', what: 'Styles: how things look. They change no behaviour.' } };
const explain = { nodes: {}, tours: [], glossary: {}, beginner: { scope: ['*'], jobs: { ...DEFAULT_JOBS }, roles: {}, wires: {}, io: {}, plays: {} }, story: {} };
const explained = new Set();
const exFiles = fs.readdirSync(EXDIR).filter(f => f.endsWith('.json')).sort();
for (const f of exFiles) Object.keys(JSON.parse(fs.readFileSync(path.join(EXDIR, f), 'utf8')).nodes || {}).forEach(id => explained.add(id));
const warnings = [];
for (const f of exFiles) {
  const j = JSON.parse(fs.readFileSync(path.join(EXDIR, f), 'utf8')); let changed = 0;
  for (const [id, e] of Object.entries(j.nodes || {})) { // re-attach an explanation whose box was renamed but whose code did not change
    if (nodes.has(id)) continue;
    const twin = e.hash && [...nodes.values()].find(n => n.hash === e.hash && n.parent === id.split('#')[0] && !explained.has(n.id));
    if (twin) { delete j.nodes[id]; j.nodes[twin.id] = e; explained.add(twin.id); changed++; } else warnings.push(`explain/${f}: no box "${id}" (renamed or deleted?)`);
  }
  if (flag('--stamp')) for (const [id, e] of Object.entries(j.nodes || {})) if (!e.hash && nodes.get(id)?.hash) { e.hash = nodes.get(id).hash; changed++; }
  if (changed && flag('--stamp')) { fs.writeFileSync(path.join(EXDIR, f), JSON.stringify(j, null, 1) + '\n'); console.log(`updated ${changed} in explain/${f}`); }
  Object.assign(explain.nodes, j.nodes || {}); explain.tours.push(...(j.tours || [])); Object.assign(explain.glossary, j.glossary || {});
  if (j.beginner) { for (const k of ['jobs', 'roles', 'wires', 'io', 'plays']) Object.assign(explain.beginner[k], j.beginner[k] || {}); if (j.beginner.scope) explain.beginner.scope = j.beginner.scope; }
  Object.assign(explain.story, j.story || {});
}
for (const t of explain.tours) for (const st of t.steps) if (!nodes.has(st.id)) warnings.push(`tour "${t.title}" points at missing box "${st.id}"`);
for (const n of nodes.values()) { const e = explain.nodes[n.id]; n.status = !e ? (n.kind === 'content' ? 'ok' : 'missing') : (n.hash && e.hash && e.hash !== n.hash) ? 'stale' : 'ok'; if (e) n.ex = e; }

// ---------- 6. theme: copies of fonts and a stylesheet inside the output folder (browsers block files outside it) ----------
const THEME = fs.existsSync(path.join(OUT, 'theme.json')) ? JSON.parse(fs.readFileSync(path.join(OUT, 'theme.json'), 'utf8')) : {};
fs.mkdirSync(path.join(OUT, 'assets/fonts'), { recursive: true });
const faces = (THEME.fontFiles || []).map(ff => { const src = path.resolve(ROOT, ff.path); if (!fs.existsSync(src)) { warnings.push(`theme.json: font file not found: ${ff.path}`); return ''; } const dst = path.basename(src); fs.copyFileSync(src, path.join(OUT, 'assets/fonts', dst)); return `@font-face{font-family:'${ff.family}';font-weight:${ff.weight || '100 900'};font-style:${ff.style || 'normal'};font-display:swap;src:url('fonts/${dst}')}`; });
const accent = THEME.accent || '#3B82F6';
const tok = (o, k, d) => (o && o[k]) || d;
const L = THEME.light || {}, D = THEME.dark || {};
const fontH = THEME.fonts?.head || 'system-ui, -apple-system, Segoe UI, sans-serif', fontB = THEME.fonts?.body || 'system-ui, -apple-system, Segoe UI, sans-serif', fontM = THEME.fonts?.mono || 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';
const lum = hex => { const m = /^#?([0-9a-f]{6})$/i.exec(hex || ''); if (!m) return .5; const [r, g, b] = [0, 2, 4].map(i => { const v = parseInt(m[1].slice(i, i + 2), 16) / 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }); return .2126 * r + .7152 * g + .0722 * b; };
const onAccent = THEME.onAccent || (lum(accent) > .35 ? '#0F0F0F' : '#FFFFFF');
const vars = (o, dflt) => Object.entries({ ...dflt, ...o }).map(([k, v]) => `--${k}:${v}`).join(';');
const LIGHT = { bg: '#FFFFFF', s1: '#F8F9FA', s2: '#F1F3F5', s3: '#E5E7EB', border: '#E5E7EB', text: '#111111', copy: '#374151', muted: '#6B7280', dim: '#9CA3AF' };
const DARK = { bg: '#0F0F10', s1: '#17181A', s2: '#1F2023', s3: '#2E3034', border: '#2E3034', text: '#F5F5F5', copy: '#D4D4D4', muted: '#A3A3A3', dim: '#737373' };
const map = o => Object.fromEntries(Object.entries(o).filter(([k]) => ['bg', 's1', 's2', 's3', 'border', 'text', 'copy', 'muted', 'dim'].includes(k)));
fs.writeFileSync(path.join(OUT, 'assets/theme.css'), `/* written by scan.mjs from theme.json */\n${faces.join('\n')}
:root{${vars(map(L), LIGHT)};--g:${accent};--gt:${tok(L, 'accentText', `color-mix(in srgb, ${accent} 62%, #000)`)};--gbg:color-mix(in srgb, ${accent} 9%, var(--bg));--gborder:color-mix(in srgb, ${accent} 38%, var(--bg));--on-g:${onAccent};--blog:#F59E0B;--blog-bg:#FFFBEB;--blog-border:#FDE68A;--font-h:${fontH};--font-b:${fontB};--font-m:${fontM};color-scheme:light}
:root[data-theme=dark]{${vars(map(D), DARK)};--gt:${tok(D, 'accentText', accent)};--blog-bg:#1F1808;--blog-border:#5C4508;color-scheme:dark}\n`);

// ---------- 7. coverage check and output ----------
const notCovered = codeFiles.filter(f => !nodes.has(f));
const orphans = [...nodes.values()].filter(n => n.kind !== 'area' && !nodes.has(n.parent));
const dedup = [...new Map(edges.filter(e => nodes.has(e.from) && nodes.has(e.to)).map(e => [e.from + '>' + e.to + '>' + e.kind, e])).values()];
const counts = { areas: areaList.length, groups: [...nodes.values()].filter(n => n.kind === 'group').length, files: codeFiles.length, functions: [...nodes.values()].filter(n => n.kind === 'fn').length, edges: dedup.length, approx: dedup.filter(e => e.approx).length,
  missing: [...nodes.values()].filter(n => n.status === 'missing').length, stale: [...nodes.values()].filter(n => n.status === 'stale').length };
let at = ''; try { at = execFileSync('git', ['log', '-1', '--format=%h %cs'], { cwd: ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch { at = new Date().toISOString().slice(0, 10); }
// remember which reader was used: switching between precise and plain-text reading changes the fingerprints
const STATE = path.join(OUT, '.scanstate.json'), parsers = { typescript: !!ts, python: !!PYTHON };
try { const prev = JSON.parse(fs.readFileSync(STATE, 'utf8')); if (JSON.stringify(prev.parsers) !== JSON.stringify(parsers)) warnings.unshift(`parsers changed since the last scan (${JSON.stringify(prev.parsers)} -> ${JSON.stringify(parsers)}): some boxes may show "code changed" only because they are read differently. Run with the same setup (or --generic both times) to compare.`); } catch {}
fs.writeFileSync(STATE, JSON.stringify({ parsers, at: new Date().toISOString() }));
const meta = { title: CFG.title || path.basename(ROOT), id: hash(ROOT), at, parsers: { typescript: !!ts, python: !!PYTHON }, world: { town: 'Town', neighbourhood: 'neighbourhood', building: 'building', person: 'person', ...(CFG.world || {}) } };
const areaMeta = Object.fromEntries(areaList.map(a => [a.id, { color: a.color || '#94A3B8', icon: a.icon || 'box', place: a.place || a.name }]));
fs.writeFileSync(path.join(OUT, 'data.js'), 'window.MAP = ' + JSON.stringify({ meta, counts, areas: areaMeta, lanes: CFG.lanes || null, nodes: [...nodes.values()], edges: dedup, tours: explain.tours, glossary: explain.glossary, beginner: explain.beginner, story: explain.story, notCovered, skipped }).replace(/<\/script/gi, '<\\/script') + ';\n');
// the same map as a knowledge graph, for other tools: graph.json (nodes + edges) and graph.graphml (Gephi, yEd, Cytoscape)
{
  const areaIdOf = n => { let p = n; while (p && p.kind !== 'area') p = nodes.get(p.parent); return p ? p.id.slice(5) : null; };
  const kn = [...nodes.values()].map(n => ({ id: n.id, label: n.name, kind: n.kind, parent: n.parent || null, area: areaIdOf(n), path: n.path || (n.kind === 'fn' ? n.parent : null), lines: n.kind === 'fn' ? [n.start, n.end] : undefined, what: n.ex?.what || n.what || undefined }));
  const ke = [...dedup.map(e => ({ source: e.from, target: e.to, kind: e.kind, approx: !!e.approx })), ...[...nodes.values()].filter(n => n.parent).map(n => ({ source: n.parent, target: n.id, kind: 'contains', approx: false }))];
  fs.writeFileSync(path.join(OUT, 'graph.json'), JSON.stringify({ title: CFG.title || path.basename(ROOT), scanned: at, nodes: kn, edges: ke }, null, 1));
  const x = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  fs.writeFileSync(path.join(OUT, 'graph.graphml'), `<?xml version="1.0" encoding="UTF-8"?>\n<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n<key id="label" for="node" attr.name="label" attr.type="string"/><key id="kind" for="node" attr.name="kind" attr.type="string"/><key id="area" for="node" attr.name="area" attr.type="string"/><key id="what" for="node" attr.name="what" attr.type="string"/><key id="ekind" for="edge" attr.name="kind" attr.type="string"/><key id="approx" for="edge" attr.name="approx" attr.type="boolean"/>\n<graph edgedefault="directed">\n${kn.map(n => `<node id="${x(n.id)}"><data key="label">${x(n.label)}</data><data key="kind">${n.kind}</data><data key="area">${x(n.area)}</data>${n.what ? `<data key="what">${x(n.what)}</data>` : ''}</node>`).join('\n')}\n${ke.map((e, i) => `<edge id="e${i}" source="${x(e.source)}" target="${x(e.target)}"><data key="ekind">${e.kind}</data><data key="approx">${e.approx}</data></edge>`).join('\n')}\n</graph>\n</graphml>\n`);
}
console.log(`code atlas: ${counts.files} files, ${counts.functions} functions, ${counts.edges} wires (${counts.approx} guessed by name); ${counts.missing} need an explanation, ${counts.stale} changed since explained (${at}); parsers: ${ts ? 'TypeScript' : 'plain-text JS'}, ${PYTHON ? 'Python ast' : 'plain-text Python'}`);
if (skipped.length) console.log(`skipped ${skipped.length}: ${skipped.slice(0, 5).join(', ')}${skipped.length > 5 ? ' ...' : ''}`);
warnings.slice(0, 20).forEach(w => console.error('warning: ' + w));
if (notCovered.length || orphans.length) { console.error('COVERAGE PROBLEM'); if (notCovered.length) console.error(' not on the map:', notCovered.join(', ')); if (orphans.length) console.error(' no parent:', orphans.map(n => n.id).join(', ')); process.exitCode = 1; }
