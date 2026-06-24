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

ORPHAN-HEADING RULE (redesigned 2026-06-25): a heading is NEVER allowed to be
the last line/block of a page. This FAILs regardless of how large the trailing
blank is — the rule is structural ("a heading must travel with its following
content"), not blank-size-gated. The only exemption is a genuine section break
(`data-ends-before-lecture="true"` or a next-sheet chapter-shaped h2), where
the heading is the intended end of a section.

FIGURE-BOUNDARY ANALYSIS (redesigned 2026-06-25): instead of a blanket
exemption, the gate CALCULATES whether a next-sheet image figure could fit in
the current trailing gap if narrowed to the width-band minimum (0.8x of its
current rendered width — the band floor below which readability suffers). The
figure's minimum-scale block height = tallest image height * 0.8 + fixed
overhead (figure margins/captions). If that minimum height fits in the gap,
the blank IS a defect: the figure could have been narrowed and moved up, so
the gate FAILs with an actionable hint ("shrink the figure within its width
band and let it move up"). If even the minimum-width figure is taller than the
gap, the blank is the unavoidable cost of the width-band floor and the sheet is
exempt. This makes the gate's judgment match a human's: "could this image,
shrunk a bit, have gone on the previous page? yes -> fix it; no -> leave it."
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
                // Figure-boundary trade-off (evolved 2026-06-23, refined
                // 2026-06-24): when the next sheet's FIRST content block is an
                // image figure (single img, <figure>, or multi-image cluster),
                // the trailing blank on the current sheet is the unavoidable
                // cost of the image width-band rule — images cannot be freely
                // shrunk to fill the gap, so the gap is legitimate regardless
                // of whether the figure "almost fits". The per-image width
                // band is enforced by validate_rendered_handout_contract.py,
                // NOT here; running it in this trailing-blank gate produced
                // false positives on proportionally-scaled multi-image
                // clusters (individual siblings dip below their solo band by
                // design), which tempted weak models to "fix" correct breaks.
                // Figure-boundary analysis (evolved 2026-06-23, redesigned
                // 2026-06-25). The next sheet's FIRST content block is an image
                // figure (single <img>, <figure>, or multi-image cluster). The
                // image width-band rule allows the image to render anywhere in
                // its band — including as small as ~0.8x of its current rendered
                // width (a floor below which readability suffers). So whether
                // the trailing blank on THIS sheet is a real defect depends on
                // a CALCULATION, not a blanket exemption:
                //   - If the figure, shrunk to the band minimum (0.8x), would
                //     fit in the trailing gap, the blank IS a defect: the image
                //     could have been narrowed and moved up. FAIL with a hint
                //     telling the model to shrink the figure (the model knows
                //     the width band and can pick a smaller in-band width).
                //   - If even the minimum-width figure is taller than the gap,
                //     the blank is the unavoidable cost of the width-band floor.
                //     Exempt — do not flag, do not tempt a weak model to shrink
                //     past readability.
                // The minimum-scale factor (0.8) is the band floor: it mirrors
                // the lowest in-band width the rendered-contract gate permits.
                const FIGURE_MIN_SCALE = 0.8;
                function analyzeFigureBoundary(nextBody, trailingPx) {
                    if (!nextBody) return null;
                    const first = Array.from(nextBody.children).find(
                        (c) => !c.classList.contains('doc-title') && c.getBoundingClientRect().height > 0
                    );
                    if (!first) return null;
                    const imgs = first.querySelectorAll('img');
                    const isFigureBlock = first.tagName === 'FIGURE'
                        || !!first.querySelector(':scope > figure, :scope > img, :scope > .ocr-image-cluster')
                        || imgs.length > 0;
                    if (!isFigureBlock) return null;
                    // Block height = tallest image + non-image overhead (figure
                    // padding/margins/captions, which do NOT scale with image
                    // width). At the minimum scale, image height scales 0.8x
                    // (aspect preserved) while overhead stays fixed.
                    let tallestImgH = 0;
                    imgs.forEach((img) => {
                        tallestImgH = Math.max(tallestImgH, img.getBoundingClientRect().height);
                    });
                    const blockH = first.getBoundingClientRect().height;
                    const overhead = Math.max(0, blockH - tallestImgH);
                    const estHeightAtMin = tallestImgH * FIGURE_MIN_SCALE + overhead;
                    return {
                        isFigure: true,
                        blockH: Math.round(blockH),
                        estHeightAtMin: Math.round(estHeightAtMin),
                        trailingPx: Math.round(trailingPx),
                        // "fits at minimum scale" => the blank is avoidable by
                        // shrinking the figure within its band; this is a defect.
                        fitsAtMinScale: estHeightAtMin <= trailingPx,
                    };
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

                    const figureAnalysis = analyzeFigureBoundary(nextBody, trailing);
                    // figureExempt: the next sheet starts with an image figure
                    // that cannot fit in the trailing gap even at the band
                    // minimum (0.8x) — the blank is the unavoidable cost of the
                    // width-band floor. figureDefect: the figure COULD fit if
                    // narrowed to its band minimum — the blank is avoidable.
                    const figureExempt = !!(figureAnalysis && figureAnalysis.isFigure && !figureAnalysis.fitsAtMinScale);
                    const figureDefect = !!(figureAnalysis && figureAnalysis.isFigure && figureAnalysis.fitsAtMinScale);
                    const headingBoundary = nextStartsHeadingBoundary(nextBody);

                    // A real section break — the heading is the intended end
                    // of a chapter/lecture on this sheet. This is the ONLY
                    // reason a heading-ending sheet may keep its trailing blank.
                    const sectionBreak = endsBeforeLecture || nextStartsWithChapterH2;

                    // Orphan-heading guard: a sheet ending with a heading is a
                    // pagination defect (the heading must travel with its
                    // following content) unless a real section break justifies
                    // it. NOTE: a heading as the last block is a defect EVEN
                    // when the trailing blank is small — the rule is "a heading
                    // is never the last line of a page", not "a heading above a
                    // big blank". So this does NOT gate on fraction > maxFraction.
                    const endsWithHeading = !!lastContentHeading(body);
                    const orphanHeading = endsWithHeading && !sectionBreak;

                    // Normal exemptions: blank is the unavoidable cost of a
                    // next-sheet blockquote / non-fitting figure / heading-
                    // boundary, or an explicit lecture/chapter break. A figure
                    // that COULD fit (figureDefect) is NOT exempt.
                    const baseExempt = nextStartsWithBlockquote || endsBeforeLecture || figureExempt || nextStartsWithChapterH2 || headingBoundary;
                    const exempt = baseExempt && !orphanHeading && !figureDefect;

                    measurements.push({
                        pageNumber,
                        trailingPx: Math.round(trailing),
                        bodyHeightPx: Math.round(bodyHeight),
                        fraction: Number(fraction.toFixed(3)),
                        nextStartsWithBlockquote,
                        endsBeforeLecture,
                        figureExempt,
                        figureDefect,
                        nextStartsWithChapterH2,
                        headingBoundary,
                        endsWithHeading,
                        orphanHeading,
                        figureAnalysis,
                    });

                    // A sheet violates when:
                    //  (a) orphan heading — a heading is the last line (always
                    //      a defect, regardless of blank size); or
                    //  (b) a figure that could fit at band-minimum width sits
                    //      on the next sheet above a real trailing gap; or
                    //  (c) a non-exempt sheet whose trailing blank exceeds the
                    //      threshold.
                    let violated = false;
                    let reason = '';
                    if (orphanHeading) {
                        violated = true;
                        reason = 'orphan-heading';
                    } else if (figureDefect && fraction > maxFraction) {
                        violated = true;
                        reason = 'figure-could-fit-at-band-min';
                    } else if (!exempt && fraction > maxFraction) {
                        violated = true;
                        reason = 'excessive-trailing-blank';
                    }
                    if (violated) {
                        violations.push({
                            pageNumber,
                            trailingPx: Math.round(trailing),
                            bodyHeightPx: Math.round(bodyHeight),
                            fraction: Number(fraction.toFixed(3)),
                            reason,
                            orphanHeading,
                            figureDefect,
                            figureAnalysis,
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
        if m.get("figureExempt"):
            fa = m.get("figureAnalysis") or {}
            exempt_reasons.append(
                f"next sheet starts with a figure that cannot fit at band-min "
                f"(est {fa.get('estHeightAtMin')}px > gap {fa.get('trailingPx')}px)"
            )
        if m.get("nextStartsWithChapterH2"):
            exempt_reasons.append("next sheet starts with chapter h2")
        if m.get("headingBoundary"):
            exempt_reasons.append("next sheet starts with a heading (section start)")
        exempt_note = f" [exempt: {', '.join(exempt_reasons)}]" if exempt_reasons else ""
        print(
            f"  Sheet {m['pageNumber']}: trailing {m['trailingPx']}px / "
            f"body {m['bodyHeightPx']}px ({m['fraction'] * 100:.1f}%){exempt_note}"
        )

    if results["violations"]:
        print("FAIL: trailing-blank / orphan-heading / movable-figure defects:")
        for v in results["violations"]:
            reason = v.get("reason", "excessive-trailing-blank")
            if reason == "orphan-heading":
                # Orphan headings FAIL regardless of blank size — the rule is
                # "a heading is never the last line of a page", so do not show
                # a misleading "> threshold%" clause.
                print(
                    f"  - Sheet {v['pageNumber']}: heading is the last line "
                    f"(trailing {v['trailingPx']}px)  [orphan heading: move "
                    f"the trailing heading to the next sheet]"
                )
            elif reason == "figure-could-fit-at-band-min":
                fa = v.get("figureAnalysis") or {}
                print(
                    f"  - Sheet {v['pageNumber']}: trailing {v['trailingPx']}px / "
                    f"body {v['bodyHeightPx']}px ({v['fraction'] * 100:.1f}% > "
                    f"{max_fraction * 100:.1f}%)  [figure on next sheet could fit if "
                    f"narrowed to band-min: est {fa.get('estHeightAtMin')}px <= gap "
                    f"{fa.get('trailingPx')}px — shrink the figure within its width "
                    f"band and let it move up]"
                )
            else:
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
