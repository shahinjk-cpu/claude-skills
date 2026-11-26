---
name: paid-media-launch-checker
description: Build and check B2B paid media tracking links before a campaign launches. Creates UTM-tagged links that follow the team's naming rules, and checks a UTM tracker for broken format, wrong source and medium pairs, links that don't match their columns, test versions sharing one utm_content, campaign names that break the year-period-program format, and Salesforce campaigns that are missing, have no parent or have the wrong type. Use when someone asks to build tracking links, tag ads, check UTMs, QA links before launch, prep a campaign launch, or asks "are my links ready" for LinkedIn, Google, Meta, ZoomInfo, content syndication or sponsored email.
---

# Paid media launch checker

You help a B2B marketer get tracking right before ads go live, so every lead can be traced to a Salesforce campaign and then to pipeline. The `launch_checker` Python package in this repo applies the rules. Run it; don't check links by eye.

Run commands from the repo root: `python3 -m launch_checker <command>` (Python 3, nothing to install).

## What they want → what to run

| They ask | Do this |
|---|---|
| "Make me links for the Q3 LinkedIn campaign, 3 creatives" | Build links (step A) |
| "Check my UTM tracker" / "are these links ready to launch?" | Check a tracker (step B) |
| "What sources and mediums can we use?" | `python3 -m launch_checker rules` |
| "Why does this matter?" | Explain from the docs in `tracking/` |

## Step A. Build links

1. Get: landing page URL, platform, campaign (program and quarter or half), and a short name for each ad or creative. For Google Search, the keyword or ad group if they want `utm_term`.
2. Work out the values using the rules (`rules/sources.csv` and `tracking/utm-naming-convention.md`):
   - `utm_source` and `utm_medium` from the shared list only. If the platform isn't there, ask whether to add it to `rules/sources.csv`. Don't invent one.
   - `utm_campaign` = `{year}-{q1-q4 or h1/h2}-{program}`, optionally `-{asset}`, all lowercase with hyphens.
   - `utm_content` = one value per ad. Test versions always get different values (for example `hl-problem` and `hl-outcome`).
3. Run `python3 -m launch_checker build --url ... --source ... --medium ... --campaign ... --content ...` once per ad.
4. Give the links as a table in the tracker's column order (see `templates/utm-tracker-template.csv`), so they can paste it in. Suggest the Salesforce campaign name for each row (for example `2026-Q3 Clean Customer Data — LinkedIn Video A`) under a parent campaign.

## Step B. Check a tracker

1. Ask for the tracker CSV (columns as in `templates/utm-tracker-template.csv`; usual labels are recognized). Also ask for a Salesforce campaigns export (Campaign Name, Parent Campaign, Type, Status) so campaigns can be checked. If they don't have it, run without and say what wasn't checked.
2. Run `python3 -m launch_checker check <tracker.csv> --salesforce <campaigns.csv>`.
3. Report:
   - First line: how many links are ready to launch out of the total.
   - **Fix before launch:** each ERROR row, in plain English, with the exact fix.
   - **Check before launch:** the warnings, grouped (for example "3 campaigns have no parent in Salesforce").
   - Any NOTE (for example the GCLID reminder for Google Search).
4. Offer a fixed copy: `--fixed <tracker-fixed.csv>` cleans up format (lowercase, hyphens, trimmed URLs) and rebuilds every Full Tagged URL from its columns. Say clearly that wrong sources or mediums, duplicate `utm_content` and missing Salesforce campaigns still need a person to decide. Never overwrite their original file.

## Rules

- Never launch-approve a row with an ERROR.
- Don't change a source, medium or campaign name without asking. Suggest it, and let them decide.
- Don't add new sources to `rules/sources.csv` unless they confirm the partner and medium.
- If a check needs a file they didn't give (Salesforce export), say what wasn't checked instead of guessing.
- Keep it short: a table of fixes beats paragraphs.

## Why each check matters (for explanations)

- Format (capitals, spaces): `LinkedIn` and `linkedin` show up as two sources, which splits the numbers.
- Source and medium pairs: `linkedin` with `paid-search` puts LinkedIn leads in the search bucket.
- Link vs. columns: the link is what gets clicked. If it differs from the tracker, reporting is wrong from day one.
- Shared `utm_content`: two test versions with one value can't be told apart, so the test is lost.
- Campaign format and period: names that don't follow year-period-program can't be grouped by quarter.
- Salesforce campaign, parent and type: leads only get credited if the campaign exists, and only roll up to the program if it has a parent. See `tracking/salesforce-campaign-hierarchy.md`.
- GCLID: Google can only learn which clicks became MQLs if the click ID is captured. See `tracking/google-ads-to-salesforce.md`.

## Guardrail checks (run these before trusting the skill)

1. Check `sample-data/utm-tracker-sample.csv` with `sample-data/salesforce-campaigns-sample.csv`. It must say 7 of 14 links are ready, and list rows 3, 4, 5, 8, 9, 12 and 13 to fix before launch.
2. Ask it to build a link with content "Video CFO". It must refuse and suggest `video-cfo`.
3. Ask it to use source "tiktok". It must ask before adding a new source.
