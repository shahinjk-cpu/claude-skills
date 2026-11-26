#!/usr/bin/env node
// Optional: rescan the code atlas after every commit (local git hook, never committed, never blocks a commit).
//   node install-hook.mjs [--root <repo>] [--out <dir>]      install
//   node install-hook.mjs --remove                           remove
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const root = execFileSync('git', ['rev-parse', '--show-toplevel'], { cwd: path.resolve(arg('--root', process.cwd())), encoding: 'utf8' }).trim();
const out = path.resolve(arg('--out', path.join(root, 'code-atlas')));
const hooksDir = (() => { try { const p = execFileSync('git', ['config', 'core.hooksPath'], { cwd: root, encoding: 'utf8' }).trim(); if (p) return path.resolve(root, p); } catch {} return path.join(root, '.git/hooks'); })();
const hook = path.join(hooksDir, 'post-commit'), START = '# >>> code-atlas', END = '# <<< code-atlas';
const q = s => `'${s.replace(/'/g, `'\\''`)}'`; // safe in sh, even with apostrophes in the path
const block = `${START}\n${q(process.execPath)} ${q(path.join(HERE, 'scan.mjs'))} --root ${q(root)} --out ${q(out)} > ${q(path.join(out, 'scan.log'))} 2>&1 || true\nhead -n 2 ${q(path.join(out, 'scan.log'))} 2>/dev/null || true\n${END}\n`;
let cur = fs.existsSync(hook) ? fs.readFileSync(hook, 'utf8') : '';
cur = cur.replace(new RegExp(`${START}[\\s\\S]*?${END}\\n?`), '');
if (process.argv.includes('--remove')) { fs.writeFileSync(hook, cur); console.log('removed the code-atlas rescan from', hook); process.exit(0); }
if (!cur.trim()) cur = '#!/bin/sh\n';
fs.mkdirSync(hooksDir, { recursive: true });
fs.writeFileSync(hook, cur.replace(/\n?$/, '\n') + block); fs.chmodSync(hook, 0o755);
console.log('installed: after each commit the code atlas rescans (output in', path.join(out, 'scan.log') + ')');
