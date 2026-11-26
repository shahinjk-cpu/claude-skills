---
name: epub-ebook-publisher
description: >-
  Converts markdown documents, research notes, dissertations, and long chat syntheses
  into professionally formatted EPUB ebooks and publication-ready documents. Inspired by
  smerchek/claude-epub-skill. Use when compiling books, reports, or offline reading files.
---

# EPUB eBook & Publication Publisher

Inspired by `smerchek/claude-epub-skill`.

## 1. Publication Workflow
1. **Compilation & Metadata**:
   - Extract title, author, description, language (`az`, `en`, `ru`), ISBN/UUID, and publication date into standard EPUB OPF package metadata.
2. **Table of Contents & Navigation**:
   - Generate multi-level Table of Contents (`nav.xhtml` and `toc.ncx`) from Markdown `#`, `##`, `###` headers.
3. **Typography & E-Reader Styling**:
   - Include clean CSS optimized for Kindle, Apple Books, and Kobo e-readers (responsive typography, hyphenation, clear chapter dividers, and code block wrapping).
4. **Automated Conversion**:
   - Use Python `ebooklib` or `pandoc -o book.epub --toc --metadata title="..." input.md` to produce valid, error-free EPUB3 binaries.
