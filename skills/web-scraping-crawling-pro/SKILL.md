---
name: web-scraping-crawling-pro
description: Extracts clean, structured data and LLM-ready Markdown from complex websites, SPAs, and APIs with anti-bot handling, smart parsing, and prompt-driven graph extraction. Combines D4Vinci/Scrapling (87k ⭐), ScrapeGraphAI (17k ⭐), and Firecrawl. Use when gathering data from the web, bypassing bot protection, scraping competitor sites, extracting tables to JSON, or feeding external pages into RAG.
---

# Web Scraping, Intelligent Crawling & ScrapeGraphAI Pro

Unified web intelligence engine combining **anti-bot resilience** (`D4Vinci/Scrapling` ~87k ⭐), **prompt-driven graph extraction** (`ScrapeGraphAI` ~17k ⭐), and **clean Markdown transformations** (`Firecrawl`).

---

## 1. Unified 4-Tier Extraction Strategy

When tasked with extracting data from web sources, follow this priority hierarchy to maximize speed, minimize token spend, and avoid bot blocking:

```
[Level 1: Network Inspection]  --> Query hidden internal JSON APIs (10x faster, zero HTML parsing)
       │ (if no API)
       ▼
[Level 2: Stealth Fetching]    --> Scrapling / httpx with TLS spoofing (bypasses Cloudflare & WAF)
       │ (if JS-heavy SPA)
       ▼
[Level 3: Headless Playwright] --> Full DOM hydration with stealth human mouse/scroll behavior
       │ (for structured data)
       ▼
[Level 4: ScrapeGraphAI Mode]  --> Natural language prompt-to-JSON without writing CSS/XPath
```

---

## 2. Level 1 & 2: Anti-Bot & Stealth Extraction (`Scrapling`)

Use when scraping high-security sites protected by Cloudflare Turnstile, Datadome, or PerimeterX without triggering CAPTCHAs.

### Python Stealth Pattern (`scrapling`)
```python
from scrapling import Fetcher, StealthyFetcher

# 1. Fast static fetch with auto-rotating headers
fetcher = Fetcher()
response = fetcher.get("https://example.com/products")

# 2. For Cloudflare-protected dynamic pages (Stealth mode)
stealth = StealthyFetcher()
page = stealth.fetch("https://protected-site.com/catalog", headless=True)

# Smart DOM query (auto-adapts if class names change slightly)
products = page.css(".product-card")
for item in products:
    name = item.css("h3::text").first
    price = item.css(".price::text").first
```

---

## 3. Level 4: Prompt-Driven Scraping (`ScrapeGraphAI`)

Use when you need structured JSON immediately without spending time writing or debugging CSS/XPath selectors.

### Setup & Multi-Model Execution
```bash
pip install scrapegraphai
```

### A. Single Page Smart Extraction (`SmartScraperGraph`)
```python
from scrapegraphai.graphs import SmartScraperGraph

# Works with Google Gemini, Groq, OpenAI, or local Ollama
graph_config = {
    "llm": {
        "model": "google_genai/gemini-2.0-flash", # Or "groq/llama-3.3-70b-versatile"
        "api_key": "YOUR_API_KEY",
        "temperature": 0.0,
    },
    "verbose": False,
    "headless": True,
}

smart_scraper = SmartScraperGraph(
    prompt="Extract a JSON list of all products with their title, current price, rating, and image URL.",
    source="https://target-ecommerce.com/items",
    config=graph_config
)

result = smart_scraper.run()
# Returns structured dictionary / JSON ready for database insertion
print(result)
```

### B. Multi-Page Search & Aggregate (`SearchGraph`)
Scrapes multiple search results across Google/DuckDuckGo automatically:
```python
from scrapegraphai.graphs import SearchGraph

search_graph = SearchGraph(
    prompt="Find the top 5 open-source AI game engines and list their GitHub stars, primary language, and key feature.",
    config=graph_config
)
result = search_graph.run()
```

---

## 4. LLM-Ready Markdown Cleaning (For RAG & Dissertation Synthesis)

When ingesting web pages into RAG databases or research documents, strip noise to preserve context window tokens:

1. **Remove Noise Elements**:
   - Strip `<nav>`, `<header>`, `<footer>`, `<aside>`, `<script>`, `<style>`, cookie modals, and tracking pixels.
2. **Preserve Semantic Information**:
   - Retain hierarchical headings (`#` through `####`), code blocks (` ``` `), tabular data (`| Header | ... |`), and blockquotes.
3. **Link & Image Curation**:
   - Keep relative or absolute canonical links for citations; drop decorative SVG icons and base64 tracking pixels.

---

## 5. Decision Matrix: Which Tool to Choose?

| Scenario | Best Tool | Why? |
|---|---|---|
| **E-commerce / Catalog with Cloudflare** | `Scrapling` (StealthyFetcher) | Bypasses bot detection without paying for proxy services |
| **Quick one-off data extraction (no code)** | `ScrapeGraphAI` (`SmartScraperGraph`) | Prompt-to-JSON in 3 lines of code; zero CSS selectors required |
| **Feeding articles / papers into RAG** | `Firecrawl` / Markdown Cleaner | Strips all ads and UI chrome, producing clean token-efficient text |
| **Multi-source automated research** | `ScrapeGraphAI` (`SearchGraph`) | Automatically discovers, crawls, and aggregates across multiple URLs |
