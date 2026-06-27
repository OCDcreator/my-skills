#!/usr/bin/env python3
"""Shared Playwright handout-rendering context for scan-pdf-to-print-html.

WHY THIS EXISTS
---------------
Three scripts (render_html_to_pdf.py, validate_rendered_handout_contract.py,
validate_sheet_bottom_margin.py) each used to open the built handout.html in
Chromium and wait for it to finish rendering — and each copy-pasted its own
version of that boilerplate. The copies drifted: different viewports
(794×1123 vs 1440×1123 vs configurable), different handoutReady wait
expressions (strict `=== 'true'` vs lenient `!dataset || === 'true'`),
different timeouts (60s vs 120s). A bug fixed in one copy stayed in the
others (see evolution-log session 5: the CJK \\b and flow-block bugs were
spread across these copies).

This module is the single source of truth. Any script that needs to "open a
built handout in a browser and wait until it's done rendering" uses
`with open_handout(html_path) as (page, errors):` instead of rewriting the
launch+wait sequence.

USAGE
-----
    from handout_browser import open_handout
    with open_handout(html_path, viewport=(794, 1123), collect_errors=True) as (page, errors):
        results = page.evaluate("() => { ... your DOM checks ... }")
    # browser auto-closed on exit; errors is list[str] of pageerror/console
    # errors (empty if collect_errors=False or nothing went wrong).

This is importable AND runnable directly as a smoke test:
    python3 handout_browser.py path/to/handout.html
prints whether the page reached handout-ready without errors.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_handout(
    html_path: Path,
    *,
    viewport: tuple[int, int] = (794, 1123),
    device_scale_factor: float = 1.0,
    collect_errors: bool = False,
    strict_ready: bool = True,
    ready_timeout_ms: int = 60_000,
    fonts_timeout_ms: int = 60_000,
    settle_ms: int = 0,
):
    """Open a built handout.html in headless Chromium and wait for render.

    Yields (page, errors) inside a `with` block; closes the browser on exit.

    Args:
        html_path: path to the built handout.html.
        viewport: (width, height) in CSS pixels. Defaults to A4 @ 96dpi (794×1123).
        device_scale_factor: Playwright context rasterization scale. 1.0 keeps
            CSS pixels 1:1 (validators measure CSS-px geometry, so they must stay
            at the default 1.0). Values >1.0 only affect raster output (PNG
            screenshots); `page.pdf()` uses the print path and ignores this, so a
            high-res screenshot does NOT change the vector PDF.
        collect_errors: if True, attach pageerror/console-error listeners and
            populate `errors`. render_html_to_pdf doesn't need this; validators
            do (they fail on JS errors).
        strict_ready: if True, require dataset.handoutReady === 'true'. If
            False, accept either absent or 'true' (for HTML not built by the
            handout builder, e.g. minimal test fixtures or legacy pages).
        ready_timeout_ms / fonts_timeout_ms: wait timeouts for the handoutReady
            and document.fonts signals.
        settle_ms: extra wait after fonts load, for late layout settling
            (e.g. 400ms used by the bottom-margin validator).

    Yields:
        (page, errors) — page is a Playwright Page ready for evaluate();
        errors is list[str] (empty unless collect_errors=True).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required but not installed. Install with: "
            "pip install playwright && playwright install chromium\n"
            f"Details: {exc}"
        ) from exc

    html_path = Path(html_path).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")

    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context(
                viewport={"width": viewport[0], "height": viewport[1]},
                device_scale_factor=device_scale_factor,
            )
            page = context.new_page()

            if collect_errors:
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.on(
                    "console",
                    lambda msg: errors.append(f"[{msg.type}] {msg.text}")
                    if msg.type == "error"
                    else None,
                )

            page.goto(html_path.as_uri(), wait_until="networkidle")

            if strict_ready:
                ready_expr = "document.documentElement.dataset.handoutReady === 'true'"
            else:
                # Lenient: accept pages that never set the flag (e.g. minimal fixtures).
                ready_expr = (
                    "() => !document.documentElement.dataset.handoutReady || "
                    "document.documentElement.dataset.handoutReady === 'true'"
                )
            page.wait_for_function(ready_expr, timeout=ready_timeout_ms)
            page.wait_for_function(
                "() => !document.fonts || document.fonts.status === 'loaded'",
                timeout=fonts_timeout_ms,
            )
            if settle_ms > 0:
                page.wait_for_timeout(settle_ms)

            yield page, errors
        finally:
            browser.close()


# ---------------------------------------------------------------------------
# Direct-run smoke test: python3 handout_browser.py handout.html
# ---------------------------------------------------------------------------

def _smoke_main(html_arg: str) -> int:
    with open_handout(Path(html_arg), collect_errors=True) as (page, errors):
        title = page.title()
        ready = page.evaluate("() => document.documentElement.dataset.handoutReady")
        sheet_count = page.evaluate("() => document.querySelectorAll('.sheet').length")
    print(f"title: {title!r}")
    print(f"handout-ready: {ready!r}")
    print(f"sheets: {sheet_count}")
    print(f"errors: {len(errors)}")
    for e in errors[:5]:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 handout_browser.py path/to/handout.html", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(_smoke_main(sys.argv[1]))
