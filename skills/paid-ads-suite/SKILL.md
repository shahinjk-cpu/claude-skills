---
name: paid-ads-suite
description: Comprehensive multi-platform advertising and paid acquisition master suite covering Google, Meta, TikTok, Amazon, Apple Search Ads, LinkedIn, Reddit, and Pinterest.
---

# Paid Ads & Performance Marketing Master Suite

Cross-channel advertising strategies, campaign architecture, attribution modeling, and creative optimization.

## Supported Ad Networks & Playbooks
### Amazon (`ads-amazon`)
---
name: ads-amazon
description: "Amazon Ads deep analysis covering Sponsored Products, Sponsored Brands (incl. Sponsored Brands Video), Sponsored Display (audiences + contextual), and basic Amazon DSP. Evaluates campaign structure, ACOS/TACOS targets, search-term harvesting, negative keyword discipline, Brand Analytics signals, day-parting, bid management, auto vs manual campaign mix, ASIN targeting, and DSP retargeting. Use when user says Amaz

### Apple (`ads-apple`)
---
name: ads-apple
description: "Apple Ads (formerly Apple Search Ads) deep analysis for mobile app advertisers. Evaluates campaign structure, bid health, Custom Product Pages (CPPs), AdAttributionKit (view-through attribution 24h post-impression), MMP attribution, budget pacing, TAP coverage (Today/Search/Product Pages), Maximize Conversions bidding, and goal CPA benchmarks by country. Use when user says Apple Ads, Apple Search Ads, ASA, App St

### Attribution (`ads-attribution`)
---
name: ads-attribution
description: "Cross-platform attribution health audit covering AdAttributionKit (iOS view-through 24h post-impression, WWDC 2025 configurable windows), GA4 attribution models (data-driven vs last-click), Consent Mode V2 enforcement, server-side attribution stitching, MMP integration health, and cross-device / cross-platform attribution. Use when user says attribution audit, attribution model, AdAttributionKit, AAK, view-

### Audit (`ads-audit`)
---
name: ads-audit
description: "Full multi-platform paid advertising audit with parallel subagent delegation. Analyzes Google Ads, Meta Ads, LinkedIn Ads, TikTok Ads, Microsoft Ads, and Apple Ads accounts via 6 parallel audit agents. Amazon Ads, cross-platform attribution, and server-side tracking are covered by their standalone sub-skills (ads-amazon, ads-attribution, ads-server-side-tracking) — Wave 3 will add their paired agents so they can 

### Budget (`ads-budget`)
---
name: ads-budget
description: "Budget allocation and bidding strategy review across all ad platforms. Evaluates spend distribution, bidding strategy appropriateness, scaling readiness, and identifies campaigns to kill or scale. Uses 70/20/10 rule, 3x Kill Rule, and 20% scaling rule. Use when user says budget allocation, bidding strategy, ad spend, ROAS target, media budget, or scaling."
user-invokable: false
tested_date: 2026-05-17
tested_wit

### Competitor (`ads-competitor`)
---
name: ads-competitor
description: "Competitor ad intelligence analysis across Google, Meta, LinkedIn, TikTok, Microsoft, and Apple Ads. Analyzes competitor ad copy, creative strategy, keyword targeting, estimated spend via Meta Ad Library / Google Ads Transparency Center / TikTok Top Ads, and identifies competitive gaps and opportunities. Use when user says competitor ads, ad spy, competitive analysis, competitor PPC, ad intelligence, Meta Ad

### Create (`ads-create`)
---
name: ads-create
description: "Campaign concept and copy brief generator for paid advertising. Reads brand-profile.json and optional audit results to produce structured campaign concepts, messaging pillars, and copy briefs. Outputs campaign-brief.md to the current directory. Run after /ads dna and before /ads generate. Triggers on: create campaign, campaign brief, ad concepts, write ad copy, campaign strategy, ad messaging, creative brief, ge

### Creative (`ads-creative`)
---
name: ads-creative
description: "Cross-platform creative quality audit covering ad copy, video, image, and format diversity across all platforms. Detects creative fatigue, evaluates platform-native compliance, scores creative diversity for Andromeda Entity-ID retrieval, and provides production priorities. Use when user says creative audit, ad creative, creative fatigue, creative diversity score, ad variation audit, ad copy, ad design, or crea

### Dna (`ads-dna`)
---
name: ads-dna
description: "Brand DNA extractor for paid advertising. Scans a website URL to extract visual identity, tone of voice, color palette, typography, and imagery style. Outputs brand-profile.json to the current directory. Run before /ads create or /ads generate for brand-consistent creative. Triggers on: brand DNA, brand profile, extract brand, brand identity, brand colors, what is the brand voice, analyze brand, brand style guide."

### Generate (`ads-generate`)
---
name: ads-generate
description: "AI image generation for paid ad creatives. Reads campaign-brief.md and brand-profile.json to produce platform-sized ad images using banana-claude. Requires banana-claude (v1.4.1+) with nanobanana-mcp configured. Triggers on: generate ads, create images, make ad creatives, generate visuals, create ad images, generate campaign images, make the images, generate from brief."
user-invokable: false
tested_date: 2026

### Google (`ads-google`)
---
name: ads-google
description: "Google Ads deep analysis covering Search, Performance Max, AI Max, Display, YouTube, and Demand Gen campaigns. Evaluates 80 checks across conversion tracking, wasted spend, account structure, keywords, ads, and settings. Includes AI Max (search-term-matching, AI Brief, text customization, FUE, brand exclusions) and Smart Bidding signals. Use when user says Google Ads, Google PPC, search ads, PMax, Performance Ma

### Landing (`ads-landing`)
---
name: ads-landing
description: "Landing page quality assessment for paid advertising campaigns. Evaluates message match, page speed, mobile experience, trust signals, form optimization, and conversion rate potential. Use when user says landing page, post-click experience, landing page audit, LP audit, conversion rate, landing page CRO, post-click CRO, or landing page optimization."
user-invokable: false
tested_date: 2026-05-17
tested_with: cl

### Linkedin (`ads-linkedin`)
---
name: ads-linkedin
description: "LinkedIn Ads deep analysis for B2B advertising. Evaluates 27 checks across technical setup, audience targeting, creative quality, lead gen forms, and bidding strategy. Includes Thought Leader Ads, ABM, predictive audiences, and the Oct 2025 Campaign Groups→Campaigns→Ad Sets terminology change. Use when user says LinkedIn Ads, B2B ads, sponsored content, lead gen forms, InMail, ABM ads, Thought Leader Ads, pred

### Math (`ads-math`)
---
name: ads-math
description: "PPC financial calculator and modeling tool. CPA, ROAS, CPL calculations, break-even analysis, impression share opportunity sizing, budget forecasting, LTV:CAC ratio analysis, and MER (Marketing Efficiency Ratio) assessment. Requires zero API access. Works with pasted data from exports. Use when user says PPC math, ad calculator, break-even, budget forecast, ROAS calculator, CPA calculator, impression share, LTV CA

### Meta (`ads-meta`)
---
name: ads-meta
description: "Meta Ads deep analysis covering Facebook, Instagram, and Threads advertising in the Andromeda + GEM + Lattice era. Evaluates 50 checks across Pixel/CAPI health, creative diversity and Entity-ID clustering risk, account structure, ASC/AAC defaults for Sales/Leads/App, and audience targeting. Includes Advantage+ assessment and creative-as-targeting scoring. Use when user says Meta Ads, Facebook Ads, Instagram Ads, T

### Microsoft (`ads-microsoft`)
---
name: ads-microsoft
description: "Microsoft/Bing Ads deep analysis covering search, Performance Max, Audience Network, and Copilot integration. Evaluates 24 checks with focus on Google Ads import validation, unique Microsoft features (LinkedIn audience targeting, in-market audiences), and cost advantage assessment. Use when user says Microsoft Ads, Bing Ads, Bing PPC, Bing search ads, Copilot ads, Microsoft search ads, Google import audit, or

### Photoshoot (`ads-photoshoot`)
---
name: ads-photoshoot
description: "Product photography enhancement for ad creatives using banana-claude image generation. Takes a product image and generates 5 professional photography styles for ad use: Studio, Floating, Ingredient, In Use, and Lifestyle. Requires banana-claude (v1.4.1+) with nanobanana-mcp. Triggers on: product photo, product photography, photoshoot, enhance product image, product shoot, product photos for ads, generate pro

### Plan (`ads-plan`)
---
name: ads-plan
description: "Strategic paid advertising planning with industry-specific templates. Covers platform selection, campaign architecture, budget planning, creative strategy, and phased implementation roadmap. Use when user says ad plan, ad strategy, campaign planning, media plan, PPC strategy, or advertising plan."
user-invokable: false
tested_date: 2026-05-17
tested_with: claude-code v2.x
---

# Strategic Paid Advertising Plan

St

### Server Side Tracking (`ads-server-side-tracking`)
---
name: ads-server-side-tracking
description: "Server-side tracking pipeline audit covering server-side Google Tag Manager (sGTM), Meta CAPI Gateway, Conversions API health, event deduplication via event_id, server-side hit ratio targets, pixel debugging, and PII hashing discipline. Use when user says server-side tracking, sGTM, server-side GTM, server-side tagging, CAPI, Conversions API, CAPI Gateway, Meta Conversions API, event deduplication,

### Test (`ads-test`)
---
name: ads-test
description: "A/B test design and experiment planning for paid advertising. Structured hypothesis framework, statistical significance calculator, test duration estimator, sample size calculator, and platform-specific experiment setup guides (Meta Experiments, Google Experiments, LinkedIn A/B). Use when user says A/B test, split test, experiment design, test hypothesis, statistical significance, sample size, or test duration."
u

### Tiktok (`ads-tiktok`)
---
name: ads-tiktok
description: "TikTok Ads deep analysis covering creative quality, tracking, bidding, campaign structure, and TikTok Shop under the TikTok USDS Joint Venture (post Jan 2026 divestiture). Evaluates 28 checks with emphasis on creative-first strategy, safe zone compliance, creative diversity for retrieval, and Smart+ campaigns. Use when user says TikTok Ads, TikTok marketing, TikTok Shop, Spark Ads, Smart+, USDS, creative diversi

### Youtube (`ads-youtube`)
---
name: ads-youtube
description: "YouTube Ads specific analysis covering campaign types, creative quality, audience targeting, and measurement. Evaluates video ad performance across skippable in-stream, non-skippable, bumper, Shorts, Demand Gen, and Connected TV (CTV) formats. Covers VAC→Demand Gen migration, Shorts creative requirements, CTV shoppable ads, and frequency capping. Use when user says YouTube Ads, video ads, pre-roll, bumper ads, 

