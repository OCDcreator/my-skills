#!/usr/bin/env python3
"""Render a handout.html to a print-faithful A4 PDF + optional full-page screenshot.

Waits for the local pagination script (data-handout-ready="true"), math typesetting
(MathJax or KaTeX), and web-font loading before exporting. Uses Playwright's
chromium headless to produce deterministic results.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="Path to the input handout.html")
    parser.add_argument("--pdf", required=True, help="Output PDF path")
    parser.add_argument("--screenshot", default=None, help="Optional output PNG screenshot path")
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=1200,
        help="Extra grace period in milliseconds after math/fonts are ready (default: 1200)",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=794,
        help="Viewport width in pixels (A4 at 96 DPI ≈ 794; default: 794)",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1123,
        help="Viewport height in pixels (default: 1123)",
    )
    parser.add_argument(
        "--screenshot-scale",
        type=float,
        default=3.0,
        help=(
            "Rasterization scale for the PNG screenshot, as a multiple of the "
            "viewport (default: 3.0 ≈ A4 @ 288dpi, ~2382x3369px). Higher is "
            "sharper but larger. This does NOT affect the PDF: page.pdf() uses "
            "the print path and ignores device_scale_factor, so the PDF stays "
            "vector regardless of this value. Use 1.0 for an old-style ~96dpi "
            "screenshot."
        ),
    )
    return parser


def _resolve_output_parent(pdf_path: Path) -> None:
    """Ensure the parent directory exists for the PDF output."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)


def _load_pdf_bookmarks(page) -> list[dict[str, object]]:
    payload = page.evaluate(
        """
        () => {
          const root = document.getElementById('handout-print-root');
          if (!root) return [];
          try {
            const raw = root.dataset.pdfBookmarks || '[]';
            const entries = JSON.parse(raw);
            return Array.isArray(entries) ? entries : [];
          } catch (_err) {
            return [];
          }
        }
        """
    )
    entries: list[dict[str, object]] = []
    for entry in payload or []:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        if not title:
            continue
        try:
            page_number = int(entry.get("page", 0))
        except Exception:
            continue
        try:
            level = int(entry.get("level", 2))
        except Exception:
            level = 2
        entries.append({"title": title, "page": page_number, "level": level})
    return entries


def _dedupe_bookmarks(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    deduped: list[dict[str, object]] = []
    seen: set[tuple[str, int, int]] = set()
    for entry in entries:
        key = (
            str(entry["title"]),
            int(entry["page"]),
            int(entry["level"]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _normalize_bookmark_levels(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    previous_level = 1
    for entry in entries:
        raw_level = max(1, int(entry.get("level", 2)))
        level = raw_level
        if level > previous_level + 1:
            level = previous_level + 1
        normalized.append(
            {
                "title": str(entry["title"]),
                "page": int(entry["page"]),
                "level": level,
            }
        )
        previous_level = level
    return normalized


def _apply_pdf_bookmarks(pdf_path: Path, bookmarks: list[dict[str, object]]) -> None:
    if not bookmarks:
        return
    try:
        import fitz  # noqa: WPS433
    except ImportError:
        print("NOTE: PyMuPDF not installed; skipping PDF bookmarks.")
        return

    doc = fitz.open(pdf_path)
    toc: list[list[object]] = [[1, "封面", 1]]
    page_count = doc.page_count

    for entry in _normalize_bookmark_levels(bookmarks):
        page_number = int(entry["page"])
        if page_number < 1:
            continue
        page_number = min(page_number, page_count)
        level = max(1, int(entry["level"]))
        title = str(entry["title"]).strip()
        if not title:
            continue
        toc.append([level, title, page_number])

    doc.set_toc(toc)
    doc.save(pdf_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()

    check = fitz.open(pdf_path)
    actual_len = len(check.get_toc())
    check.close()
    if actual_len == len(toc):
        return

    # Fallback: some PDFs do not reliably persist a full TOC via incremental
    # save. Reopen, reapply, and write a fresh replacement file.
    retry = fitz.open(pdf_path)
    retry.set_toc(toc)
    temp_path = pdf_path.with_name(f"{pdf_path.stem}.bookmarks{pdf_path.suffix}")
    retry.save(temp_path)
    retry.close()
    temp_path.replace(pdf_path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")

    pdf_path = Path(args.pdf).expanduser().resolve()
    screenshot_path = (
        Path(args.screenshot).expanduser().resolve() if args.screenshot else None
    )

    _resolve_output_parent(pdf_path)

    # Ensure sibling modules (handout_browser.py in the same scripts/ dir) are
    # importable regardless of how this script is launched (direct run,
    # subprocess, or importlib from tests/).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from handout_browser import open_handout

    with open_handout(
        html_path,
        viewport=(args.viewport_width, args.viewport_height),
        device_scale_factor=args.screenshot_scale,
        strict_ready=True,
        ready_timeout_ms=60_000,
        fonts_timeout_ms=60_000,
        settle_ms=args.wait_ms,
    ) as (page, _errors):
        bookmarks = _dedupe_bookmarks(_load_pdf_bookmarks(page))

        # Full-page screenshot (optional).
        if screenshot_path:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(
                f"screenshot -> {screenshot_path} "
                f"({screenshot_path.stat().st_size} bytes)"
            )

        # Print to A4 PDF honoring the in-page @page rules (margin: 0).
        # Locked-file fallback so the user always gets a refreshed PDF even
        # when the current file is open in a viewer.
        candidates = [
            pdf_path,
            pdf_path.with_name(f"{pdf_path.stem}-updated{pdf_path.suffix}"),
            pdf_path.with_name(
                f"{pdf_path.stem}-{time.strftime('%H%M%S')}{pdf_path.suffix}"
            ),
        ]
        out_path: Path | None = None
        last_err: Exception | None = None
        # Playwright may surface a raw PermissionError or wrap it in its own
        # error type with messages like "EPERM"/"Access is denied"/"process
        # cannot access". Treat any of those as a locked target and try the
        # next candidate; re-raise anything else (real render failures).
        _LOCK_TOKENS = ("permission", "eperm", "ebusy", "access is denied", "process cannot access")
        for cand in candidates:
            try:
                page.pdf(
                    path=str(cand),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
                out_path = cand
                break
            except Exception as exc:  # noqa: BLE001 - filtered by message below
                if not any(token in str(exc).lower() for token in _LOCK_TOKENS):
                    raise
                last_err = exc
                continue

        if out_path is None:
            raise SystemExit(f"All PDF target names were locked: {last_err}")

        _apply_pdf_bookmarks(out_path, bookmarks)
        print(f"pdf -> {out_path} ({out_path.stat().st_size} bytes)")
        if out_path != pdf_path:
            print(
                "NOTE: close any open PDF viewers, then re-run to finalize "
                f"the canonical path ({pdf_path.name})."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
