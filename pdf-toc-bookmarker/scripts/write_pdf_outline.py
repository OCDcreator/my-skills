#!/usr/bin/env python3
"""Write PDF bookmarks/outline from TOC JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyMuPDF is required. Install with: python -m pip install pymupdf") from exc


def normalize_level(title: str, raw_level: Any) -> int:
    text = title.strip()
    if re.match(r"^第\s*\d+\s*章", text):
        return 1
    if re.match(r"^第[一二三四五六七八九十百]+\s*节", text):
        return 2
    if re.match(r"^[一二三四五六七八九十百]+、", text):
        return 3
    if re.match(r"^(考点\s*\d+|问题[一二三四五六七八九十百]+|\d+[.．、]|[①②③④⑤⑥⑦⑧⑨⑩])", text):
        return 4
    try:
        return min(max(int(raw_level), 1), 4)
    except (TypeError, ValueError):
        return 1


def default_output_path(pdf_path: Path) -> Path:
    return pdf_path.with_name(f"{pdf_path.stem}.with-toc{pdf_path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Input PDF path")
    parser.add_argument("--toc-json", required=True, help="JSON array with title/level/page")
    parser.add_argument(
        "--printed-page-1-pdf-page",
        required=True,
        type=int,
        help="Actual PDF page where printed page 1 begins",
    )
    parser.add_argument(
        "--toc-page",
        type=int,
        help="Actual PDF page where the table of contents begins. Adds a top-level TOC bookmark.",
    )
    parser.add_argument(
        "--toc-title",
        default="目录",
        help='Title for the table-of-contents bookmark. Defaults to "目录".',
    )
    parser.add_argument("--out", help="Output PDF path. Defaults to <input>.with-toc.pdf")
    parser.add_argument("--keep-raw-levels", action="store_true", help="Do not normalize levels by title pattern")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    json_path = Path(args.toc_json)
    out_path = Path(args.out) if args.out else default_output_path(pdf_path)
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    if not json_path.exists():
        raise SystemExit(f"TOC JSON not found: {json_path}")
    if out_path.resolve() == pdf_path.resolve():
        raise SystemExit("Refusing to overwrite the input PDF")

    items = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        raise SystemExit("TOC JSON must be a non-empty array")

    offset = args.printed_page_1_pdf_page - 1
    doc = fitz.open(pdf_path)
    outline: list[list[Any]] = []
    previous_level = 1
    previous_printed_page: int | None = None
    uncertain_titles: list[tuple[int, str]] = []
    decreasing_pages: list[tuple[int, int, int, str]] = []
    try:
        if args.toc_page is not None:
            if not (1 <= args.toc_page <= doc.page_count):
                raise SystemExit(
                    f"TOC bookmark target out of range: toc_page={args.toc_page}, page_count={doc.page_count}"
                )
            toc_title = str(args.toc_title).strip()
            if not toc_title:
                raise SystemExit("TOC bookmark title must not be empty")
            outline.append([1, toc_title, args.toc_page])

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise SystemExit(f"Item {index} is not an object")
            title = str(item.get("title", "")).strip()
            if not title:
                raise SystemExit(f"Item {index} has empty title")
            printed_page = int(item["page"])
            if "[?]" in title:
                uncertain_titles.append((index, title))
            if previous_printed_page is not None and printed_page < previous_printed_page:
                decreasing_pages.append((index, previous_printed_page, printed_page, title))
            previous_printed_page = printed_page
            target_page = printed_page + offset
            if not (1 <= target_page <= doc.page_count):
                raise SystemExit(
                    f"Bookmark target out of range at item {index}: "
                    f"title={title!r}, printed_page={printed_page}, pdf_page={target_page}, page_count={doc.page_count}"
                )

            if args.keep_raw_levels:
                level = min(max(int(item.get("level", 1)), 1), 9)
            else:
                level = normalize_level(title, item.get("level", 1))

            if len(outline) == 0:
                level = 1
            elif level > previous_level + 1:
                level = previous_level + 1
            outline.append([level, title, target_page])
            previous_level = level

        doc.set_toc(outline)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out_path, garbage=4, deflate=True)
    finally:
        doc.close()

    verify = fitz.open(out_path)
    try:
        written_toc = verify.get_toc()
        print(f"output={out_path}")
        print(f"pages={verify.page_count}")
        print(f"bookmarks={len(written_toc)}")
        print(f"offset={offset}")
        print(f"uncertain_titles={len(uncertain_titles)}")
        print(f"decreasing_printed_pages={len(decreasing_pages)}")
        for index, title in uncertain_titles[:10]:
            print(f"warning_uncertain item={index} title={title}")
        for index, prev_page, page, title in decreasing_pages[:10]:
            print(f"warning_decreasing_page item={index} prev={prev_page} page={page} title={title}")
        if written_toc:
            print(f"first={written_toc[0]}")
            print(f"last={written_toc[-1]}")
        if len(written_toc) != len(outline):
            raise SystemExit(f"Expected {len(outline)} bookmarks, got {len(written_toc)}")
    finally:
        verify.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
