#!/usr/bin/env python3
"""Convert a filled CV or letter HTML to PDF in <workspace>/<company-slug>/, check its page count and make a preview.

    python3 render_pdf.py --html /scratch/cv.html --workspace WS --company "Acme Inc" --max-pages 2

Prints the PDF path, its page count and the preview PNG (written next to the HTML, never in the workspace).
Refuses HTML that loads remote resources (img/link/script/@import/url() over the network): LibreOffice would fetch them.
"""
import argparse, glob, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import private_files  # noqa: E402

REMOTE = re.compile(r"""<(?:img|link|script|iframe|object|embed)\b[^>]*\b(?:src|href|data)\s*=\s*["']?\s*(?:https?:)?//|@import|url\(\s*["']?\s*(?:https?:)?//""", re.I)
SOFFICE = ["soffice", "libreoffice", "/Applications/LibreOffice.app/Contents/MacOS/soffice",
           r"C:\Program Files\LibreOffice\program\soffice.exe"]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60] or "company"


def soffice():
    for c in SOFFICE:
        p = shutil.which(c) or (c if os.path.isfile(c) else None)
        if p:
            return p
    raise SystemExit("LibreOffice not found: install it (Debian/Ubuntu: apt install libreoffice-writer; macOS: brew install --cask libreoffice; "
                     "Windows: winget install TheDocumentFoundation.LibreOffice)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--company", required=True, help="company name; the folder is its slug")
    ap.add_argument("--max-pages", type=int, default=2, help="2 for a CV, 1 for a letter")
    a = ap.parse_args()
    private_files()
    with open(a.html, encoding="utf-8") as fh:
        m = REMOTE.search(fh.read())
    if m:
        raise SystemExit(f"remote resource in {a.html}: {m.group(0)[:80]!r}. Inline it or remove it (posting text must never add markup).")
    out = os.path.join(os.path.abspath(os.path.expanduser(a.workspace)), slug(a.company))
    os.makedirs(out, exist_ok=True)
    r = subprocess.run([soffice(), "--headless", "--convert-to", "pdf:writer_web_pdf_Export", "--outdir", out, os.path.abspath(a.html)],
                       capture_output=True, text=True, timeout=180)  # absolute path: never read as an option
    pdf = os.path.join(out, os.path.splitext(os.path.basename(a.html))[0] + ".pdf")
    if not os.path.exists(pdf):
        raise SystemExit(f"conversion failed: {r.stderr.strip() or r.stdout.strip()}")
    pages = None
    if shutil.which("pdfinfo"):
        info = subprocess.run(["pdfinfo", "--", pdf], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", info)
        pages = int(m.group(1)) if m else None
    preview = os.path.splitext(a.html)[0] + "-preview"
    if shutil.which("pdftoppm"):
        subprocess.run(["pdftoppm", "-r", "50", "-png", "--", pdf, preview], capture_output=True)
    print("pdf:", pdf)
    print("pages:", pages if pages is not None else "unknown (install poppler for pdfinfo)",
          f"→ OVER the {a.max_pages}-page limit: shorten and re-run" if pages and pages > a.max_pages else "")
    print("preview:", ", ".join(sorted(glob.glob(preview + "*.png"))) or "none (install poppler for pdftoppm)")


if __name__ == "__main__":
    main()
