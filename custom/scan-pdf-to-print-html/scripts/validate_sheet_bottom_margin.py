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

ORPHAN-HEADING GUARD (evolved 2026-06-24): the blockquote/figure exemptions
above are about content that genuinely cannot move up. They must NOT excuse a
sheet that ends with a lone heading ("orphan heading") followed by a large
blank — that is a pagination defect (the heading should have traveled with the
next block to the following sheet), not an unavoidable cost. So even when the
next sheet starts with a blockquote/figure, the current sheet still FAILS when
its LAST content element is a heading and the trailing blank exceeds the
threshold. Only a true lecture/chapter break (`data-ends-before-lecture="true"`
or a next-sheet chapter-shaped h2) keeps an orphan-heading sheet exempt,
because there the heading is the intended end of a section.

HEADING-BOUNDARY EXEMPTION (evolved 2026-06-24): the symmetric, legitimate
case. When the NEXT sheet's FIRST content block is a heading AND it is a real
section start (at least one non-heading content block follows it on that
sheet), the trailing blank on the current sheet is the cost of the heading
starting its own section. This blank is NOT a defect: the builder placed the
heading at the section start, and pulling it up would strand it above a blank
(re-creating the orphan defect). So a sheet whose next sheet starts with a
heading (h1-h6) that has following content is exempt. The "has following
content" requirement keeps the exemption honest: a next sheet that is JUST a
lone heading is a stranded heading, not a section start, and stays a violation.
This is the critical weak-model safety valve — it stops a weaker model from
"tightening spacing" to chase a blank that is actually correct, which would
only make the layout worse and burn tokens for nothing. The current sheet's
own orphan-heading guard still runs independently, so a real stranded heading
on THIS sheet is never hidden by the next sheet's heading.
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
    # Ensure sibling modules (handout_browser.py in the same scripts/ dir) are
    # importable regardless of how this script is launched.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from handout_browser import open_handout

    with open_handout(
        html_path,
        viewport=(794, 1123),
        strict_ready=True,
        ready_timeout_ms=60_000,
        fonts_timeout_ms=60_000,
        settle_ms=400,
    ) as (page, _errors):
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

                // Heading-boundary trade-off (evolved 2026-06-24): when the next
                // sheet's FIRST content block is a heading AND that heading is a
                // real section start (it has at least one non-heading content
                // block after it on the same sheet), the trailing blank on the
                // current sheet is the unavoidable cost of the heading starting
                // its own section. Moving the heading up would either strand it
                // above a blank (an orphan heading) or split its section
                // awkwardly across the boundary — so this blank is legitimate
                // and must NOT be flagged. This is the key weak-model safety
                // valve: it stops a weaker model from "tightening spacing" to
                // pull a heading up, which would only re-create the
                // orphan-heading defect or make the layout worse.
                //
                // The "has following content" requirement is what keeps the
                // exemption honest: a sheet whose next sheet is JUST a lone
                // heading with nothing after it is NOT a section start — that
                // is a stranded heading, and the current blank stays a violation.
                // The current sheet's own orphan-heading guard still runs
                // independently, so a real stranded heading on THIS sheet is
                // never hidden by the next sheet's heading.
                function nextStartsHeadingBoundary(nextBody) {
                    if (!nextBody) return false;
                    const blocks = Array.from(nextBody.children).filter(
                        (c) => !c.classList.contains('doc-title') && c.getBoundingClientRect().height > 0
                    );
                    if (blocks.length < 2) return false;  // lone heading = not a section start
                    const first = blocks[0];
                    const firstIsHeading = /^H[1-6]$/.test(first.tagName)
                        || (first.tagName === 'DIV' && !!first.querySelector(':scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6'));
                    if (!firstIsHeading) return false;
                    // At least one more content block follows the heading — a
                    // real section, not a stranded heading.
                    return true;
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

                // The builder wraps each block in a <div class="flow-block">, so a
                // chapter <h2> sits INSIDE the flow-block, not as a direct sheet-body
                // child. firstContentChild returns the wrapper; this helper looks one
                // level inside it for an h2 and returns the h2 element (or null).
                function firstContentH2(el) {
                    if (!el) return null;
                    if (el.tagName === 'H2') return el;
                    if (el.tagName === 'DIV') {
                        return el.querySelector(':scope > h2');
                    }
                    return null;
                }

                // A chapter-shaped heading text. MUST stay in sync with
                // postprocess_handout_for_contract.py's isLectureHeading +
                // isChapterBreakHeading. Only chapter-shaped h2 (第N章/节/讲/篇/单元/
                // 部分, 单元N, N.中文, Module/Lesson/Chapter N) forces a fresh sheet;
                // a generic exposition h2 like "大招 2" or "补充说明" does NOT — that
                // would let any tall block escape the trailing-blank check.
                // NOTE: no \b — \b is an ASCII word boundary that fails after a CJK
                // character (e.g. "第三章" ends with a CJK char, \b never fires there).
                function isChapterShapedText(text) {
                    var t = (text || '').trim();
                    if (/^第\\s*[0-9一二三四五六七八九十百零]+\\s*(?:讲|章|节|部分|篇|单元)(?:\\s|$|[：:．、。])/.test(t)) return true;
                    return /^(?:第\\s*[0-9一二三四五六七八九十百零]+\\s*(?:讲|章|节|部分|篇|单元)|单元\\s*[0-9一二三四五六七八九十百零]+|[0-9]+\\s*[\\.、]\\s*[\\u4e00-\\u9fff]|(?:Module|Lesson|Chapter)\\s+\\d)/.test(t);
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

                // Orphan-heading guard (evolved 2026-06-24): a sheet whose LAST
                // content element is a heading, sitting alone above a large
                // trailing blank, is a pagination defect — the heading should
                // have followed its content to the next sheet instead of being
                // stranded at the bottom. This is true regardless of WHY the
                // blank exists (blockquote/figure on the next page); so a
                // heading-ending sheet must FAIL unless a real section break
                // (forced lecture break or next-sheet chapter h2) exempts it.
                function lastContentChild(body) {
                    const children = Array.from(body.children).filter(
                        el => !el.classList.contains('doc-title')
                    );
                    for (let i = children.length - 1; i >= 0; i -= 1) {
                        const rect = children[i].getBoundingClientRect();
                        if (rect.height > 0) return children[i];
                    }
                    return null;
                }
                function lastContentHeading(body) {
                    const last = lastContentChild(body);
                    if (!last) return null;
                    if (/^H[1-6]$/.test(last.tagName)) return last;
                    // The builder wraps each block in a .flow-block; the
                    // heading sits one level inside it. Look for the first
                    // heading among the wrapper's direct children.
                    if (last.tagName === 'DIV') {
                        return last.querySelector(':scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6');
                    }
                    return null;
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
                    const nextChapterH2 = firstContentH2(nextFirstChild);
                    const nextStartsWithChapterH2 = !!(nextChapterH2 && isChapterShapedText(nextChapterH2.textContent));

                    const trailing = bodyRect.bottom - lastContentBottom(body);
                    const fraction = trailing / bodyHeight;
                    const pageNumber = sheet.dataset.pageNumber || String(index + 1);

                    const figureBoundary = nextStartsFigureBoundary(nextBody, bodyRect.width, trailing);
                    const headingBoundary = nextStartsHeadingBoundary(nextBody);

                    // A real section break — the heading is the intended end
                    // of a chapter/lecture on this sheet. This is the ONLY
                    // reason a heading-ending sheet may keep its trailing blank.
                    const sectionBreak = endsBeforeLecture || nextStartsWithChapterH2;

                    // Orphan-heading guard: if the sheet ends with a heading
                    // above a large blank, it is a pagination defect unless a
                    // real section break justifies it. The blockquote/figure/
                    // heading-boundary exemptions do NOT cover this case — a
                    // stranded heading must travel with its following content,
                    // so we surface it as a violation even when those would
                    // otherwise excuse the blank.
                    const endsWithHeading = !!lastContentHeading(body);
                    const orphanHeading =
                        endsWithHeading &&
                        fraction > maxFraction &&
                        !sectionBreak;

                    // Normal exemptions: blank is the unavoidable cost of a
                    // next-sheet blockquote/figure/heading-boundary, or an
                    // explicit lecture/chapter break. These exempt the blank
                    // only when an orphan heading is not present (orphan
                    // overrides them).
                    const baseExempt = nextStartsWithBlockquote || endsBeforeLecture || figureBoundary || nextStartsWithChapterH2 || headingBoundary;
                    const exempt = baseExempt && !orphanHeading;

                    measurements.push({
                        pageNumber,
                        trailingPx: Math.round(trailing),
                        bodyHeightPx: Math.round(bodyHeight),
                        fraction: Number(fraction.toFixed(3)),
                        nextStartsWithBlockquote,
                        endsBeforeLecture,
                        figureBoundary,
                        nextStartsWithChapterH2,
                        headingBoundary,
                        endsWithHeading,
                        orphanHeading,
                    });

                    if (!exempt && fraction > maxFraction) {
                        violations.push({
                            pageNumber,
                            trailingPx: Math.round(trailing),
                            bodyHeightPx: Math.round(bodyHeight),
                            fraction: Number(fraction.toFixed(3)),
                            orphanHeading,
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

    print(f"Sheets inspected: {results['sheetCount']}")
    for m in results["measurements"]:
        exempt_reasons = []
        if m["nextStartsWithBlockquote"]:
            exempt_reasons.append("next sheet starts with blockquote")
        if m["endsBeforeLecture"]:
            exempt_reasons.append("forced lecture break")
        if m.get("figureBoundary"):
            exempt_reasons.append("next sheet starts with band-compliant figure")
        if m.get("nextStartsWithChapterH2"):
            exempt_reasons.append("next sheet starts with chapter h2")
        if m.get("headingBoundary"):
            exempt_reasons.append("next sheet starts with a heading (section start)")
        exempt_note = f" [exempt: {', '.join(exempt_reasons)}]" if exempt_reasons else ""
        if m.get("orphanHeading") and exempt_reasons:
            exempt_note += " [overridden by orphan heading]"
        print(
            f"  Sheet {m['pageNumber']}: trailing {m['trailingPx']}px / "
            f"body {m['bodyHeightPx']}px ({m['fraction'] * 100:.1f}%){exempt_note}"
        )

    if results["violations"]:
        print("FAIL: excessive trailing blank space detected on:")
        for v in results["violations"]:
            orphan_note = (
                "  [orphan heading: move the trailing heading to the next sheet]"
                if v.get("orphanHeading")
                else ""
            )
            print(
                f"  - Sheet {v['pageNumber']}: trailing {v['trailingPx']}px / "
                f"body {v['bodyHeightPx']}px ({v['fraction'] * 100:.1f}% > "
                f"{max_fraction * 100:.1f}%){orphan_note}"
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
