#!/usr/bin/env python3
"""Validate rendered HTML contracts that only exist after browser layout.

This is a post-render gate for faithful handouts. It checks the real printed
DOM under ``#handout-print-root`` instead of hidden source markup, so job-local
CSS overrides and pagination are measured as the user will see them.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_MIN_CHOICE_IMAGE_WIDTH = 90
DEFAULT_MIN_CHOICE_IMAGE_HEIGHT = 70


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="Path to handout.html")
    parser.add_argument(
        "--min-choice-image-width",
        type=int,
        default=DEFAULT_MIN_CHOICE_IMAGE_WIDTH,
        help="Minimum rendered width for images inside question option tables",
    )
    parser.add_argument(
        "--min-choice-image-height",
        type=int,
        default=DEFAULT_MIN_CHOICE_IMAGE_HEIGHT,
        help="Minimum rendered height for images inside question option tables",
    )
    parser.add_argument(
        "--require-katex",
        action="store_true",
        help="Require at least one rendered KaTeX node; use for math-bearing jobs",
    )
    parser.add_argument(
        "--disallow-mathjax",
        action="store_true",
        help="Fail if MathJax containers/scripts are present; use after final KaTeX post-processing",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=1000,
        help="Extra wait after fonts/math/pagination settle",
    )
    return parser


def _is_transparent(color: str) -> bool:
    normalized = color.replace(" ", "").lower()
    return normalized in {"rgba(0,0,0,0)", "transparent"}


def validate(
    html_path: Path,
    min_choice_image_width: int,
    min_choice_image_height: int,
    require_katex: bool,
    disallow_mathjax: bool,
    wait_ms: int,
) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"Playwright required: {exc}")

    html_path = html_path.expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")

    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123})
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.on(
            "console",
            lambda msg: errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None,
        )
        page.goto(html_path.as_uri(), wait_until="networkidle")
        page.wait_for_function(
            """
            () => !document.documentElement.dataset.handoutReady ||
                  document.documentElement.dataset.handoutReady === 'true'
            """,
            timeout=120_000,
        )
        page.wait_for_function(
            "() => !document.fonts || document.fonts.status === 'loaded'",
            timeout=120_000,
        )
        if wait_ms > 0:
            page.wait_for_timeout(wait_ms)

        result = page.evaluate(
            """
            ({ minChoiceImageWidth, minChoiceImageHeight }) => {
              const printRoot = document.querySelector('#handout-print-root');
              const scope = printRoot || document.body;
              const bodyText = scope.innerText || '';

              function isNoBorder(style) {
                return style.borderTopWidth === '0px' || style.borderTopStyle === 'none';
              }

              function isTransparent(color) {
                const normalized = String(color).replace(/\\s+/g, '').toLowerCase();
                return normalized === 'rgba(0,0,0,0)' || normalized === 'transparent';
              }

              function px(value) {
                const n = Number.parseFloat(String(value));
                return Number.isFinite(n) ? n : 0;
              }

              function sameColor(a, b) {
                return String(a).replace(/\\s+/g, '').toLowerCase() ===
                  String(b).replace(/\\s+/g, '').toLowerCase();
              }

              function styleOf(el) {
                const s = getComputedStyle(el);
                return {
                  borderTopWidth: s.borderTopWidth,
                  borderTopStyle: s.borderTopStyle,
                  backgroundColor: s.backgroundColor,
                  fontSize: s.fontSize,
                  fontWeight: s.fontWeight,
                  display: s.display,
                  color: s.color,
                };
              }

              const sheets = Array.from(scope.querySelectorAll('.sheet'));
              const nonCoverSheets = sheets.filter((s, index) =>
                index > 0 && !s.classList.contains('concept-map-sheet')
              );
              const contentlessSheets = nonCoverSheets.filter((sheet) => {
                const text = (sheet.innerText || '').replace(/第\\s*\\d+\\s*页/g, '').trim();
                const media = sheet.querySelectorAll('img,svg,canvas,table,math,.katex').length;
                return text.length === 0 && media === 0;
              });

              const blockquotes = Array.from(scope.querySelectorAll('.transcript-flow .phycat-blockquote'));
              const badBlockquoteRules = blockquotes.filter((quote) => {
                const s = getComputedStyle(quote);
                const leftWidth = px(s.borderLeftWidth);
                const topWidth = px(s.borderTopWidth);
                const rightWidth = px(s.borderRightWidth);
                const bottomWidth = px(s.borderBottomWidth);
                const maxOtherWidth = Math.max(topWidth, rightWidth, bottomWidth);
                const hasVisibleLeftRule =
                  leftWidth >= 2.5 &&
                  s.borderLeftStyle !== 'none' &&
                  !isTransparent(s.borderLeftColor) &&
                  !sameColor(s.borderLeftColor, s.backgroundColor);
                const isPlainBoxBorder =
                  maxOtherWidth > 0 &&
                  leftWidth <= maxOtherWidth + 0.5 &&
                  sameColor(s.borderLeftColor, s.borderTopColor) &&
                  sameColor(s.borderLeftColor, s.borderRightColor) &&
                  sameColor(s.borderLeftColor, s.borderBottomColor);
                return !hasVisibleLeftRule || isPlainBoxBorder;
              });
              const badBlockquoteRuleDetails = badBlockquoteRules.slice(0, 3).map((quote) => {
                const s = getComputedStyle(quote);
                return {
                  left: `${s.borderLeftWidth} ${s.borderLeftStyle} ${s.borderLeftColor}`,
                  top: `${s.borderTopWidth} ${s.borderTopStyle} ${s.borderTopColor}`,
                  right: `${s.borderRightWidth} ${s.borderRightStyle} ${s.borderRightColor}`,
                  bottom: `${s.borderBottomWidth} ${s.borderBottomStyle} ${s.borderBottomColor}`,
                  background: s.backgroundColor,
                };
              });

              const labelPattern = /(^|[\\s【])(?:例题?|练习)\\s*\\d/;
              const labelBlockquotes = blockquotes.filter((quote) => labelPattern.test(quote.innerText || ''));
              const missingExampleBadges = labelBlockquotes.filter(
                (quote) => !quote.querySelector('.lead-tag-example')
              );
              const badExampleBadges = Array.from(scope.querySelectorAll('.lead-tag-example')).filter((badge) => {
                const s = getComputedStyle(badge);
                return s.display === 'none' || isTransparent(s.backgroundColor);
              });

              const choiceTables = Array.from(
                scope.querySelectorAll('.transcript-flow .phycat-blockquote table')
              );
              const badChoiceTables = choiceTables.filter((table) => {
                const tableStyle = getComputedStyle(table);
                const cells = Array.from(table.querySelectorAll('th,td'));
                if (!isNoBorder(tableStyle) || !isTransparent(tableStyle.backgroundColor)) {
                  return true;
                }
                return cells.some((cell) => {
                  const s = getComputedStyle(cell);
                  return !isNoBorder(s) || !isTransparent(s.backgroundColor);
                });
              });

              const badChoiceHeaderParity = choiceTables.filter((table) => {
                const th = table.querySelector('th');
                const td = table.querySelector('td');
                if (!th || !td) return false;
                const thStyle = styleOf(th);
                const tdStyle = styleOf(td);
                return (
                  thStyle.fontSize !== tdStyle.fontSize ||
                  thStyle.fontWeight !== tdStyle.fontWeight ||
                  thStyle.backgroundColor !== tdStyle.backgroundColor ||
                  thStyle.borderTopWidth !== tdStyle.borderTopWidth ||
                  thStyle.borderTopStyle !== tdStyle.borderTopStyle
                );
              });

              const choiceImages = Array.from(
                scope.querySelectorAll('.transcript-flow .phycat-blockquote table img')
              );
              const badChoiceImages = choiceImages.filter((img) => {
                const rect = img.getBoundingClientRect();
                return rect.width < minChoiceImageWidth || rect.height < minChoiceImageHeight;
              });

              return {
                htmlElements: scope.querySelectorAll('h1,h2,h3,h4,p,blockquote,table,ul,ol').length,
                handoutReady: document.documentElement.dataset.handoutReady || '',
                sheets: sheets.length,
                overflowSheets: sheets.filter((s) => s.dataset.fitState === 'overflow').length,
                contentlessSheets: contentlessSheets.length,
                katexNodes: scope.querySelectorAll('.katex').length,
                mathjaxNodes:
                  scope.querySelectorAll('mjx-container').length +
                  document.querySelectorAll('script[src*="mathjax"], script[src*="MathJax"]').length,
                rawDollar: (bodyText.match(/\\$[^\\$\\n]+\\$/g) || []).length,
                rawParen: (bodyText.match(/\\\\\\([^)]*\\\\\\)/g) || []).length,
                rawBracket: (bodyText.match(/\\\\\\[[^\\]]*\\\\\\]/g) || []).length,
                calloutMarkers: (bodyText.match(/\\[!(?:question|note|tip|warning|info)\\]/gi) || []).length,
                blockquotes: blockquotes.length,
                badBlockquoteRules: badBlockquoteRules.length,
                badBlockquoteRuleDetails,
                labelBlockquotes: labelBlockquotes.length,
                exampleBadges: scope.querySelectorAll('.lead-tag-example').length,
                missingExampleBadges: missingExampleBadges.length,
                badExampleBadges: badExampleBadges.length,
                choiceTables: choiceTables.length,
                badChoiceTables: badChoiceTables.length,
                badChoiceHeaderParity: badChoiceHeaderParity.length,
                choiceImages: choiceImages.length,
                badChoiceImages: badChoiceImages.length,
                minChoiceImageWidth,
                minChoiceImageHeight,
                firstChoiceImageSize: choiceImages[0]
                  ? (() => {
                      const r = choiceImages[0].getBoundingClientRect();
                      return { width: Math.round(r.width), height: Math.round(r.height) };
                    })()
                  : null,
              };
            }
            """,
            {
                "minChoiceImageWidth": min_choice_image_width,
                "minChoiceImageHeight": min_choice_image_height,
            },
        )
        browser.close()

    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append((name, ok, detail))

    add("browser errors absent", not errors, f"errors={errors[:3] if errors else 0}")
    add("real HTML elements present", result["htmlElements"] > 0, f"elements={result['htmlElements']}")
    if result["sheets"] > 0:
        add("0 overflow sheets", result["overflowSheets"] == 0, f"overflow={result['overflowSheets']}")
        add(
            "0 contentless non-cover sheets",
            result["contentlessSheets"] == 0,
            f"contentless={result['contentlessSheets']}",
        )
    add(
        "MathJax absent when disallowed",
        (not disallow_mathjax) or result["mathjaxNodes"] == 0,
        f"mathjax={result['mathjaxNodes']} disallow={disallow_mathjax}",
    )
    add(
        "raw math delimiters absent",
        result["rawDollar"] == 0 and result["rawParen"] == 0 and result["rawBracket"] == 0,
        f"$={result['rawDollar']} \\(={result['rawParen']} \\[={result['rawBracket']}",
    )
    if require_katex:
        add("KaTeX nodes exist", result["katexNodes"] > 0, f"katex={result['katexNodes']}")
    add("callout markers stripped", result["calloutMarkers"] == 0, f"markers={result['calloutMarkers']}")
    if result["blockquotes"] > 0:
        add(
            "blockquote left rule visible",
            result["badBlockquoteRules"] == 0,
            (
                f"blockquotes={result['blockquotes']} bad={result['badBlockquoteRules']} "
                f"sample={result['badBlockquoteRuleDetails']}"
            ),
        )
    if result["labelBlockquotes"] > 0:
        add(
            "example/exercise lead badges visible",
            result["missingExampleBadges"] == 0 and result["badExampleBadges"] == 0,
            (
                f"labelBlockquotes={result['labelBlockquotes']} "
                f"missing={result['missingExampleBadges']} bad={result['badExampleBadges']}"
            ),
        )
    if result["choiceTables"] > 0:
        add(
            "question option tables are neutral",
            result["badChoiceTables"] == 0,
            f"choiceTables={result['choiceTables']} bad={result['badChoiceTables']}",
        )
        add(
            "question option th/td styles match",
            result["badChoiceHeaderParity"] == 0,
            f"choiceTables={result['choiceTables']} badHeaderParity={result['badChoiceHeaderParity']}",
        )
    if result["choiceImages"] > 0:
        add(
            "question option images are readable",
            result["badChoiceImages"] == 0,
            (
                f"choiceImages={result['choiceImages']} bad={result['badChoiceImages']} "
                f"min={min_choice_image_width}x{min_choice_image_height} "
                f"first={result['firstChoiceImageSize']}"
            ),
        )

    print("=" * 72)
    print("RENDERED HANDOUT CONTRACT")
    print("=" * 72)
    passed = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}\n        {detail}")
        passed += int(ok)
    print("-" * 72)
    print(f"{passed}/{len(checks)} checks PASS")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed == len(checks) else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return validate(
        Path(args.html),
        args.min_choice_image_width,
        args.min_choice_image_height,
        args.require_katex,
        args.disallow_mathjax,
        args.wait_ms,
    )


if __name__ == "__main__":
    raise SystemExit(main())
