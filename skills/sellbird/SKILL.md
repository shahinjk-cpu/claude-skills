---
name: sellbird
description: >
  Autonomous AI sales outreach and prospecting agent. Scrape leads, verify corporate emails, generate hyper-personalized cold outreach, and track reply sentiment using local LLM models.
metadata:
  version: "1.0.0"
  category: ai_ml
  triggers: sellbird, ai sales agent, cold email, b2b outreach, lead scraping, sales prospecting
---

# Sellbird — Autonomous B2B Sales & Outreach Agent

Automates the outbound sales pipeline: lead research, company enrichment, personalized cold email drafting, and reply sentiment analysis using Claude Code or local agents.

## Workflow Pipeline
1. **Prospecting & Enrichment**: Pull target company data, tech stack, and LinkedIn profiles.
2. **Email Verification**: Validate MX records and SMTP deliverability.
3. **Personalized Copywriting**: Draft 3-sentence high-converting emails referencing company achievements.
4. **Follow-Up Cadence**: Schedule multi-touch drip campaigns with automatic reply detection.

## CLI Execution
```bash
npx sellbird prospect --industry "SaaS" --role "CTO" --location "Remote"
npx sellbird draft --template consultative --tone casual
```
