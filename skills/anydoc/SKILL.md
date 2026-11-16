---
name: anydoc
description: >
  Universal document conversion engine. Seamlessly converts between Markdown, PDF, DOCX, XLSX, HTML, EPUB, and LaTeX while maintaining typography and layout fidelity.
metadata:
  version: "1.0.0"
  category: content_media
  triggers: anydoc, convert docx to pdf, markdown to docx, document converter, pandoc wrapper
---

# AnyDoc — Universal Document Conversion Pipeline

Converts documents across formats (PDF, DOCX, Markdown, HTML, XLSX, LaTeX) with strict typography preservation and clean asset embedding.

## Workflow Reference
- Markdown to DOCX: Pure JS / Python OpenXML compilation.
- HTML to PDF: Playwright print-to-pdf with `@page` styling.
- PDF to Markdown: Multi-column OCR and table extraction.
