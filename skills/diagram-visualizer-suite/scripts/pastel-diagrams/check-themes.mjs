#!/usr/bin/env node
// Checks every text/background pair of every theme against WCAG AA (4.5:1 text, 3:1 icons).
//   node scripts/check-themes.mjs [theme.json ...]     (default: all built-in themes)
import { listThemes, resolveTheme, loadTheme, contrastPairs } from "./lib/theme.mjs";

const files = process.argv.length > 2 ? process.argv.slice(2) : listThemes().map((n) => resolveTheme(n));
let bad = 0;
for (const f of files) {
  const t = loadTheme(resolveTheme(f));
  const pairs = contrastPairs(t);
  const fails = pairs.filter((p) => p.ratio < p.min);
  bad += fails.length;
  const low = pairs.reduce((a, b) => (b.ratio < a.ratio ? b : a));
  console.log(`${fails.length ? "FAIL" : "ok  "} ${t.name.padEnd(20)} lowest ${low.ratio.toFixed(2)}:1 (${low.what})`);
  for (const p of fails) console.log(`       ${p.what}: ${p.fg} on ${p.bg} = ${p.ratio.toFixed(2)}:1, needs ${p.min}:1`);
}
process.exit(bad ? 1 : 0);
