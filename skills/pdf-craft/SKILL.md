---
name: pdf-craft
description: >
  Advanced programmatic PDF crafting and typography design. Compile vector layouts, branded executive reports, invoices, and multi-page ebooks with pixel-perfect pagination.
metadata:
  version: "1.0.0"
  category: content_media
  triggers: pdf-craft, programmatic pdf, pdf layout, report generation, typst pdf, weasyprint
---

# PDF Craft — Professional Programmatic PDF Generation

Designs and compiles publication-quality PDF documents using modern CSS Paged Media (WeasyPrint / Typst / Playwright PDF).

## Key Principles
1. **Paged Media Rules**: Configure `@page { size: A4; margin: 20mm; @bottom-right { content: counter(page); } }`.
2. **Typography Hierarchy**: Distinct serif or clean sans typography with strict line heights and contrast ratios.
3. **No Orphan Headings**: Enforce `break-inside: avoid` and `page-break-after: avoid` on titles and table headers.
