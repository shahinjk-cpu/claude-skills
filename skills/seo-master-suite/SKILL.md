---
name: seo-master-suite
description: Comprehensive Generative Engine Optimization (GEO) and technical SEO master suite covering Ahrefs, SERP, schema markup, technical auditing, programmatic SEO, and ranking strategies.
---

# SEO Master Suite & Search Intelligence


## Specialized SEO Subsystems & Tool Workflows

### Module: seo-aeo
---
name: seo-aeo
description: |
  AI Search Optimization (AEO / Answer Engine Optimization): optimize for Google AI Overviews,
  Perplexity citations, ChatGPT mentions. Structured data for AI consumption, FAQ and entity
  optimization, brand authority signals, brand SERP management.

  USE FOR:
  - "AI search", "AEO", "GEO", "AI overview", "AI optimization"
  - "answer engine optimization", "AI engine optimization", "generative engine optimization"
  - "Perplexity", "ChatGPT visibility", "AI ci

### Module: seo-agentic
---
name: seo-agentic
description: >
  Audit and fix agent readiness: the Lighthouse Agentic Browsing fraction,
  accessibility tree for agents, robots.txt and Content-Signal for AI agents,
  WAF treatment of agent traffic, llms.txt, Markdown delivery, ai-catalog.json,
  /.well-known discovery files, and WebMCP tools. Use when the user asks
  whether AI agents can use or browse the site, or about llms.txt or WebMCP.
  Exclude AI citability and brand signals (seo-geo) and commerce protocol
  dept

### Module: seo-ahrefs
---
name: seo-ahrefs
description: Ahrefs API analyst (extension). Reads referring domains, backlinks, organic keywords, and content explorer data via the tested @ahrefs/mcp@0.0.11 server. Pairs with seo-backlinks for multi-source confidence weighting.
metadata:
  version: "2.6.2"
compatibility: "Tested with @ahrefs/mcp@0.0.11 (installed by extensions/ahrefs/install.sh)."
---

# seo-ahrefs

Live Ahrefs data via the tested `@ahrefs/mcp@0.0.11` server.
Package check (2026-07-10): verify the current

### Module: seo-analysis
---
name: seo-analysis
description: >-
  Technical and content SEO auditing and optimization.
---

# SEO Analysis

## Overview
Technical and content SEO auditing and optimization.
- **Category**: Automation

## Best Practices & Workflows
1. Integrate SEO Analysis following standard production patterns.
2. Maintain high reliability and environment configuration.


### Module: seo-audit
---
name: seo-audit
description: When the user wants to audit, review, or diagnose SEO issues on their site. Also use when the user mentions "SEO audit," "technical SEO," "why am I not ranking," "SEO issues," "on-page SEO," "meta tags review," or "SEO health check." For building pages at scale to target keywords, see programmatic-seo. For adding structured data, see schema-markup.
---

# SEO Audit

You are an expert in search engine optimization. Your goal is to identify SEO issues and provide a

### Module: seo-autopilot
---
name: seo-autopilot
description: >-
  Runs end-to-end daily SEO for a product inside its repository with persistent state in seo/, covering site health checks, commit fact-checks, Page 2 to Page 1 pushes, AI answer tracking, competitor sitemap diffs, monthly keyword maps, articles, comparison pages, free tools, and link drafts. Use when the user mentions "seo autopilot", wants autonomous daily SEO PRs, or asks an agent to own a site's ongoing search growth.
metadata:
  version: 1.0.0
  autho

### Module: seo-backlinks
---
name: seo-backlinks
description: |
  Backlink analysis and link building strategy: competitor backlink profiling, outreach plan
  generation, monthly SEO reporting framework, toxic link identification, link opportunity
  scoring, and unlinked mention discovery.

  USE FOR:
  - "backlinks", "link building", "outreach", "link profile"
  - "competitor backlinks", "who links to my competitors"
  - "toxic links", "disavow", "link audit", "spammy links"
  - "outreach plan", "link building strategy

### Module: seo-bing
---
name: seo-bing
description: Bing Webmaster Tools + IndexNow extension. Microsoft Copilot citations are fed by the Bing index; this skill makes Bing visibility, link data, and IndexNow URL submission first-class.
user-invocable: true
argument-hint: "[command] [url]"
license: MIT
metadata:
  version: "2.6.2"
compatibility: "Requires BING_WEBMASTER_API_KEY and (optionally) INDEXNOW_KEY in ~/.claude/settings.json env. The skill ships with the claude-seo plugin; run extensions/bing-webmaster/inst

### Module: seo-blog-images
---
name: seo-blog-images
description: Plan, generate, compress, verify, and wire high-CTR cover images and inline proof visuals into blog posts (MDX, Astro, Next.js, Hugo, HTML) with strict image SEO checks. Use when adding a blog cover or OG image, generating inline visuals without dark icon-box AI slop, capturing real product screenshots or data charts, or auditing image alt text, filenames, and Core Web Vitals attributes.
metadata:
  author: illyism
  source: https://il.ly/skills/seo-blog-im

### Module: seo-cluster
---
name: seo-cluster
description: >
  Cluster keywords by SERP overlap and design hub-and-spoke content architecture
  with internal links. Use for planning; `/seo cluster execute` then writes the
  posts with claude-blog's blog-write skill when it is installed, or content
  briefs when it is not.
user-invocable: true
argument-hint: "<seed-keyword or url>"
license: MIT
metadata:
  author: AgriciDaniel
  original_author: "Lutfiya Miller (Pro Hub Challenge Winner)"
  version: "2.6.2"
  category: 

### Module: seo-competitor-pages
---
name: seo-competitor-pages
description: >
  Generate SEO-optimized competitor comparison and alternatives pages. Covers
  "X vs Y" layouts, "alternatives to X" pages, feature matrices, schema markup,
  and conversion optimization. Use when user says "comparison page", "vs page",
  "alternatives page", "competitor comparison", "X vs Y", "versus",
  "compare competitors", or "alternative to".
user-invocable: true
argument-hint: "[url or generate] [competitor]"
license: MIT
metadata:
  author: 

### Module: seo-content
---
name: seo-content
description: |
  Content optimization for SEO: on-page scoring (0-100), E-E-A-T analysis, title/meta
  optimization, heading structure, keyword density, SERP preview, content readability,
  featured snippet optimization, content gap and decay detection, pre-publish checklists.

  USE FOR:
  - "optimize this page", "content score", "on-page SEO", "page score"
  - "title tag", "meta description", "heading structure"
  - "E-E-A-T", "content quality", "content audit"
  - "pre-p

### Module: seo-content-brief
---
name: seo-content-brief
description: >
  Generate competitive SEO content briefs with per-section word counts,
  competitor scoring, keyword placement guidance, and page-type templates.
  Supports both new page briefs and improve-existing-page briefs.
  Use when user says "content brief", "write a brief", "content outline",
  "blog brief", "service page brief", "brief for", "writing brief",
  "content plan", or "outline for".
user-invocable: true
argument-hint: "[url-or-keyword] [page-type]"

### Module: seo-dataforseo
---
name: seo-dataforseo
description: >
  Live SEO data via DataForSEO MCP server: SERP analysis, keyword research
  (volume, difficulty, intent, trends), backlink profiles, on-page analysis,
  competitor and content analysis, business listings, AI visibility (LLM
  mention tracking), and domain analytics. Requires DataForSEO extension
  installed. Use when user says "dataforseo", "live SERP", "keyword volume",
  "backlink data", "AI visibility check", or "real search data".
user-invocable: true

### Module: seo-drift
---
name: seo-drift
description: >
  SEO drift monitoring: capture baselines of SEO-critical elements, detect changes,
  and track regressions over time. Git for SEO: baseline, diff, and track changes
  to your on-page SEO. Use when user says "SEO drift", "baseline", "track changes",
  "did anything break", "SEO regression", "compare SEO", "before and after",
  "monitor SEO changes", or "deployment check".
user-invocable: true
argument-hint: "baseline|compare|history <url>"
license: MIT
metadata

### Module: seo-ecommerce
---
name: seo-ecommerce
description: >
  Analyze ecommerce SEO across product pages, product schema, Shopping
  visibility, marketplace signals, and keyword gaps. Use only for stores,
  catalogs, or product listings.
user-invocable: true
argument-hint: "<url or keyword>"
license: MIT
compatibility: "Enhanced with DataForSEO Merchant API (optional)"
metadata:
  author: AgriciDaniel
  original_author: "Matej Marjanovic (Pro Hub Challenge)"
  version: "2.6.2"
  category: seo
---

# E-commerce SEO A

### Module: seo-firecrawl
---
name: seo-firecrawl
description: >
  Full-site crawling, scraping, and site mapping via Firecrawl MCP.
  Use when user says "crawl site", "map site", "full crawl",
  "find all pages", "broken links", "site structure",
  "discover pages", "JS rendering", or needs site-wide analysis.
user-invocable: true
argument-hint: "[command] <url>"
license: MIT
compatibility: "Requires Firecrawl MCP server"
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# Firecrawl Extension for 

### Module: seo-flow
---
name: seo-flow
description: >
  FLOW framework integration: evidence-led SEO using the Find → Leverage →
  Optimize → Win loop. Surfaces stage-specific AI prompts from the FLOW
  knowledge base (41 prompts, CC BY 4.0). Use when user says "FLOW", "FLOW
  framework", "seo flow", "evidence-led SEO", "find leverage optimize win",
  or wants stage-specific SEO prompts.
user-invocable: true
argument-hint: "[stage] [url|topic]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  cate

### Module: seo-fundamentals
---
name: seo-fundamentals
description: SEO fundamentals, E-E-A-T, Core Web Vitals, and Google algorithm principles.
allowed-tools: Read, Glob, Grep
---

# SEO Fundamentals

> Principles for search engine visibility.

---

## 1. E-E-A-T Framework

| Principle | Signals |
|-----------|---------|
| **Experience** | First-hand knowledge, real examples |
| **Expertise** | Credentials, depth of knowledge |
| **Authoritativeness** | Backlinks, mentions, industry recognition |
| **Trustworthiness** | H

### Module: seo-geo
---
name: seo-geo
description: >
  Audit and improve content for AI Overviews and answer engines, including
  citability, entity clarity, crawler access, brand signals, and passage
  structure. Use when the user asks about AI Overviews, AI Mode, ChatGPT,
  Perplexity or Gemini citations, GEO, or AI search visibility.
user-invocable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# AI Search / GEO Optimization (May 2026)

## Prima

### Module: seo-google
---
name: seo-google
description: >
  Google SEO APIs: Search Console (Search Analytics, URL Inspection, Sitemaps),
  PageSpeed Insights v5, CrUX field data with 25-week history, Indexing API v3,
  and GA4 organic traffic. Provides real Google field data for Core Web Vitals,
  indexation status, search performance, and organic traffic trends. Use when
  user says "search console", "GSC", "PageSpeed", "CrUX", "field data",
  "indexing API", "GA4 organic", "URL inspection", or "real CWV data".
use

### Module: seo-growth-product-manager
---
name: seo-growth-product-manager
description: Implements technical SEO, Schema.org JSON-LD structured data, Answer Engine Optimization (AEO for AI search), OpenGraph social cards, conversion rate optimization (CRO), and Product Management artifacts (PRDs, User Stories, RICE prioritization, KPI trees). Use when launching websites, optimizing search rankings, or planning product roadmaps.
---

# Technical SEO, Growth & Product Management Skill

Unified playbook combining technical SEO/AEO engi

### Module: seo-hreflang
---
name: seo-hreflang
description: >
  Hreflang and international SEO audit, validation, and generation. Detects
  common mistakes, validates language/region codes, and generates correct
  hreflang implementations. Use when user says "hreflang", "i18n SEO",
  "international SEO", "multi-language", "multi-region", or "language tags".
user-invocable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# Hreflang & International SEO

Va

### Module: seo-image-gen
---
name: seo-image-gen
description: "AI image generation for SEO assets: OG/social preview images, blog hero images, schema images, product photography, infographics. Powered by Gemini via nanobanana-mcp. Requires banana extension installed. Use when the user wants an SEO asset and says \"OG image\", \"social preview\", \"hero image\", \"blog image\", \"product photo\", \"infographic\", \"seo image\", \"image-gen\", \"favicon\", \"schema image\", or \"pinterest pin\". Not for general artwork, b

### Module: seo-images
---
name: seo-images
description: >
  Image optimization analysis for SEO and performance. Checks alt text, file
  sizes, formats, responsive images, lazy loading, CLS prevention, image SERP
  rankings (via DataForSEO), and image file optimization (WebP/AVIF conversion,
  IPTC/XMP metadata injection). Use when user says "image optimization",
  "alt text", "image SEO", "image size", "image audit", "optimize images",
  "image metadata", "image SERP", "convert to webp", or "image file optimize".
us

### Module: seo-keywords
---
name: seo-keywords
description: |
  Revenue-focused keyword research and strategy for SEO campaigns. Handles keyword discovery,
  clustering, search intent mapping, difficulty assessment, competitor gap analysis, topical
  authority mapping, SERP feature analysis, competitor content strategy reverse engineering,
  and programmatic SEO template generation.

  USE FOR:
  - "keyword research", "find keywords", "keyword strategy"
  - "competitor keywords", "keyword gap analysis"
  - "search inte

### Module: seo-local
---
name: seo-local
description: |
  Local SEO optimization: Google Business Profile post generation, 30-day posting calendars,
  NAP consistency checks, local citation audits, review response templates, local keywords.

  USE FOR:
  - "Google Business Profile", "GBP", "Google My Business", "GMB"
  - "local SEO", "local search", "map pack", "local pack"
  - "GBP posts", "posting calendar", "social posts for business"
  - "NAP consistency", "citations", "local listings", "directories"
  - "review

### Module: seo-maps
---
name: seo-maps
description: >
  Maps intelligence for local SEO: geo-grid rank tracking, GBP profile
  auditing via API, review intelligence across Google/Tripadvisor/Trustpilot,
  cross-platform NAP verification, competitor radius mapping, and
  LocalBusiness schema generation. Three tiers: free (Overpass + Geoapify),
  DataForSEO, and DataForSEO + Google. Use when user says "maps", "geo-grid",
  "rank tracking", "GBP audit", "review velocity", "competitor radius", or
  "SoLV".
user-invocab

### Module: seo-matomo
---
name: seo-matomo
description: Matomo Reporting API extension. Self-hosted or Matomo Cloud analytics as a GA4 alternative or complement. Organic traffic, landing pages, device / country breakdowns, referrers, search keywords. Triggers on "Matomo", "self-hosted analytics", "analytics ohne Google", "GA4 alternative", "Matomo Reporting", "Piwik".
metadata:
  version: "2.6.2"
compatibility: "Requires a Matomo instance URL and API token in matomo.json (0600) in the profile directory (CLAUDE_SEO_PR

### Module: seo-optimizer
---
name: seo-optimizer
description: Search Engine Optimization specialist for content strategy, technical SEO, keyword research, and ranking improvements. Use when optimizing website content, improving search rankings, conducting keyword analysis, or implementing SEO best practices. Expert in on-page SEO, meta tags, schema markup, and Core Web Vitals.
---

# SEO Optimizer

Comprehensive guidance for search engine optimization across content, technical implementation, and strategic planning to i

### Module: seo-page
---
name: seo-page
description: >
  Analyze one supplied URL across on-page, content, technical metadata, schema,
  images, and performance. Use only for a single-page review.
user-invocable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# Single Page Analysis

## Step 1: Run the Deterministic Checks

Run this first. It does the mechanical on-page checks in code, so they are
repeatable and you do not recount them from the HTML b

### Module: seo-plan
---
name: seo-plan
description: >
  Strategic SEO planning for new or existing websites. Industry-specific
  templates, competitive analysis, content strategy, and implementation
  roadmap. Use when user says "SEO plan", "SEO strategy", "SEO planning",
  "content strategy", "keyword strategy", "content calendar",
  "site architecture", or "SEO roadmap".
user-invocable: true
argument-hint: "[business-type]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# St

### Module: seo-posthog
---
name: seo-posthog
description: PostHog MCP extension. PostHog analytics as a GA4 alternative or complement. Organic traffic, landing pages, device / country breakdowns, referrers, via the PostHog MCP server. Triggers on "PostHog", "posthog analytics", "GA4 alternative", "product analytics SEO".
metadata:
  author: AgriciDaniel
  original_author: AlexMili
  version: "2.6.2"
compatibility: "Requires the PostHog MCP server (https://mcp.posthog.com/mcp) connected to Claude Code. No local credent

### Module: seo-profound
---
name: seo-profound
description: Profound LLM citation tracker (extension). Time-series brand citation rates across ChatGPT, Perplexity, and other LLMs. Pairs with seo-seranking for triangulated AI visibility coverage.
metadata:
  version: "2.6.2"
compatibility: "Requires a Profound API key (set PROFOUND_API_KEY by running extensions/profound/install.sh)."
---

# seo-profound

Profound is purpose-built for LLM brand-mention tracking. While
SE Ranking samples prompts on demand, Profound contin

### Module: seo-programmatic
---
name: seo-programmatic
description: >
  Programmatic SEO planning and analysis for pages generated at scale from data
  sources. Covers template engines, URL patterns, internal linking automation,
  thin content safeguards, and index bloat prevention. Use when user says
  "programmatic SEO", "pages at scale", "dynamic pages", "template pages",
  "generated pages", or "data-driven SEO".
user-invocable: true
argument-hint: "[url or plan]"
license: MIT
metadata:
  author: AgriciDaniel
  version

### Module: seo-roast
---
name: seo-roast
description: Runs a brutal, revenue-first SEO teardown of a site and its codebase, kills fatal crawl, programmatic, layout, authority, and AI-visibility blockers in a fix PR, and ships a revenue-ordered seo/roast-roadmap.md (plus an optional client deck). Use when the user says "roast my SEO", "why don't we rank", "audit my site", "SEO teardown", asks why traffic or signups are flat, or wants an SEO review that ends in fixes instead of a checklist.
metadata:
  author: illyism

### Module: seo-schema
---
name: seo-schema
description: >
  Detect, validate, or generate Schema.org JSON-LD for a supplied page or
  entity. Use only when structured data or rich-result markup is requested.
user-invocable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# Schema Markup Analysis & Generation

## Detection

1. Extract JSON-LD with `"${CLAUDE_PLUGIN_ROOT}/scripts/claude-seo" run parse_html.py --url <url> --json`
   (or scan `<script type

### Module: seo-seranking
---
name: seo-seranking
description: SE Ranking AI visibility analyst (extension). Tracks AI Share-of-Voice across ChatGPT, Gemini, Perplexity, AI Overviews, and AI Mode in a single query.
metadata:
  version: "2.6.2"
compatibility: "Requires an SE Ranking API key (set SERANKING_API_KEY by running extensions/seranking/install.sh)."
---

# seo-seranking

Live AI visibility tracking via the SE Ranking REST API.

## Prerequisites

- Run `extensions/seranking/install.sh` (or `install.ps1`).
- An SE 

### Module: seo-shopify
---
name: seo-shopify
description: "Uncapped, sitemap-complete crawl of a Shopify storefront using the merchant's Crawler Access signature from a project-local .shopify-env, feeding the standard seo-audit pipeline. Use when the user says 'Shopify audit', 'crawl the whole store', 'Crawler access', 'signature-agent', 'web-bot-auth', 'rate limited while crawling', or audits a host listed in .shopify-env."
metadata:
  original_author: Nordalux
  version: "2.6.2"
compatibility: "Requires a Shopify st

### Module: seo-sitemap
---
name: seo-sitemap
description: >
  Analyze existing XML sitemaps or generate new ones with industry templates.
  Validates format, URLs, and structure. Use when user says "sitemap",
  "generate sitemap", "sitemap issues", or "XML sitemap".
user-invocable: true
argument-hint: "[url or generate]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# Sitemap Analysis & Generation

## Mode 1: Analyze Existing Sitemap

Discover candidates before reporting a sitem

### Module: seo-sxo
---
name: seo-sxo
description: >
  Diagnose search-experience and intent mismatches using SERP page types, user
  stories, and persona scoring. Use when ranking problems appear intent- or
  layout-driven.
user-invocable: true
argument-hint: "<url> [keyword]"
license: MIT
metadata:
  author: AgriciDaniel
  original_author: "Florian Schmitz (Pro Hub Challenge)"
  version: "2.6.2"
  category: seo
---

# Search Experience Optimization (SXO)

SXO bridges the gap between SEO (what Google rewards) and 

### Module: seo-technical
---
name: seo-technical
description: >
  Audit technical SEO across crawlability, indexability, security, URLs, mobile,
  Core Web Vitals, rendering, structured data, and IndexNow. Use when the user
  asks for a technical SEO audit or about crawling, indexing, rendering, or
  site speed. Exclude content strategy and backlinks.
user-invocable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "2.6.2"
  category: seo
---

# Technical SEO Audit

## Categories

###

### Module: seo-technical-audit
---
name: seo-technical-audit
description: |
  Full technical SEO site audit: crawlability, indexability, speed, mobile, schema markup
  validation with JSON-LD generation, internal linking analysis, Core Web Vitals, page speed
  optimization, crawl budget analysis, cannibalization detection, international SEO.

  USE FOR:
  - "technical SEO audit", "site audit", "SEO health check"
  - "check my site", "crawl errors", "indexing issues"
  - "schema markup", "JSON-LD", "structured data"
  - "core 

### Module: seo-title-optimization
---
name: seo-title-optimization
description: Rewrite and audit SEO page titles, title tags, MDX frontmatter titles, H1 alignment, and bulk title improvements. Use when the user mentions titles, title tags, SERP titles, metadata titles, SEO titles, CTR, truncation, or asks to improve titles across pages.
metadata:
  version: 1.0.0
  author: illyism
  source: https://il.ly/skills/seo-title-optimization
---

# SEO title optimization

Improve page titles for rankings and click-through rate.

## Cor

### Module: seo-unlighthouse
---
name: seo-unlighthouse
description: Multi-page Lighthouse audit via the MIT-licensed Unlighthouse CLI. Free-tier alternative to running PageSpeed against every URL on a site, no API quota burn, runs locally.
metadata:
  version: "2.6.2"
compatibility: "Requires Node 18+ and the unlighthouse npm package. Run extensions/unlighthouse/install.sh to pre-warm."
---

# seo-unlighthouse

Run Lighthouse against every URL on a site (up to a configurable cap)
and aggregate the results. Useful when:

- 

