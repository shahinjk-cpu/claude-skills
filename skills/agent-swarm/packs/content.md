---
name: content
description: Content team: video scripts, social posts, blog and SEO, newsletters and content calendars. Drafts only.
triggers: [youtube, video, script, post, social, tiktok, instagram, blog, seo, newsletter, caption, thumbnail, podcast]
extends: general
---

## Roles

### scriptwriter
- type: writer
- model: standard
- verifier: editor
- rules:
  - Hook in the first 5 seconds, one idea per section, a clear ending. Mark on-screen text and b-roll cues.
  - Give the read length, at about 150 words a minute.

### social-drafter
- type: writer
- model: cheap
- verifier: editor
- rules:
  - One file per post, named `YYYY-MM-DD-<platform>-<slug>.md`, with the platform's length limit, alt text and asset paths.
  - Write for each network: its format and its tone.

### seo-writer
- type: writer
- model: standard
- verifier: editor
- rules:
  - Search intent first; then title, meta description, headings and internal links. No keyword stuffing.
  - Cite a source for every claim.

### trend-researcher
- type: researcher
- model: cheap
- rules:
  - Report what is working now in the niche (formats, topics, hooks), with links and dates.

### content-planner
- type: scout
- model: standard
- rules:
  - Calendars: date, platform, topic, format, asset needed, owner. Balance the mix across the week.

### editor
- type: verifier
- model: standard
- rules:
  - Read-only. Check voice, accuracy, clarity, platform rules and copyright (quotes under 15 words, credited).

## Pairings
- Videos: trend-researcher, then scriptwriter, checked by editor.
- Posts: social-drafter, checked by editor.
- Blog and SEO: seo-writer, checked by editor.
- Calendars: content-planner.

## Guardrails
- Drafts only. Never post, upload, schedule or send; a person approves each batch.
