---
name: pdf-preprocessing-workflow
description: >-
  High-efficiency PDF text, table, and OCR extraction workflow that converts bulky PDFs into clean structured Markdown before passing to LLMs, saving 90% tokens.
---

# PDF Pre-processing Workflow for LLMs

Directly uploading multi-megabyte PDFs to LLM context windows causes massive token consumption, high latency, and degraded reasoning. This workflow pre-processes PDFs into lean Markdown.

## Pipeline Steps
1. **Text & Table Extraction**: Parse text layers using `pypdf`, `pdfplumber`, or `marker-pdf`.
2. **Table Normalization**: Convert PDF tables into clean GitHub Flavored Markdown tables.
3. **OCR on Visual Pages**: Run local Tesseract or lightweight vision model only on scanned pages/diagrams.
4. **Token Reduction**: Strip headers, footers, page numbers, and redundant whitespace.

## Python Extractor Recipe
```python
import pdfplumber

def pdf_to_clean_markdown(pdf_path: str) -> str:
    md_output = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                md_output.append(f"<!-- Page {i+1} -->\n{text.strip()}")
    return "\n\n".join(md_output)
```
