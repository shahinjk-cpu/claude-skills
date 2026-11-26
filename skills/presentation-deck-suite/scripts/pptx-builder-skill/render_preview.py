"""
Renders a .pptx to one PNG per slide via LibreOffice + PyMuPDF, so the deck
can actually be looked at (with the Read tool) before calling it done.

verify_pptx.py catches file corruption. It cannot catch a deck that opens
perfectly cleanly but has content shifted, overlapping, or overflowing its
box — that class of bug only shows up by looking at the rendered slides.
This happened once (a fixed-height Playwright viewport caused icon
screenshots to auto-scroll the page, shifting every element measured
afterward on that slide) and was only caught by rendering and looking.

Usage:
    python render_preview.py <file.pptx> <output_dir>

Requires LibreOffice (soffice) — install with:
    winget install TheDocumentFoundation.LibreOffice
and the `pymupdf` package — install with:
    pip install pymupdf
"""
import sys
import os
import shutil
import subprocess

SOFFICE_CANDIDATES = [
    "soffice",
    r"C:\Program Files\LibreOffice\program\soffice.exe",
]


def find_soffice():
    for candidate in SOFFICE_CANDIDATES:
        if os.path.sep in candidate or ":" in candidate:
            if os.path.exists(candidate):
                return candidate
        else:
            found = shutil.which(candidate)
            if found:
                return found
    raise FileNotFoundError(
        "LibreOffice (soffice) not found. Install it with:\n"
        "  winget install TheDocumentFoundation.LibreOffice\n"
        "It's required to render a visual preview of the generated pptx."
    )


def main():
    pptx_path, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    soffice = find_soffice()

    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, pptx_path],
        check=True, capture_output=True,
    )
    pdf_path = os.path.join(out_dir, os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf")

    import fitz
    doc = fitz.open(pdf_path)
    out_paths = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        out_png = os.path.join(out_dir, f"slide{i + 1}.png")
        pix.save(out_png)
        out_paths.append(out_png)
    doc.close()

    print(f"Rendered {len(out_paths)} slide(s) to {out_dir}")
    for p in out_paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
