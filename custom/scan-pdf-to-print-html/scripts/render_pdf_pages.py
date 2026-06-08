#!/usr/bin/env python3
"""Render PDF pages to image files with a simple JSON manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def parse_page_spec(spec: str | None, page_count: int) -> list[int]:
    if not spec:
        return list(range(page_count))
    pages: set[int] = set()
    for chunk in spec.split(","):
        item = chunk.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                start, end = end, start
            for page_number in range(start, end + 1):
                if 1 <= page_number <= page_count:
                    pages.add(page_number - 1)
            continue
        page_number = int(item)
        if 1 <= page_number <= page_count:
            pages.add(page_number - 1)
    return sorted(pages)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Input PDF path")
    parser.add_argument("--out-dir", required=True, help="Directory for rendered pages")
    parser.add_argument("--dpi", type=int, default=220, help="Render DPI (default: 220)")
    parser.add_argument("--pages", help='1-based page selection, for example "1-3,7"')
    parser.add_argument(
        "--manifest",
        help="Optional manifest path. Defaults to <out-dir>/manifest.json",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else out_dir / "manifest.json"

    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    selected_pages = parse_page_spec(args.pages, document.page_count)
    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    rendered_pages: list[dict[str, object]] = []
    for zero_based_page in selected_pages:
        page = document.load_page(zero_based_page)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        page_name = f"page-{zero_based_page + 1:03d}.png"
        out_path = out_dir / page_name
        pixmap.save(out_path)
        rendered_pages.append(
            {
                "page_number": zero_based_page + 1,
                "image_path": str(out_path),
                "width": pixmap.width,
                "height": pixmap.height,
                "dpi": args.dpi,
            }
        )

    manifest = {
        "source_pdf": str(pdf_path),
        "page_count": document.page_count,
        "rendered_page_count": len(rendered_pages),
        "dpi": args.dpi,
        "pages": rendered_pages,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
