---
name: office-document-master
description: >-
  Creates, edits, converts, extracts, and automates local Office and document files
  including Word (.docx), PDF (.pdf), Excel (.xlsx, .csv), PowerPoint (.pptx), and
  Markdown/LaTeX. Use whenever the user asks to generate reports, manipulate PDFs,
  build spreadsheets with formulas/charts, create slide decks, or batch-process files.
---

# Office & Local Document Master (.docx, .pdf, .xlsx, .pptx)

Inspired by `anthropics/skills` (`docx`, `pdf`, `xlsx`, `pptx`), this skill provides deterministic workflows for reading, generating, converting, and batch-processing local documents.

## 1. Word Documents (`.docx`)
- **Tooling**: Use Python `python-docx` (or `pandoc` for Markdown/LaTeX conversions).
- **Best Practices**:
  - Define document styles (`Heading 1`, `Heading 2`, `Normal`, `List Bullet`) at the start rather than hardcoding inline fonts on every run.
  - Set explicit page margins, header/footer page numbers, and table borders (`Table Grid`).
  - When editing an existing `.docx`, iterate through `doc.paragraphs` and `doc.tables` preserving existing run formatting (`run.bold`, `run.italic`, `run.font`) whenever replacing text placeholders.

## 2. PDF Toolkit (`.pdf`)
- **Reading / Extraction**:
  - Use `pypdf` / `pymupdf` (`fitz`) or `pdfplumber` (best for extracting structured tables from PDFs).
  - Never dump a 100-page PDF into chat context; write a quick script to search headings/keywords or extract specific page ranges first.
- **Creating / Generating PDFs**:
  - Use `reportlab` (Platypus `SimpleDocTemplate`, `Paragraph`, `Table`, `Spacer`, `PageBreak`) or HTML-to-PDF via `weasyprint` / Playwright `page.pdf()` for pixel-perfect styled reports with Unicode/Azerbaijani character support (`ə, ı, ö, ü, ç, ş, ğ`).
  - **CRITICAL Font Rule for Azerbaijani / Unicode**: In `reportlab`, default `Helvetica` does NOT render `ə`, `ş`, `ğ`, `ı`, `İ`. Always register a Unicode TTF font (such as `C:\Windows\Fonts\arial.ttf` or `segoeui.ttf` via `pdfmetrics.registerFont(TTFont('Arial', ...))`) when generating PDFs in Azerbaijani or Turkish.

## 3. Excel Spreadsheets (`.xlsx` & `.csv`)
- **Tooling**: Use `openpyxl` for `.xlsx` creation/styling and `pandas` for heavy data transformations.
- **Best Practices**:
  - **Use Native Excel Formulas**: Write real formulas (`=SUM(B2:B50)`, `=AVERAGE(...)`, `=VLOOKUP(...)`, `=XLOOKUP(...)`) into cells instead of hardcoding static Python-calculated totals so the user's spreadsheet remains live and editable.
  - Apply professional formatting: freeze the header row (`ws.freeze_panes = 'A2'`), auto-fit column widths based on max cell length + padding, format currency/percentage cells (`#,##0.00`, `0.0%`), and style header rows with a clean fill and bold text.

## 4. PowerPoint Presentations (`.pptx`)
- **Tooling**: Use `python-pptx` for local `.pptx` files (or the `gslides` skill if working on Google Slides).
- **Best Practices**:
  - Set widescreen 16:9 slide dimensions (`13.333` x `7.5` inches).
  - Follow the **1-Idea-Per-Slide** rule: a clear action title, max 4–5 concise bullet points or a 2-column visual comparison/chart, and speaker notes in `slide.notes_slide`.
  - Verify text-box bounds so text never overflows or overlaps slide footers.

## 5. Safe Batch File Operations
- Before renaming, moving, or overwriting >5 user files in a folder, print a dry-run preview table (`Original -> Target`) and verify no files will be accidentally overwritten.
