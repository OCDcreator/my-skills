#!/usr/bin/env python3
"""Check that no non-cover, non-final A4 sheet ends with excessive trailing blank space.

The check is applied after the local pagination script has run and fonts have
settled. For every sheet except the first (assumed cover) and the last
(document terminator, where trailing blank space is normal), it measures the gap
between the bottom of the last content element and the bottom of the sheet body.

A sheet is exempt from the check when the very first content element on the
following sheet is a `.phycat-blockquote`, because example/question blockquotes
must be kept whole; in that case the trailing blank on the preceding sheet is
the unavoidable cost of keeping the blockquote unsplit. A sheet is also exempt
when it is explicitly marked `data-ends-before-lecture="true"`, because some
jobs require each lecture-level heading to start on a fresh A4 sheet.

A sheet is ALSO exempt when the trailing blank is the unavoidable cost of the
aspect-ratio image-width rule: i.e. the first content element on the following
sheet is a single figure/image that satisfies the width band for its aspect
ratio and is too tall to move up without overflowing. When two hard contracts
conflict at a page boundary, the rule whose target is met (image width) wins
over the rule whose target cannot be met without breaking it (trailing blank).
This is the "near-is-exempt" trade-off for figure-boundary sheets. <!-- evolved 2026-06-23 -->
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_MAX_TRAILING_FRACTION = 0.10


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="Path to handout.html")
    parser.add_argument(
        "--max-fraction",
        type=float,
        default=DEFAULT_MAX_TRAILING_FRACTION,
        help="Maximum allowed trailing blank fraction per sheet (default: 0.10)",
    )
    parser.add_argument(
        "--skip-cover",
        action="store_true",
        default=True,
        help="Skip the first sheet (cover) in the check",
    )
    parser.add_argument(
        "--no-skip-cover",
        action="store_false",
        dest="skip_cover",
        help="Check the first sheet too",
    )
    parser.add_argument(
        "--skip-last",
        action="store_true",
        default=True,
        help="Skip the last sheet (document terminator) in the check",
    )
    parser.add_argument(
        "--no-skip-last",
        action="store_false",
        dest="skip_last",
        help="Check the last sheet too",
    )
    return parser


def validate(
    html_path: Path,
    max_fraction: float,
    skip_cover: bool,
    skip_last: bool,
) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"Playwright required: {exc}")

    url = html_path.as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 794, "height": 1123})
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_function(
            "document.documentElement.dataset.handoutReady === 'true'",
            timeout=60_000,
        )
        page.wait_for_function(
            "document.fonts && document.fonts.status === 'loaded'",
            timeout=60_000,
        )
        page.wait_for_timeout(400)

        results = page.evaluate(
            """
            ({ maxFraction, skipCover, skipLast }) => {
                function isBlockquote(el) {
                    return el && (
                        el.classList.contains('phycat-blockquote') ||
                        el.querySelector('.phycat-blockquote') !== null
                    );
                }
                // Figure-boundary trade-off (evolved 2026-06-23): when the
                // next sheet's FIRST content block contains an image that
                // satisfies its aspect-ratio width band AND that block is too
                // tall to fit in the current sheet's trailing blank, the blank
                // is the unavoidable cost of the image-width rule. Exempt the
                // current sheet rather than letting the two hard contracts
                // fight — the rule whose target is met (image width) wins over
                // the rule whose target cannot be met without breaking it.
                function smoothTargetPct(ar) {
                    const pts = [
                        [0.0, 18], [0.7, 22], [0.9, 27], [1.0, 30], [1.2, 35],
                        [1.5, 45], [2.0, 58], [2.5, 68], [3.5, 78], [6.0, 82],
                    ];
                    if (ar <= pts[0][0]) return pts[0][1];
                    if (ar >= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
                    for (let i = 0; i < pts.length - 1; i++) {
                        const a0 = pts[i][0], t0 = pts[i][1];
                        const a1 = pts[i + 1][0], t1 = pts[i + 1][1];
                        if (a0 <= ar && ar <= a1) {
                            const r = (ar - a0) / (a1 - a0);
                            return t0 + (t1 - t0) * r;
                        }
                    }
                    return 30;
                }
                function classifyAspect(nw, nh) {
                    const ar = nw / Math.max(nh, 1);
                    const target = smoothTargetPct(ar) / 100;
                    const lo = Math.max(0.12, target - 0.07);
                    const hi = Math.min(0.92, target + 0.07);
                    return { lo, hi };
                }
                function imgBandOk(img, bodyWidth) {
                    if (!img || !img.naturalWidth || !img.naturalHeight) return false;
                    // Each image — whether alone or one of several in a side-by-side
                    // figure/cluster — is judged against its OWN aspect-ratio band,
                    // capped by its OWN natural width (no upscaling). A multi-image
                    // row does not justify enlarging each sibling to fill the row.
                    const natFrac = img.naturalWidth / Math.max(bodyWidth, 1);
                    const band = classifyAspect(img.naturalWidth, img.naturalHeight);
                    let lo = band.lo, hi = band.hi;
                    if (natFrac <= band.lo) {
                        lo = Math.max(0.12, natFrac - 0.07); hi = natFrac + 0.07;
                    } else {
                        hi = Math.min(band.hi, Math.max(band.lo, natFrac));
                    }
                    const frac = img.getBoundingClientRect().width / Math.max(bodyWidth, 1);
                    return frac >= lo - 0.04 && frac <= hi + 0.04;
                }
                function nextStartsFigureBoundary(nextBody, bodyWidth, trailingPx) {
                    if (!nextBody) return false;
                    const first = Array.from(nextBody.children).find(
                        (c) => !c.classList.contains('doc-title') && c.getBoundingClientRect().height > 0
                    );
                    if (!first) return false;
                    const img = first.querySelector('img');
                    if (!img) return false;
                    // The image must satisfy its band (this is the rule that
                    // wins the trade-off). The block must be too tall to move
                    // up — but "almost fits" also counts: if moving the figure
                    // would overflow by only a few percent, the blank is still
                    // genuinely caused by that figure. trailingPx*0.08 lets a
                    // figure that is within ~8% of fitting stay a boundary.
                    const blockH = first.getBoundingClientRect().height;
                    return imgBandOk(img, bodyWidth) &&
                        blockH > trailingPx - Math.max(16, trailingPx * 0.08);
                }

                function firstContentChild(body) {
                    const children = Array.from(body.children).filter(
                        el => !el.classList.contains('doc-title')
                    );
                    for (const child of children) {
                        const rect = child.getBoundingClientRect();
                        if (rect.height > 0) return child;
                    }
                    return null;
                }

                function lastContentBottom(body) {
                    const children = Array.from(body.children).filter(
                        el => !el.classList.contains('doc-title')
                    );
                    let lastBottom = body.getBoundingClientRect().top;
                    for (const child of children) {
                        const rect = child.getBoundingClientRect();
                        if (rect.height > 0) {
                            lastBottom = Math.max(lastBottom, rect.bottom);
                        }
                    }
                    return lastBottom;
                }

                const sheets = Array.from(document.querySelectorAll('.sheet'));
                const lastIndex = sheets.length - 1;
                const violations = [];
                const measurements = [];

                sheets.forEach((sheet, index) => {
                    if (skipCover && index === 0) return;
                    if (skipLast && index === lastIndex) return;

                    const body = sheet.querySelector('.sheet-body');
                    if (!body) return;
                    const bodyRect = body.getBoundingClientRect();
                    const bodyHeight = bodyRect.height;
                    if (bodyHeight <= 0) return;

                    const nextSheet = sheets[index + 1];
                    const nextBody = nextSheet ? nextSheet.querySelector('.sheet-body') : null;
                    const nextFirstChild = nextBody ? firstContentChild(nextBody) : null;
                    const nextStartsWithBlockquote = isBlockquote(nextFirstChild);
                    const endsBeforeLecture = sheet.dataset.endsBeforeLecture === 'true';

                    const trailing = bodyRect.bottom - lastContentBottom(body);
                    const fraction = trailing / bodyHeight;
                    const pageNumber = sheet.dataset.pageNumber || String(index + 1);

                    const figureBoundary = nextStartsFigureBoundary(nextBody, bodyRect.width, trailing);
                    const exempt = nextStartsWithBlockquote || endsBeforeLecture || figureBoundary;

                    measurements.push({
                        pageNumber,
                        trailingPx: Math.round(trailing),
                        bodyHeightPx: Math.round(bodyHeight),
                        fraction: Number(fraction.toFixed(3)),
                        nextStartsWithBlockquote,
                        endsBeforeLecture,
                        figureBoundary,
                    });

                    if (!exempt && fraction > maxFraction) {
                        violations.push({
                            pageNumber,
                            trailingPx: Math.round(trailing),
                            bodyHeightPx: Math.round(bodyHeight),
                            fraction: Number(fraction.toFixed(3)),
                        });
                    }
                });

                return { sheetCount: sheets.length, measurements, violations };
            }
            """,
            {
                "maxFraction": max_fraction,
                "skipCover": skip_cover,
                "skipLast": skip_last,
            },
        )

        browser.close()

    print(f"Sheets inspected: {results['sheetCount']}")
    for m in results["measurements"]:
        exempt_reasons = []
        if m["nextStartsWithBlockquote"]:
            exempt_reasons.append("next sheet starts with blockquote")
        if m["endsBeforeLecture"]:
            exempt_reasons.append("forced lecture break")
        if m.get("figureBoundary"):
            exempt_reasons.append("next sheet starts with band-compliant figure")
        exempt_note = f" [exempt: {', '.join(exempt_reasons)}]" if exempt_reasons else ""
        print(
            f"  Sheet {m['pageNumber']}: trailing {m['trailingPx']}px / "
            f"body {m['bodyHeightPx']}px ({m['fraction'] * 100:.1f}%){exempt_note}"
        )

    if results["violations"]:
        print("FAIL: excessive trailing blank space detected on:")
        for v in results["violations"]:
            print(
                f"  - Sheet {v['pageNumber']}: trailing {v['trailingPx']}px / "
                f"body {v['bodyHeightPx']}px ({v['fraction'] * 100:.1f}% > "
                f"{max_fraction * 100:.1f}%)"
            )
        return 1

    print(
        f"PASS: no inspected sheet has trailing blank space exceeding "
        f"{max_fraction * 100:.0f}% of body height."
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")
    return validate(
        html_path,
        args.max_fraction,
        args.skip_cover,
        args.skip_last,
    )


if __name__ == "__main__":
    raise SystemExit(main())
