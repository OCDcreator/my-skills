#!/usr/bin/env python3
"""Extract specified PDF pages as image files for proofreading verification.

Usage:
    py -3 scripts/extract_pdf_pages.py --pdf "C:/path/doc.pdf" --out-dir "C:/path/pdf-pages"
    py -3 scripts/extract_pdf_pages.py --pdf "doc.pdf" --out-dir "pdf-pages" --pages "1-3,7" --dpi 200 --format png

Outputs:
    <out-dir>/page-001.png (one image per selected page)
    <out-dir>/manifest.json  (rendering metadata)
    Prints manifest path on success.

Dependencies:
    pip install PyMuPDF  (imported as fitz)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_page_spec(spec: str | None, page_count: int) -> list[int]:
    """Parse a user-friendly page spec into 0-based page indices.

    Supported formats:
        "1-3,7"  -> pages 1,2,3,7
        "5"      -> page 5
        "1-3"    -> pages 1,2,3
        None     -> all pages
    """
    if not spec:
        return list(range(page_count))

    pages: set[int] = set()
    for chunk in spec.split(","):
        item = chunk.strip()
        if not item:
            continue
        if "-" in item:
            parts = item.split("-", 1)
            start = int(parts[0])
            end = int(parts[1])
            if start > end:
                start, end = end, start
            for p in range(start, end + 1):
                if 1 <= p <= page_count:
                    pages.add(p - 1)
        else:
            p = int(item)
            if 1 <= p <= page_count:
                pages.add(p - 1)
    return sorted(pages)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pdf", required=True, help="Input PDF file path")
    parser.add_argument("--out-dir", required=True, help="Output directory for rendered page images")
    parser.add_argument(
        "--pages",
        help='1-based page selection, e.g. "1-3,7" (default: all pages)',
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Render DPI (default: 200). Higher = sharper but larger files.",
    )
    parser.add_argument(
        "--format",
        choices=["png", "jpg"],
        default="png",
        help="Output image format (default: png). Use jpg for smaller files.",
    )
    parser.add_argument(
        "--jpg-quality",
        type=int,
        default=90,
        help="JPEG quality 1-100 (default: 90, only used when --format=jpg)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", flush=True)
        return 1

    import fitz  # PyMuPDF -- imported here so --help works without it

    out_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(str(pdf_path))
    selected_pages = parse_page_spec(args.pages, document.page_count)

    if not selected_pages:
        print(
            f"WARNING: No valid pages selected (spec={args.pages!r}, "
            f"total pages={document.page_count}).",
            flush=True,
        )
        return 0

    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    ext = args.format
    img_kw: dict[str, object] = {}
    if ext == "jpg":
        img_kw["jpeg_quality"] = args.jpg_quality

    rendered_pages: list[dict[str, object]] = []
    for zero_based in selected_pages:
        page = document.load_page(zero_based)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        page_num = zero_based + 1
        filename = f"page-{page_num:03d}.{ext}"
        out_path = out_dir / filename
        pixmap.save(str(out_path), **img_kw)
        rendered_pages.append({
            "page_number": page_num,
            "image_path": str(out_path),
            "width": pixmap.width,
            "height": pixmap.height,
            "dpi": args.dpi,
            "format": ext,
        })

    manifest = {
        "source_pdf": str(pdf_path),
        "total_page_count": document.page_count,
        "rendered_page_count": len(rendered_pages),
        "dpi": args.dpi,
        "format": ext,
        "pages": rendered_pages,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(str(manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
