#!/usr/bin/env python3
"""Preflight: extract a sub-PDF of the requested pages for Doc2X submission.

This is a safety wrapper around Doc2X OCR. It extracts only the pages you
actually need into a small sub-PDF, and guards against accidentally uploading
most of a large source PDF.

Known limitation: this script is advisory, not a runtime gate. The model can
still bypass it by calling doc2x_parse_pdf_submit() directly on the full PDF.
The Hard Contract in SKILL.md forbids this, but there is no code-level interlock
preventing it.

Usage:
    py -3 scripts/extract_and_submit.py \
        --pdf "C:/path/source.pdf" \
        --pages 6-36 \
        --output-dir "C:/path/product/job/"

    # Small PDFs (<=10 pages) may be submitted in full:
    py -3 scripts/extract_and_submit.py --pdf small.pdf --output-dir out/ --allow-full-pdf

    # Override the ratio guard once you have confirmed the scope:
    py -3 scripts/extract_and_submit.py --pdf big.pdf --pages 1-300 --output-dir out/ --confirm-large

Outputs:
    <output-dir>/doc2x/source-pages.pdf        (the sub-PDF to submit)
    <output-dir>/doc2x/extract-manifest.json   (audit metadata)

Dependencies:
    pip install PyMuPDF  (imported as fitz)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Safety threshold: refuse to silently extract more than 60% of the source.
LARGE_RATIO_THRESHOLD = 0.6
# Below this page count, --pages may be omitted when --allow-full-pdf is set.
SMALL_PDF_PAGE_CAP = 10


def parse_page_range(spec: str) -> list[int]:
    """Parse a 1-indexed page range string into sorted, deduplicated 0-indexed page numbers.

    Supported forms (whitespace tolerant):
        "7"            -> [6]
        "6-36"         -> [5, 6, ..., 35]
        "1-3,7,10-12"  -> [0, 1, 2, 6, 9, 10, 11]
        " 1 , 2 "      -> [0, 1]

    Raises:
        ValueError: if the spec is empty, blank, or contains a token that
            cannot be interpreted as a page number or range. Page numbers must
            be >= 1. Out-of-range pages (beyond a document's page count) are
            NOT rejected here -- callers filter those against the document.
    """
    if spec is None:
        raise ValueError("Empty page range")
    if not spec.strip():
        raise ValueError("Empty page range")

    pages: set[int] = set()
    saw_token = False

    for chunk in spec.split(","):
        token = chunk.strip()
        if not token:
            continue
        saw_token = True

        if "-" in token:
            parts = token.split("-", 1)
            left = parts[0].strip()
            right = parts[1].strip()
            if left == "" or right == "":
                raise ValueError(f"Invalid page range token: {token!r}")
            try:
                start = int(left)
                end = int(right)
            except ValueError as exc:
                raise ValueError(f"Invalid page range token: {token!r}") from exc
            if start < 1 or end < 1:
                raise ValueError(f"Page numbers must be >= 1: {token!r}")
            if start > end:
                start, end = end, start
            for p in range(start, end + 1):
                pages.add(p - 1)
        else:
            try:
                p = int(token)
            except ValueError as exc:
                raise ValueError(f"Invalid page number: {token!r}") from exc
            if p < 1:
                raise ValueError(f"Page numbers must be >= 1: {token!r}")
            pages.add(p - 1)

    if not saw_token:
        raise ValueError("Empty page range")
    return sorted(pages)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--pdf", required=True, help="Source PDF file path")
    parser.add_argument(
        "--pages",
        help='1-based page selection, e.g. "6-36" or "1-3,7,10-12". '
        "Required for PDFs with more than 10 pages.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for the sub-PDF and manifest",
    )
    parser.add_argument(
        "--confirm-large",
        action="store_true",
        help="Proceed even when the requested range exceeds 60%% of the PDF.",
    )
    parser.add_argument(
        "--allow-full-pdf",
        action="store_true",
        help="Allow omitting --pages for small PDFs (<=10 pages).",
    )
    return parser


def _select_pages(args: argparse.Namespace, page_count: int) -> list[int]:
    """Resolve the list of 0-indexed pages to extract, applying all guards.

    Handles:
      * missing --pages guard (small-PDF full submission)
      * invalid range errors
      * out-of-range warnings + skip

    Exits the process (via SystemExit) on hard failures; returns the validated
    page list on success.
    """
    if not args.pages:
        if page_count <= SMALL_PDF_PAGE_CAP and args.allow_full_pdf:
            return list(range(page_count))
        print(
            "ERROR: --pages is required for PDFs with more than 10 pages. "
            "Use --allow-full-pdf for small PDFs.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        requested = parse_page_range(args.pages)
    except ValueError as exc:
        print(f"ERROR: Invalid --pages value {args.pages!r}: {exc}", file=sys.stderr)
        sys.exit(1)

    valid = [p for p in requested if 0 <= p < page_count]
    skipped = [p for p in requested if p >= page_count]
    if skipped:
        human = ", ".join(str(p + 1) for p in skipped)
        print(
            f"WARNING: {len(skipped)} page(s) out of range "
            f"(source has {page_count} pages); skipping: {human}",
            file=sys.stderr,
        )

    if not valid:
        print(
            "ERROR: No valid pages to extract after range filtering.",
            file=sys.stderr,
        )
        sys.exit(1)
    return valid


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    if not pdf_path.exists():
        print(f"ERROR: Source PDF not found: {pdf_path}", file=sys.stderr)
        return 1

    try:
        import fitz  # type: ignore  # PyMuPDF -- imported lazily so --help works without it
    except ImportError:
        print(
            "ERROR: PyMuPDF is not installed. Install it with:\n"
            "    pip install PyMuPDF",
            file=sys.stderr,
        )
        return 1

    doc = fitz.open(str(pdf_path))
    try:
        page_count = doc.page_count

        selected = _select_pages(args, page_count)

        ratio = len(selected) / page_count if page_count else 1.0
        # The ratio guard prevents ACCIDENTAL near-full uploads of an explicit
        # page range. When the user reached here via --allow-full-pdf (signaled
        # by args.pages being empty), they have already explicitly opted into
        # uploading the whole small PDF, so the guard does not apply.
        if (
            args.pages
            and ratio > LARGE_RATIO_THRESHOLD
            and not args.confirm_large
        ):
            print(
                "ERROR: Requesting "
                f"{len(selected)}/{page_count} pages ({ratio:.0%}). "
                "This looks like you might be uploading most of the PDF. "
                "Pass --confirm-large to proceed.",
                file=sys.stderr,
            )
            return 1

        doc2x_dir = output_dir / "doc2x"
        doc2x_dir.mkdir(parents=True, exist_ok=True)
        sub_pdf_path = doc2x_dir / "source-pages.pdf"

        new_doc = fitz.open()
        try:
            for zero_based in selected:
                new_doc.insert_pdf(doc, from_page=zero_based, to_page=zero_based)
            new_doc.save(str(sub_pdf_path))
        finally:
            new_doc.close()

        manifest = {
            "source_pdf": str(pdf_path),
            "source_page_count": page_count,
            "requested_pages": args.pages if args.pages else "all",
            "extracted_page_count": len(selected),
            "extracted_pdf": "doc2x/source-pages.pdf",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        manifest_path = doc2x_dir / "extract-manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    finally:
        doc.close()

    page_label = args.pages if args.pages else "all"
    print(
        f"OK: Extracted {len(selected)} pages ({page_label}) "
        f"from {page_count}-page PDF."
    )
    print(f"Sub-PDF: {sub_pdf_path}")
    print(f"Manifest: {manifest_path}")
    print()
    print("Next step: Submit the sub-PDF to Doc2X:")
    print(
        f'  doc2x_parse_pdf_submit(pdf_path="{sub_pdf_path}")'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
