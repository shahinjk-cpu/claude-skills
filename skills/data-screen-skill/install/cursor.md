# Cursor / Cline / Roo / Windsurf / Copilot

这些工具没有统一的 skill 目录，用「规则文件」即可。

## Cursor

创建 `.cursor/rules/data-screen.mdc`：

```markdown
---
description: 数据大屏构建规范
globs: ["**/*.html", "**/*.css", "**/*.js", "screens/**"]
alwaysApply: false
---

请先阅读 @SKILL.md（或把 SKILL.md 全文贴在这里）。
关键规则：
- 图表只读 DashboardData，不直接 fetch。
- 演示数据必须标「示例数据」。
- 1920×1080 等比缩放，正文 ≥14px。
- 交付前跑 node scripts/qa.mjs。
```

## Cline

创建 `.clinerules/data-screen.md`，内容同上（去掉 frontmatter）。

## Roo Code

在 `.roo/rules/` 下放 `data-screen.md`，内容同上。

## Windsurf

在 `.windsurf/rules/data-screen.md` 放规则；或把 `SKILL.md` 加入 `@` 引用。

## GitHub Copilot

创建 `.github/copilot-instructions.md`：

```markdown
构建数据大屏时，遵循 data-screen-skill 的 SKILL.md：
1) 先从对话提炼 brief；2) 选 A1–A6 布局；3) 用统一数据契约；
4) 1920×1080 等比缩放；5) 交付前跑 qa.mjs。
```

## 通用建议

- 规则文件控制在 200 行内，细节让 Agent 去读 `knowledge/`。
- 一定要保留「先提炼 brief、再写代码」和「数据契约」两条硬规则。
