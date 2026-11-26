---
name: digital-ads-suite
description: >
  Comprehensive marketing & advertising suite covering Google Ads, Meta Ads, TikTok, LinkedIn, Apple Search Ads, Amazon, Microsoft Ads, ad creative generation, copywriting, attribution, tracking, and campaign audit.
category: content_media
version: "2.0.0"
role: consolidated_suite
triggers: digital-ads-suite, digital advertising & creative performance suite, ads, ads-amazon, ads-apple, ads-attribution, ads-audit, ads-budget, ads-competitor, ads-create, ads-creative, ads-dna, ads-generate, ads-google, ads-landing, ads-linkedin, ads-math, ads-meta, ads-microsoft, ads-photoshoot, ads-plan, ads-server-side-tracking, ads-test, ads-tiktok, ads-youtube
---

# 📢 Digital Advertising & Creative Performance Suite

Comprehensive marketing & advertising suite covering Google Ads, Meta Ads, TikTok, LinkedIn, Apple Search Ads, Amazon, Microsoft Ads, ad creative generation, copywriting, attribution, tracking, and campaign audit.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (22 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`ads-amazon`**: Amazon Ads deep analysis covering Sponsored Products, Sponsored Brands (incl. Sponsored Brands Video), Sponsored Display (audiences + contextual), and basic Amazon DSP. Evaluates campaign structure, ACOS/TACOS targets, search-term harvesting, negative keyword discipline, Brand Analytics signals, day-parting, bid management, auto vs manual campaign mix, ASIN targeting, and DSP retargeting. Use when user says Amazon Ads, Amazon advertising, Amazon PPC, Amazon search ads, Sponsored Products, Sponsored Brands, Sponsored Display, Amazon DSP, ACOS, TACOS, retail media audit, Amazon Marketing Services, AMS, or Amazon seller advertising.
  - *Reference File:* `references/ads-amazon.md`
- **`ads-apple`**: Apple Ads (formerly Apple Search Ads) deep analysis for mobile app advertisers. Evaluates campaign structure, bid health, Custom Product Pages (CPPs), AdAttributionKit (view-through attribution 24h post-impression), MMP attribution, budget pacing, TAP coverage (Today/Search/Product Pages), Maximize Conversions bidding, and goal CPA benchmarks by country. Use when user says Apple Ads, Apple Search Ads, ASA, App Store ads, Apple ads, Search Ads, AdAttributionKit, view-through attribution, or is advertising a mobile app on iOS.
  - *Reference File:* `references/ads-apple.md`
- **`ads-attribution`**: Cross-platform attribution health audit covering AdAttributionKit (iOS view-through 24h post-impression, WWDC 2025 configurable windows), GA4 attribution models (data-driven vs last-click), Consent Mode V2 enforcement, server-side attribution stitching, MMP integration health, and cross-device / cross-platform attribution. Use when user says attribution audit, attribution model, AdAttributionKit, AAK, view-through attribution, GA4 attribution, Consent Mode V2, conversion window, attribution window, MMP audit, AppsFlyer audit, Adjust audit, Branch audit, Singular audit, cross-device attribution, or cross-platform attribution.
  - *Reference File:* `references/ads-attribution.md`
- **`ads-audit`**: Full multi-platform paid advertising audit with parallel subagent delegation. Analyzes Google Ads, Meta Ads, LinkedIn Ads, TikTok Ads, Microsoft Ads, and Apple Ads accounts via 6 parallel audit agents. Amazon Ads, cross-platform attribution, and server-side tracking are covered by their standalone sub-skills (ads-amazon, ads-attribution, ads-server-side-tracking) — Wave 3 will add their paired agents so they can dispatch in parallel here. Generates health score per platform and aggregate score (0-100). Use when user says audit, full ad check, analyze my ads, account health check, paid media audit, paid advertising audit, ad spend audit, advertising audit, or PPC audit.
  - *Reference File:* `references/ads-audit.md`
- **`ads-budget`**: Budget allocation and bidding strategy review across all ad platforms. Evaluates spend distribution, bidding strategy appropriateness, scaling readiness, and identifies campaigns to kill or scale. Uses 70/20/10 rule, 3x Kill Rule, and 20% scaling rule. Use when user says budget allocation, bidding strategy, ad spend, ROAS target, media budget, or scaling.
  - *Reference File:* `references/ads-budget.md`
- **`ads-competitor`**: Competitor ad intelligence analysis across Google, Meta, LinkedIn, TikTok, Microsoft, and Apple Ads. Analyzes competitor ad copy, creative strategy, keyword targeting, estimated spend via Meta Ad Library / Google Ads Transparency Center / TikTok Top Ads, and identifies competitive gaps and opportunities. Use when user says competitor ads, ad spy, competitive analysis, competitor PPC, ad intelligence, Meta Ad Library, Facebook Ad Library, Google Ads Transparency, competitor creative, or competitor research.
  - *Reference File:* `references/ads-competitor.md`
- **`ads-create`**: Campaign concept and copy brief generator for paid advertising. Reads brand-profile.json and optional audit results to produce structured campaign concepts, messaging pillars, and copy briefs. Outputs campaign-brief.md to the current directory. Run after /ads dna and before /ads generate. Triggers on: create campaign, campaign brief, ad concepts, write ad copy, campaign strategy, ad messaging, creative brief, generate concepts.
  - *Reference File:* `references/ads-create.md`
- **`ads-creative`**: Cross-platform creative quality audit covering ad copy, video, image, and format diversity across all platforms. Detects creative fatigue, evaluates platform-native compliance, scores creative diversity for Andromeda Entity-ID retrieval, and provides production priorities. Use when user says creative audit, ad creative, creative fatigue, creative diversity score, ad variation audit, ad copy, ad design, or creative review.
  - *Reference File:* `references/ads-creative.md`
- **`ads-dna`**: Brand DNA extractor for paid advertising. Scans a website URL to extract visual identity, tone of voice, color palette, typography, and imagery style. Outputs brand-profile.json to the current directory. Run before /ads create or /ads generate for brand-consistent creative. Triggers on: brand DNA, brand profile, extract brand, brand identity, brand colors, what is the brand voice, analyze brand, brand style guide.
  - *Reference File:* `references/ads-dna.md`
- **`ads-generate`**: AI image generation for paid ad creatives. Reads campaign-brief.md and brand-profile.json to produce platform-sized ad images using banana-claude. Requires banana-claude (v1.4.1+) with nanobanana-mcp configured. Triggers on: generate ads, create images, make ad creatives, generate visuals, create ad images, generate campaign images, make the images, generate from brief.
  - *Reference File:* `references/ads-generate.md`
- **`ads-google`**: Google Ads deep analysis covering Search, Performance Max, AI Max, Display, YouTube, and Demand Gen campaigns. Evaluates 80 checks across conversion tracking, wasted spend, account structure, keywords, ads, and settings. Includes AI Max (search-term-matching, AI Brief, text customization, FUE, brand exclusions) and Smart Bidding signals. Use when user says Google Ads, Google PPC, search ads, PMax, Performance Max, AI Max, AI Brief, broad match audit, Quality Score check, search terms audit, Smart Bidding, or Google campaign.
  - *Reference File:* `references/ads-google.md`
- **`ads-landing`**: Landing page quality assessment for paid advertising campaigns. Evaluates message match, page speed, mobile experience, trust signals, form optimization, and conversion rate potential. Use when user says landing page, post-click experience, landing page audit, LP audit, conversion rate, landing page CRO, post-click CRO, or landing page optimization.
  - *Reference File:* `references/ads-landing.md`
- **`ads-linkedin`**: LinkedIn Ads deep analysis for B2B advertising. Evaluates 27 checks across technical setup, audience targeting, creative quality, lead gen forms, and bidding strategy. Includes Thought Leader Ads, ABM, predictive audiences, and the Oct 2025 Campaign Groups→Campaigns→Ad Sets terminology change. Use when user says LinkedIn Ads, B2B ads, sponsored content, lead gen forms, InMail, ABM ads, Thought Leader Ads, predictive audiences, B2B paid, or LinkedIn campaign.
  - *Reference File:* `references/ads-linkedin.md`
- **`ads-math`**: PPC financial calculator and modeling tool. CPA, ROAS, CPL calculations, break-even analysis, impression share opportunity sizing, budget forecasting, LTV:CAC ratio analysis, and MER (Marketing Efficiency Ratio) assessment. Requires zero API access. Works with pasted data from exports. Use when user says PPC math, ad calculator, break-even, budget forecast, ROAS calculator, CPA calculator, impression share, LTV CAC, or MER.
  - *Reference File:* `references/ads-math.md`
- **`ads-meta`**: Meta Ads deep analysis covering Facebook, Instagram, and Threads advertising in the Andromeda + GEM + Lattice era. Evaluates 50 checks across Pixel/CAPI health, creative diversity and Entity-ID clustering risk, account structure, ASC/AAC defaults for Sales/Leads/App, and audience targeting. Includes Advantage+ assessment and creative-as-targeting scoring. Use when user says Meta Ads, Facebook Ads, Instagram Ads, Threads ads, Advantage+, ASC, AAC, Andromeda, GEM, Lattice, Entity-ID clustering, creative diversity, Sales optimization, Leads optimization, App optimization, or Meta campaign.
  - *Reference File:* `references/ads-meta.md`
- **`ads-microsoft`**: Microsoft/Bing Ads deep analysis covering search, Performance Max, Audience Network, and Copilot integration. Evaluates 24 checks with focus on Google Ads import validation, unique Microsoft features (LinkedIn audience targeting, in-market audiences), and cost advantage assessment. Use when user says Microsoft Ads, Bing Ads, Bing PPC, Bing search ads, Copilot ads, Microsoft search ads, Google import audit, or Microsoft campaign.
  - *Reference File:* `references/ads-microsoft.md`
- **`ads-photoshoot`**: Product photography enhancement for ad creatives using banana-claude image generation. Takes a product image and generates 5 professional photography styles for ad use: Studio, Floating, Ingredient, In Use, and Lifestyle. Requires banana-claude (v1.4.1+) with nanobanana-mcp. Triggers on: product photo, product photography, photoshoot, enhance product image, product shoot, product photos for ads, generate product photos, studio shot, lifestyle photo.
  - *Reference File:* `references/ads-photoshoot.md`
- **`ads-plan`**: Strategic paid advertising planning with industry-specific templates. Covers platform selection, campaign architecture, budget planning, creative strategy, and phased implementation roadmap. Use when user says ad plan, ad strategy, campaign planning, media plan, PPC strategy, or advertising plan.
  - *Reference File:* `references/ads-plan.md`
- **`ads-server-side-tracking`**: Server-side tracking pipeline audit covering server-side Google Tag Manager (sGTM), Meta CAPI Gateway, Conversions API health, event deduplication via event_id, server-side hit ratio targets, pixel debugging, and PII hashing discipline. Use when user says server-side tracking, sGTM, server-side GTM, server-side tagging, CAPI, Conversions API, CAPI Gateway, Meta Conversions API, event deduplication, event_id, pixel debug, pixel health, Pixel/CAPI audit, first-party tracking, iOS 14.5 recovery, or server-side hit ratio.
  - *Reference File:* `references/ads-server-side-tracking.md`
- **`ads-test`**: A/B test design and experiment planning for paid advertising. Structured hypothesis framework, statistical significance calculator, test duration estimator, sample size calculator, and platform-specific experiment setup guides (Meta Experiments, Google Experiments, LinkedIn A/B). Use when user says A/B test, split test, experiment design, test hypothesis, statistical significance, sample size, or test duration.
  - *Reference File:* `references/ads-test.md`
- **`ads-tiktok`**: TikTok Ads deep analysis covering creative quality, tracking, bidding, campaign structure, and TikTok Shop under the TikTok USDS Joint Venture (post Jan 2026 divestiture). Evaluates 28 checks with emphasis on creative-first strategy, safe zone compliance, creative diversity for retrieval, and Smart+ campaigns. Use when user says TikTok Ads, TikTok marketing, TikTok Shop, Spark Ads, Smart+, USDS, creative diversity for retrieval, or TikTok campaign.
  - *Reference File:* `references/ads-tiktok.md`
- **`ads-youtube`**: YouTube Ads specific analysis covering campaign types, creative quality, audience targeting, and measurement. Evaluates video ad performance across skippable in-stream, non-skippable, bumper, Shorts, Demand Gen, and Connected TV (CTV) formats. Covers VAC→Demand Gen migration, Shorts creative requirements, CTV shoppable ads, and frequency capping. Use when user says YouTube Ads, video ads, pre-roll, bumper ads, skippable in-stream, YouTube campaign, YouTube Shorts ads, Demand Gen, VAC, or CTV YouTube ads.
  - *Reference File:* `references/ads-youtube.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `ads-amazon`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
