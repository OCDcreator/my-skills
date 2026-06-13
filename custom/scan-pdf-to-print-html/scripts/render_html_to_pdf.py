#!/usr/bin/env python3
"""Render a handout.html to a print-faithful A4 PDF + optional full-page screenshot.

Waits for the local pagination script (data-handout-ready="true"), math typesetting
(MathJax or KaTeX), and web-font loading before exporting. Uses Playwright's
chromium headless to produce deterministic results.
"""

from __future__ import annotations

import argparse
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
    return parser


def _resolve_output_parent(pdf_path: Path) -> None:
    """Ensure the parent directory exists for the PDF output."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)


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

    try:
        from playwright.sync_api import sync_playwright  # noqa: E402
    except ImportError as exc:
        raise SystemExit(
            f"Playwright is required but not installed. Install with: pip install playwright && playwright install chromium\n"
            f"Details: {exc}"
        ) from exc

    url = html_path.as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": args.viewport_width, "height": args.viewport_height}
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle")

        # Engine-agnostic math wait — works for MathJax tex-svg and KaTeX.
        page.wait_for_function(
            "document.documentElement.dataset.handoutReady === 'true'",
            timeout=60_000,
        )
        page.wait_for_function(
            "document.fonts && document.fonts.status === 'loaded'",
            timeout=60_000,
        )
        page.wait_for_timeout(args.wait_ms)

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

        print(f"pdf -> {out_path} ({out_path.stat().st_size} bytes)")
        if out_path != pdf_path:
            print(
                "NOTE: close any open PDF viewers, then re-run to finalize "
                f"the canonical path ({pdf_path.name})."
            )

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
