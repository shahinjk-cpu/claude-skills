# Claude Code / Claude Agent Skills

## 用户级（所有项目可用）

```bash
git clone https://github.com/jxy162/data-screen-skill.git /tmp/dss
cp -r /tmp/dss ~/.claude/skills/data-screen-builder
```

重启 Claude Code，在对话里说：

> 用 data-screen-builder 做一个 XX 大屏

Claude 会自动读取 `~/.claude/skills/data-screen-builder/SKILL.md`。

## 项目级

```bash
mkdir -p .claude/skills
cp -r /path/to/data-screen-skill .claude/skills/data-screen-builder
```

## 验证

```bash
ls ~/.claude/skills/data-screen-builder/SKILL.md
```

## 注意

- 目录名建议用 `data-screen-builder`（与 frontmatter 的 `name` 一致）。
- 如果 skill 没有被发现，检查 `SKILL.md` 是否在目录根部、frontmatter 是否完整。
- 需要 Node 18+ 才能跑脚本；不跑脚本也能只用知识库。
