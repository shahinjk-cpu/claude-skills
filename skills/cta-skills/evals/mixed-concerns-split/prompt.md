---
tags: [commit]
max_turns: 6
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

My staged diff has a bug fix in auth.py and also a README rewrite, and I want it all in one commit. Use the build plugin's commit skill. State how many commits you make and in which order, which git subcommand you never use to fold it into my last commit, and which flag you never pass if a hook blocks. Give the two commit subjects. You cannot run commands or edit files here, so answer in prose. Do not ask me questions first.
