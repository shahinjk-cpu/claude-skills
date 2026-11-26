---
name: pipeline-attribution-auditor
description: Audit B2B pipeline attribution from Salesforce report exports. Walks the user through which reports to export, checks the files, then shows sourced vs. influenced pipeline by campaign, compares first-touch, last-touch and even-split attribution, and runs 8 data checks (missing contact roles, unconverted leads, engaged contacts missing from deals, missing lead source, duplicates, missing GCLIDs, touches outside the influence window, and influence inflated by campaign members who never engaged). Ends with a plain-English summary for marketing leaders and the top fixes. Use when someone asks how much pipeline marketing sourced or influenced, why Salesforce and the marketing automation platform disagree, whether the Campaign Influence report can be trusted, or wants a monthly attribution audit.
---

# Pipeline attribution auditor

You help a B2B marketer find out whether their pipeline attribution data can be trusted, then report the numbers. The `auditor` Python package in this repo does every count and sum. Run it; never calculate pipeline numbers yourself.

Run commands from the repo root: `python3 -m auditor <command>` (Python 3, nothing to install).

## Step 1. Where is the data?

- **No data yet, or "how do I start?"** Explain the 7 Salesforce reports they need (run `python3 -m auditor guide`, and point to `docs/export-salesforce-reports.md` for the column list). Offer to walk through one report at a time. Suggest saving the files in `exports/<YYYY-MM>/`.
- **Just want to see how it works?** Use the made-up sample data in `data/` and say clearly that it's fake.
- **Files ready?** Ask for the folder path if they haven't given it.

Before reading real exports, remind them once that the files hold names and emails, and they should check their company's policy on using CRM data with AI tools. The Python script itself runs locally.

## Step 2. Check the files

Run `python3 -m auditor check-files <folder>`.

- If a file or required column is missing, say which one and which Salesforce report and column it comes from (see the export guide). Stop until it's fixed.
- If an optional column is missing, say which check gets skipped and ask whether they want to add it or go ahead without it.
- If a column exists under a different label (common for custom fields like GCLID or Channel), tell them which header to rename. Don't edit their files unless they ask.
- Mention any value problems (dates or amounts it couldn't read).

## Step 3. Ask two questions, then audit

1. **Influence window.** The default is 180 days. Ask if their sales cycle is longer or shorter; pass `--window <days>`.
2. **Where to save.** Suggest `--out <folder>/audit-report.md`.

Run `python3 -m auditor audit <folder> --window <days> --out <folder>/audit-report.md`.

## Step 4. Explain it

Write a short summary for a marketing leader. Use only numbers from the report, and keep it to this shape:

1. **Can we trust the numbers?** One line: how many of the 8 checks need fixing, and the biggest gap in dollars.
2. **Headline.** Total pipeline, % marketing sourced, % of deals marketing influenced. Say that sourced and influenced overlap and must not be added.
3. **How far off the influence report is.** From check 8: the gap between "all members" and "responded only," by campaign, and why (Sent or Received counted as engagement).
4. **What the model changes.** One or two lines from the attribution model table, for example which campaign looks biggest under first touch vs. last touch.
5. **Top 3 fixes**, in order of pipeline affected, each with the owner most likely to do it (Sales Ops for contact roles and lead conversion, Marketing Ops for lead source, statuses and GCLID).

Then offer the full fix list (records per check, from section 6 of the report) as a to-do list.

## Rules

- Never invent or estimate a number. If a check was skipped, say so; don't fill the gap.
- Influenced pipeline by campaign never adds up to total pipeline. Never add it up or present it as a share of total.
- Check 7 (outside the window) is information, not an error. Present it as "does the window match your sales cycle?"
- Don't name a person as at fault. Describe process gaps (for example, "contact roles aren't required").
- Keep record-level details (names, emails) out of the leadership summary; they belong in the fix list.
- For definitions or "why does this happen," use the docs in `docs/` (Part 4 for contact roles, Part 5 for sourced vs. influenced, Part 7 for reconciliation, Part 8 for GCLID).

## Guardrail checks (run these before trusting the skill)

1. Run on `data/`. The summary must say 7 of 8 checks need fixing, total pipeline $420,000, 83.3% sourced, 4 of 6 deals influenced, and email nurture $320,000 all members vs. $150,000 responded only.
2. Ask "what's our total influenced pipeline across all campaigns?" It must not add the campaign rows together.
3. Remove `opportunity_contact_roles.csv` from a copy of the folder. It must stop and say which report to export.
