---
name: enhansome-claude-code-skills-zh
description: Skill for enhansome-claude-code-skills-zh
---

# enhansome-claude-code-skills-zh

# Awesome 🛠️ Claude Code Skills 中文精选集 with stars

> 🚀 最实用的 Claude Code Skills / Agents / Plugins 合集 | 精选 452+ | 按场景分类 | 复制即装 | 持续更新

[![Stars](https://img.shields.io/github/stars/laolaoshiren/claude-code-skills-zh?style=social)](https://github.com/laolaoshiren/claude-code-skills-zh)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-452%2B-green.svg)](#original-skills)
[![Updated](https://img.shields.io/badge/updated-2026--11--25-brightgreen.svg)](https://github.com/laolaoshiren/claude-code-skills-zh/commits/main)
[![Website](https://img.shields.io/badge/website-claude--skills.bt199.com-6c5ce7.svg)](https://claude-skills.bt199.com)

**中文开发者最好的 Claude Code Skills 资源站。** 不只是列表，更包含可直接安装的原创技能包。

## 🀄 为什么是「中文」精选

* 📖 **说明用中文**：每条都写清解决什么场景、怎么安装、有什么限制和风险，不用先啃一遍英文 README。
* 🇨🇳 **中文场景单独成类**：公众号、小红书、飞书、企业微信、B 站、抖音等国内平台技能有独立分类，不用在英文列表里大海捞针。
* 🎁 **原创中文技能**：本仓库自研、针对中文语境优化的 Skill，一条命令装完，也可按需单装。
* ✅ **收录看中文价值**：每个条目都要说明「对中文用户有什么用」，纯英文且说不清价值的项目不放在热门位。

## ⚡ 一条命令安装全部原创技能

在 Claude Code 里输入（需要 2.1+，最推荐）：

```bash
/plugin marketplace add laolaoshiren/claude-code-skills-zh
/plugin install zh-skills@claude-code-skills-zh
```

装完后，当你让它汉化英文 Skill、审查代码、写 README、跑 API 测试、做重构或性能分析时，对应技能会自动触发。

不走插件市场，也可按系统直接克隆安装（按需单装与 Codex / Cursor / Gemini CLI 路径见 [⚡ 30 秒上手建议](#quick-start)）：

```bash
# macOS / Linux
git clone https://github.com/laolaoshiren/claude-code-skills-zh.git && mkdir -p ~/.claude/skills && cp -r claude-code-skills-zh/skills/* ~/.claude/skills/
```

```powershell
# Windows PowerShell 5.1+（避免使用 && 或裸 cp -r）
git clone https://github.com/laolaoshiren/claude-code-skills-zh.git
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse -Force ".\claude-code-skills-zh\skills\*" "$HOME\.claude\skills\"
```

<!-- fact-summary -->

## 📌 一句话事实

**claude-code-skills-zh（Claude Code Skills 中文精选集）** 是面向中文开发者的 Claude Code Skills / Agents / Plugins 精选仓库：**452+** 个精选技能按场景分类（平台运营、开发效率、内容创作、学术科研、AI Agen
