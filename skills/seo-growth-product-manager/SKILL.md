---
name: seo-growth-product-manager
description: Implements technical SEO, Schema.org JSON-LD structured data, Answer Engine Optimization (AEO for AI search), OpenGraph social cards, conversion rate optimization (CRO), and Product Management artifacts (PRDs, User Stories, RICE prioritization, KPI trees). Use when launching websites, optimizing search rankings, or planning product roadmaps.
---

# Technical SEO, Growth & Product Management Skill

Unified playbook combining technical SEO/AEO engineering (`coreyhaines/marketing-skills`) and structured Product Management frameworks (`deanpeters/pm-skills`).

---

## 1. Technical SEO & AI Search Optimization (AEO) Checklist

Every public-facing web application or landing page must implement:

### A. Complete Metadata & Canonical Architecture
- **Title Tag**: 50–60 characters, primary keyword front-loaded (`Primary Keyword — Secondary Value | Brand`).
- **Meta Description**: 150–160 characters with a clear value proposition and call-to-action.
- **Canonical URL**: Always set `<link rel="canonical" href="https://domain.com/clean-path" />` to prevent duplicate content penalties from query parameters (`?utm_source=...`).
- **Hreflang Tags**: For multilingual sites (e.g., `az`, `en`, `ru`, `tr`), specify `<link rel="alternate" hreflang="az" ... />` and `hreflang="x-default"`.

### B. OpenGraph (OG) & Twitter/X Dynamic Cards
```html
<meta property="og:type" content="website" />
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:image" content="https://domain.com/og-image.png" /> <!-- 1200x630px -->
<meta name="twitter:card" content="summary_large_image" />
```

### C. Schema.org JSON-LD Structured Data
Inject valid JSON-LD in `<head>` so Google and AI Answer Engines (Perplexity, ChatGPT Search, Google AI Overviews) parse entities accurately:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Product Name",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web, Windows, iOS, Android",
  "offers": {
    "@type": "Offer",
    "price": "29.00",
    "priceCurrency": "USD"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.9",
    "ratingCount": "128"
  }
}
</script>
```

### D. Crawlability & AI Indexing (`robots.txt`, `sitemap.xml`, `llms.txt`)
- Generate dynamic XML sitemaps (`/sitemap.xml`) with `<lastmod>` timestamps.
- Provide `/llms.txt` and `/llms-full.txt` at the root domain to give AI crawlers a clean, markdown-formatted summary of your product, documentation, and API capabilities.

---

## 2. Conversion Rate Optimization (CRO) & Landing Page Anatomy

Structure high-converting landing pages using the **PAS (Problem–Agitate–Solution)** or **AIDA** hierarchy:
1. **Above the Fold (Hero)**:
   - Specific outcome-driven headline (what the user achieves, not vague buzzwords).
   - Subheadline explaining *how* it works and *who* it is for.
   - Primary CTA button with micro-copy reducing friction (e.g., *"Start Free — No credit card required"*).
   - Interactive product preview, live demo widget, or high-contrast dashboard visual.
2. **Social Proof & Trust Bar**: Quantified metrics, customer logos, or verifiable benchmarks.
3. **Feature-to-Benefit Bento Grid**: Group features into 3–4 visual cards focusing on user outcomes.
4. **Objection Handling (FAQ with `FAQPage` JSON-LD)**: Address pricing, security, migration, and support questions directly.

---

## 3. Product Management (PM) Frameworks

### A. RICE Prioritization Matrix
When prioritizing features or backlog items, score each item using:
$$\text{RICE Score} = \frac{\text{Reach} \times \text{Impact} \times \text{Confidence}}{\text{Effort}}$$
- **Reach**: Users affected per quarter.
- **Impact**: `3` (Massive), `2` (High), `1` (Medium), `0.5` (Low), `0.25` (Minimal).
- **Confidence**: `100%` (High data), `80%` (Medium), `50%` (Low).
- **Effort**: Person-weeks required.

### B. Product Requirements Document (PRD) Template
1. **Problem Statement & User Persona**: Who is struggling, why, and what is the cost of inaction?
2. **Goals & Non-Goals (Scope Guardrails)**: Explicit KPIs (e.g., Activation Rate, D30 Retention, P95 Latency) and what is strictly out of scope for v1.
3. **User Stories & Acceptance Criteria (Given / When / Then)**:
   - *Given* a user with an expired subscription, *When* they attempt to export a PDF report, *Then* display the upgrade modal while preserving their draft state.
4. **Edge Cases & Empty/Error States**: Zero-data onboarding view, rate-limit fallback, offline behavior.
5. **Analytics & Telemetry Events**: Define exact event names and properties (e.g., `checkout_completed { plan_id, billing_cycle, revenue_usd }`).
