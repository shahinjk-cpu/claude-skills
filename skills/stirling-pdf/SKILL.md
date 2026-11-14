---
name: stirling-pdf
description: >
  Locally hosted one-stop PDF editing and manipulation tool suite. Split, merge, compress, OCR, convert, watermark, sanitize, and extract PDF content via Stirling-PDF REST API.
metadata:
  version: "1.0.0"
  category: content_media
  triggers: stirling-pdf, pdf edit, ocr pdf, merge pdf, compress pdf, sanitize pdf
---

# Stirling-PDF — Powerful Local PDF Suite

Orchestrates local PDF processing using self-hosted Stirling-PDF. Performs OCR, conversion, compression, merging, splitting, watermarking, and redaction via REST API without sending data to third-party clouds.

## Core Operations
- **Merge & Split**: Combine multiple PDFs or extract specific page ranges.
- **OCR (Tesseract)**: Convert scanned image PDFs into searchable text PDFs with multi-language support.
- **Compression**: Reduce PDF file size with adjustable DPI and Ghostscript optimization.
- **Conversion**: PDF to/from Word, HTML, Images (PNG/JPG), and Markdown.
- **Sanitization & Security**: Strip metadata, flatten forms, remove javascript, and apply AES encryption.

## API Integration

### Docker Deployment
```bash
docker run -d -p 8080:8080 --name stirling-pdf frooodle/s-pdf:latest
```

### Python API Example (Merge PDFs)
```python
import requests

def merge_pdfs(pdf_paths, output_path, base_url="http://localhost:8080"):
    url = f"{base_url}/api/v1/general/merge-pdfs"
    files = [('fileInput', open(p, 'rb')) for p in pdf_paths]
    resp = requests.post(url, files=files)
    if resp.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(resp.content)
        return True
    return False
```
