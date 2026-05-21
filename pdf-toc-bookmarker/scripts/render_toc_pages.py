#!/usr/bin/env python3
"""Render PDF table-of-contents pages to PNG images."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF is required. Install with: python -m pip install pymupdf") from exc


def parse_page_range(value: str) -> list[int]:
    pages: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                raise ValueError(f"Invalid descending range: {part}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
    if not pages:
        raise ValueError("No pages specified")
    if any(page < 1 for page in pages):
        raise ValueError("PDF pages are 1-based and must be positive")
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Input PDF path")
    parser.add_argument("--pages", required=True, help="TOC PDF pages, e.g. 11-16 or 11,13-15")
    parser.add_argument("--out", required=True, help="Output directory for PNG files")
    parser.add_argument("--zoom", type=float, default=2.5, help="Render zoom factor")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    out_dir = Path(args.out)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    pages = parse_page_range(args.pages)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    try:
        for page_no in pages:
            if page_no > doc.page_count:
                raise SystemExit(f"Page {page_no} is outside PDF page count {doc.page_count}")
            page = doc[page_no - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(args.zoom, args.zoom), alpha=False)
            out_path = out_dir / f"toc_page_{page_no:04d}.png"
            pix.save(out_path)
            print(out_path)
        print(f"rendered={len(pages)} pages={doc.page_count}")
    finally:
        doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
