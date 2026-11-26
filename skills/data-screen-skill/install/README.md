# 安装到各类 Agent / Harness

本 skill 不依赖任何专有 API，核心只有 Markdown + 原生 JS。
按你的工具选择一种方式即可。

| Harness | 方式 | 说明 |
|---|---|---|
| Claude Code | `~/.claude/skills/` | 原生 skill，自动发现 |
| Claude 网页版 | 粘贴 bundle | 无文件系统 |
| Codex / Codex CLI | `~/.codex/skills/` 或 `AGENTS.md` | 读文件 + shell |
| Cursor | `.cursor/rules/*.mdc` | 规则文件 |
| Cline / Roo Code | `.clinerules` / 自定义指令 | 规则文件 |
| Windsurf | `.windsurf/rules` | 规则文件 |
| GitHub Copilot | `.github/copilot-instructions.md` | 指令文件 |
| 自研 Agent | 读 `SKILL.md` | 支持读文件即可 |

## 通用安装

```bash
git clone https://github.com/jxy162/data-screen-skill.git
cd data-screen-skill
```

然后按 `install/<harness>.md` 操作。

## 通用降级

- 没有 shell：复制 `starter/` 到目标目录，手动改文件。
- 没有浏览器：用 `node scripts/qa.mjs` 静态检查。
- 没有网络：只用 `starter/` + `knowledge/`，不跑 `fetch-templates.mjs`。
- 没有文件系统：`node scripts/bundle.mjs --preset chat`，把 bundle 贴进对话。
