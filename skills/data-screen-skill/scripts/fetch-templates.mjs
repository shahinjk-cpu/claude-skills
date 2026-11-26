#!/usr/bin/env node
/**
 * 拉取上游模板仓库到 vendor/（不纳入本仓库版本管理）。
 * 用法：node scripts/fetch-templates.mjs [--ref main]
 * 需要本机安装 git。
 */
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const dest = path.join(repo, "vendor", "dashuju-templates");
const upstream = "https://gitee.com/lvyeyou/DaShuJuZhiDaPingZhanShi.git";

function run(args, cwd) {
  return execFileSync("git", args, { cwd, stdio: "inherit" });
}

fs.mkdirSync(path.join(repo, "vendor"), { recursive: true });

if (fs.existsSync(path.join(dest, ".git"))) {
  console.log("→ 更新已有仓库：" + dest);
  run(["fetch", "--depth", "1", "origin"], dest);
  run(["reset", "--hard", "origin/HEAD"], dest);
} else {
  console.log("→ 克隆上游模板：" + upstream);
  run(["clone", "--depth", "1", upstream, dest], repo);
}

const cats = fs.readdirSync(dest, { withFileTypes: true }).filter((e) => e.isDirectory() && e.name !== ".git");
let screens = 0;
for (const c of cats) {
  for (const s of fs.readdirSync(path.join(dest, c.name), { withFileTypes: true })) {
    if (!s.isDirectory()) continue;
    const dir = path.join(dest, c.name, s.name);
    if (fs.readdirSync(dir).some((f) => f.endsWith(".html"))) screens++;
  }
}
console.log(`✔ 完成：${cats.length} 个行业 · ${screens} 套模板`);
console.log(`  路径：${path.relative(repo, dest)}（已在 .gitignore 中忽略）`);
console.log("  下一步：node scripts/build-catalog.mjs");
