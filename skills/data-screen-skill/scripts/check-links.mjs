#!/usr/bin/env node
/**
 * 检查 Markdown 中的本地链接/图片是否存在。
 * 用法：node scripts/check-links.mjs [dir]
 */
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] || ".");
const files = [];
( function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    if (["node_modules", ".git", "vendor", "dist"].includes(e.name)) continue;
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else if (p.endsWith(".md")) files.push(p);
  }
})(root);

let bad = 0;
for (const f of files) {
  const text = fs.readFileSync(f, "utf8");
  const re = /!?\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
  for (const m of text.matchAll(re)) {
    const href = m[1];
    if (/^(https?:|mailto:|#|data:)/.test(href)) continue;
    const target = path.resolve(path.dirname(f), decodeURIComponent(href.split("#")[0]));
    if (!fs.existsSync(target)) {
      bad++;
      console.log(`MISSING  ${path.relative(root, f)}  ->  ${href}`);
    }
  }
}
console.log(`\n${bad === 0 ? "✔" : "✘"} ${files.length} markdown files, ${bad} broken link(s)`);
process.exit(bad ? 1 : 0);
