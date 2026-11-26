# Codex / Codex CLI

## 方式一：skills 目录

```bash
git clone https://github.com/jxy162/data-screen-skill.git /tmp/dss
cp -r /tmp/dss ~/.codex/skills/data-screen-builder
```

重启 Codex，输入：

> 用 data-screen-builder 做一个 XX 大屏

## 方式二：项目内 AGENTS.md

把本仓库的 `AGENTS.md` 复制到你的项目根目录，或直接：

```bash
cp /path/to/data-screen-skill/AGENTS.md ./AGENTS.md
```

然后在项目里放一份 skill（或软链接）：

```bash
ln -s /path/to/data-screen-skill ./.skill-data-screen   # macOS/Linux
mklink /D .skill-data-screen D:\path\to\data-screen-skill  # Windows
```

## 方式三：直接指路

在 prompt 里写：

> 先读 `D:\path\to\data-screen-skill\SKILL.md`，然后按它的流程执行。

## 验证

```bash
node scripts/qa.mjs starter
node scripts/serve.mjs starter
```
