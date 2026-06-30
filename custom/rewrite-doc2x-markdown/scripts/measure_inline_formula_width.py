"""Measure the REAL rendered width (px) of every inline `$...$` formula in a
Markdown file, via a plain KaTeX print + headless Chromium.

WHY: `validate_canonical_markdown.py::lint_long_inline_formula` uses an
*estimated* render width (regex macro folding) as a coarse signal. That
estimate can misjudge: a verbose-but-short-render formula (sin β chain, 275
source chars, ~360px render) was false-flagged as "long". This script measures
the TRUE pixel width and classifies each formula into three bands relative to
the A4 text area (184mm ≈ 695px @ 96dpi, font-size 12px), so the orchestrator
can decide fold-to-aligned vs keep-inline on a physical basis.

PLAIN PRINT (not the scan skill): this builds a minimal HTML with ONLY KaTeX
CDN + the formula spans, no A4 sheet / scan styling. Rendered width of an
inline `.katex` (inline-block) is container-independent — verified 2026-06-30:
the same formula measures identically in a wide vs narrow (100px) container
when wrapped in `white-space:nowrap` and measured via `.katex` itself.

USAGE:
    py -3 scripts/measure_inline_formula_width.py --md source-transcript.md
    py -3 scripts/measure_inline_formula_width.py --md source-transcript.md --json
    py -3 scripts/measure_inline_formula_width.py --md source-transcript.md --band medium,long

Requirements: Python Playwright (sync_api) + Chromium already installed (the
scan-pdf-to-print-html skill depends on the same). Network access for the
KaTeX CDN; or pass --katex-local <dir> to point at a local katex/dist/.

Exit codes: 0 always (this is a measurement tool, not a gate). The output
itself is the deliverable; the caller decides what to act on.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Inline math extractor: matches $...$ but not $$...$$ and not escaped \$
# (mirrors validate_canonical_markdown.py::INLINE_MATH_PATTERN)
INLINE_MATH_PATTERN = re.compile(r"(?<!\\)(?<!\$)\$([^\n$]+)\$(?!\$)")

# A4 text-area geometry (from handout.html: A4 210mm, .sheet padding 13mm L/R).
# 184mm * 96/25.4 ≈ 695.4px. Font-size 12px. .katex inline inherits 12px.
A4_TEXT_WIDTH_PX = 695
TWO_THIRDS_PX = 464   # A4 text * 2/3  — short/medium boundary
NINETY_PCT_PX = 625   # A4 text * 0.90 — medium/long boundary

KATEX_CDN_CSS = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
KATEX_CDN_JS = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
KATEX_CDN_AUTORENDER = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"


def classify_band(width_px: float) -> str:
    """Three-band classifier relative to A4 text area."""
    if width_px <= TWO_THIRDS_PX:
        return "short"    # ≤ 2/3 A4 — fits comfortably inline
    if width_px > NINETY_PCT_PX:
        return "long"     # > 90% A4 — almost certainly overflows/wraps ugly
    return "medium"       # 2/3 .. 90% — judge in context (derivation chain? compact eval?)


def extract_inline_formulas(md_text: str) -> list[tuple[int, str]]:
    """Return [(line_number, latex_body), ...] for every inline $...$ span.

    `$$...$$` display blocks are skipped (the pattern requires no adjacent $).
    Duplicate bodies across lines are kept (the caller may want per-line info);
    use --dedup to collapse."""
    results: list[tuple[int, str]] = []
    for lineno, line in enumerate(md_text.splitlines(), start=1):
        # strip $$...$$ display blocks so their inner $ don't confuse the inline regex
        cleaned = re.sub(r"\$\$.*?\$\$", "", line, flags=re.S)
        for m in INLINE_MATH_PATTERN.finditer(cleaned):
            body = m.group(1)
            # skip trivial/empty
            if body.strip():
                results.append((lineno, body))
    return results


def build_measure_html(bodies: list[str], font_size_px: int = 12) -> str:
    """Build a minimal HTML: KaTeX + one span per formula body.

    Each span is wrapped in `white-space:nowrap` so the .katex stays on one line
    (we measure the formula's own width, not a wrapped fragment)."""
    spans = []
    for idx, body in enumerate(bodies):
        # escape nothing — the body is LaTeX, $...$ delimiters restored
        spans.append(
            f'<div style="white-space:nowrap;"><span id="f{idx}">${body}$</span></div>'
        )
    spans_html = "\n".join(spans)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<link rel="stylesheet" href="{KATEX_CDN_CSS}">
<script defer src="{KATEX_CDN_JS}"></script>
<script defer src="{KATEX_CDN_AUTORENDER}"></script>
<style>body{{font-size:{font_size_px}px;line-height:1.56;}}</style>
</head><body>
{spans_html}
<script>
document.addEventListener("DOMContentLoaded", function() {{
  renderMathInElement(document.body, {{
    delimiters: [{{left: "$$", right: "$$", display: true}}, {{left: "$", right: "$", display: false}}],
    ignoredTags: ["script", "style", "code", "pre", "textarea", "math", "option"],
    throwOnError: false
  }});
}});
</script>
</body></html>"""


def measure_widths(bodies: list[str], font_size_px: int = 12, wait_ms: int = 600) -> list[float]:
    """Render the bodies via headless Chromium + KaTeX, return widths in px.

    Returns a list parallel to `bodies`; a body whose KaTeX render failed (no
    .katex produced) gets width 0.0."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed (pip install playwright; playwright install chromium)",
              file=sys.stderr)
        sys.exit(2)

    html = build_measure_html(bodies, font_size_px)
    tmp_html = Path(__file__).resolve().parent.parent / ".measure_inline_tmp.html"
    tmp_html.write_text(html, encoding="utf-8")
    file_url = "file:///" + str(tmp_html).replace("\\", "/")

    widths: list[float] = [0.0] * len(bodies)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(file_url)
            page.wait_for_load_state("networkidle")
            # wait for fonts + KaTeX auto-render
            try:
                page.wait_for_function("document.fonts.ready.then(() => true)", timeout=15000)
            except Exception:
                pass  # fonts may not all load offline; proceed anyway
            page.wait_for_selector(".katex", timeout=15000)
            page.wait_for_timeout(wait_ms)

            for idx in range(len(bodies)):
                w = page.evaluate(
                    f'(function(){{var el=document.querySelector("#f{idx} .katex");'
                    f'return el?el.getBoundingClientRect().width:0;}})()'
                )
                widths[idx] = float(w) if w else 0.0
        finally:
            browser.close()
            try:
                tmp_html.unlink()
            except OSError:
                pass
    return widths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--md", required=True, help="Path to source-transcript.md")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a table")
    parser.add_argument("--band", default="all",
                        help="Comma-list of bands to show: short,medium,long (default: all)")
    parser.add_argument("--dedup", action="store_true", help="Collapse duplicate formula bodies")
    parser.add_argument("--font-size", type=int, default=12, help="Base font-size px (default 12)")
    parser.add_argument("--wait-ms", type=int, default=600, help="Extra render settle ms (default 600)")
    args = parser.parse_args()

    md_path = Path(args.md)
    if not md_path.is_file():
        print(f"ERROR: not a file: {args.md}", file=sys.stderr)
        return 2
    md_text = md_path.read_text(encoding="utf-8")

    formulas = extract_inline_formulas(md_text)
    if args.dedup:
        seen: set[str] = set()
        deduped: list[tuple[int, str]] = []
        for lineno, body in formulas:
            if body not in seen:
                seen.add(body)
                deduped.append((lineno, body))
        formulas = deduped

    if not formulas:
        print("(no inline $...$ formulas found)" if not args.json else "[]")
        return 0

    bodies = [b for _, b in formulas]
    widths = measure_widths(bodies, font_size_px=args.font_size, wait_ms=args.wait_ms)

    band_filter = {b.strip() for b in args.band.split(",") if b.strip()} if args.band != "all" else None
    rows = []
    for (lineno, body), width in zip(formulas, widths):
        band = classify_band(width)
        if band_filter and band not in band_filter:
            continue
        rows.append({"line": lineno, "width_px": round(width, 1), "band": band, "tex": body})

    if args.json:
        json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"A4 text area = {A4_TEXT_WIDTH_PX}px; 2/3 = {TWO_THIRDS_PX}px; 90% = {NINETY_PCT_PX}px; font-size {args.font_size}px")
        print(f"{'line':>5} {'width_px':>9} {'band':>7}  tex")
        print("-" * 100)
        for r in rows:
            preview = r["tex"][:80] + ("…" if len(r["tex"]) > 80 else "")
            print(f"{r['line']:>5} {r['width_px']:>9} {r['band']:>7}  {preview}")
        # summary
        from collections import Counter
        bands = Counter(r["band"] for r in rows)
        print(f"\nsummary: short={bands.get('short',0)} medium={bands.get('medium',0)} long={bands.get('long',0)} (total {len(rows)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
