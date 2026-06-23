#!/usr/bin/env python3
"""Validate rendered HTML contracts that only exist after browser layout.

This is a post-render gate for faithful handouts. It checks the real printed
DOM under ``#handout-print-root`` instead of hidden source markup, so job-local
CSS overrides and pagination are measured as the user will see them.
"""

from __future__ import annotations

import argparse
import json
import sys
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
    parser.add_argument(
        "--check-image-width-bands",
        action="store_true",
        default=True,
        help="Verify non-exempt images render within their aspect-ratio width band "
        "(portrait ~20%% / square ~35%% / landscape 50-80%% of sheet-body width). "
        "Use --no-check-image-width-bands to disable. <!-- evolved 2026-06-23 -->",
    )
    parser.add_argument(
        "--no-check-image-width-bands",
        dest="check_image_width_bands",
        action="store_false",
        help="Disable the aspect-ratio image width band check.",
    )
    parser.add_argument(
        "--check-adjacent-side-by-side",
        action="store_true",
        default=True,
        help="Verify images inside the same .ocr-image-cluster or <figure> are "
        "side-by-side, not vertically stacked. <!-- evolved 2026-06-23 -->",
    )
    parser.add_argument(
        "--no-check-adjacent-side-by-side",
        dest="check_adjacent_side_by_side",
        action="store_false",
        help="Disable the adjacent-image side-by-side check.",
    )
    parser.add_argument(
        "--disallow-remote-images",
        action="store_true",
        default=False,
        help="Fail if any <img src> in handout.html is a non-local URL. OFF by default; "
        "turned on automatically as part of the image-hosting workflow step. "
        "Non-image remote refs (KaTeX CDN stylesheet/script) are unaffected. "
        "<!-- evolved 2026-06-23 -->",
    )
    parser.add_argument(
        "--remote-image-allowlist",
        action="append",
        default=[],
        help="Hostname substrings exempt from --disallow-remote-images "
        "(repeatable). Reserved for legitimate remote <img> essentials.",
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
    check_image_width_bands: bool,
    check_adjacent_side_by_side: bool,
    disallow_remote_images: bool,
    remote_image_allowlist: list[str],
) -> int:
    # Ensure sibling modules (handout_browser.py in the same scripts/ dir) are
    # importable regardless of how this script is launched.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from handout_browser import open_handout

    html_path = html_path.expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")

    errors: list[str] = []

    with open_handout(
        html_path,
        viewport=(1440, 1123),
        collect_errors=True,
        strict_ready=False,
        ready_timeout_ms=120_000,
        fonts_timeout_ms=120_000,
        settle_ms=wait_ms,
    ) as (page, errors):
        result = page.evaluate(
            """
            ({
              minChoiceImageWidth,
              minChoiceImageHeight,
              checkImageWidthBands,
              checkAdjacentSideBySide,
              disallowRemoteImages,
              remoteAllowlist,
            }) => {
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
              const specialCoverSheets = sheets.filter((sheet) =>
                sheet.classList.contains('concept-map-sheet') ||
                sheet.matches('[data-sheet-role="cover"], [data-cover-sheet="true"]')
              );
              const regularSheets = sheets.filter((sheet) => !specialCoverSheets.includes(sheet));
              const sheetAlignmentTolerancePx = 2;
              const sheetAlignmentFailures = [];
              if (specialCoverSheets.length > 0 && regularSheets.length > 0) {
                const regularRect = regularSheets[0].getBoundingClientRect();
                specialCoverSheets.forEach((sheet, index) => {
                  const rect = sheet.getBoundingClientRect();
                  const leftDelta = Math.abs(rect.left - regularRect.left);
                  const widthDelta = Math.abs(rect.width - regularRect.width);
                  if (
                    leftDelta > sheetAlignmentTolerancePx ||
                    widthDelta > sheetAlignmentTolerancePx
                  ) {
                    sheetAlignmentFailures.push({
                      index,
                      classes: sheet.className,
                      left: Math.round(rect.left * 10) / 10,
                      width: Math.round(rect.width * 10) / 10,
                      regularLeft: Math.round(regularRect.left * 10) / 10,
                      regularWidth: Math.round(regularRect.width * 10) / 10,
                      leftDelta: Math.round(leftDelta * 10) / 10,
                      widthDelta: Math.round(widthDelta * 10) / 10,
                    });
                  }
                });
              }
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

              // --- Aspect-ratio image width band check (C26) ---
              // Per figure-policy.md, the only exempt images are choice-table
              // images and images on marked cover sheets. <figure>/cluster images
              // are NOT blanket-exempt: a single-image figure must satisfy the
              // band for its own aspect ratio. A multi-image group renders as one
              // side-by-side row, so each sibling occupies only a fraction of the
              // row; for those we check the group's AGGREGATE rendered width
              // against the band of the row's dominant aspect class (and the
              // side-by-side gate C27 separately verifies they stayed in one row).
              // Smooth target as a function of aspect ratio (redesigned
              // 2026-06-23). No hard jump at class boundaries; near-square
              // figures read fine at ~30%, only genuinely wide figures need
              // a wide column. Target is then capped by the image's OWN
              // natural width so it is never upscaled past native resolution.
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
              function classifyAspect(naturalW, naturalH) {
                const ar = naturalW / Math.max(naturalH, 1);
                const target = smoothTargetPct(ar) / 100;
                const lo = Math.max(0.12, target - 0.07);
                const hi = Math.min(0.92, target + 0.07);
                let cls;
                if (ar < 0.9) cls = 'portrait';
                else if (ar <= 1.1) cls = 'near-square';
                else if (ar <= 1.5) cls = 'landscape-mild';
                else if (ar <= 2.5) cls = 'landscape-typical';
                else cls = 'landscape-wide';
                return { cls, lo, hi, target };
              }
              function isMarkedCover(node) {
                let cur = node;
                while (cur && cur !== scope) {
                  if (
                    cur.classList && (
                      cur.classList.contains('concept-map-sheet') ||
                      cur.matches('[data-sheet-role="cover"], [data-cover-sheet="true"]')
                    )
                  ) return true;
                  cur = cur.parentElement;
                }
                return false;
              }
              function sheetBodyWidth(node) {
                const sheet = node.closest('.sheet') || node.closest('.sheet-body') || scope;
                const body = sheet.querySelector('.sheet-body') || sheet;
                const bodyRect = body.getBoundingClientRect();
                return bodyRect.width || sheet.getBoundingClientRect().width || 1;
              }
              // Dominant class = widest band (largest hi) among the group, so the
              // aggregate check accepts a row that is collectively large enough.
              function dominantBand(imgs) {
                let best = null;
                for (const im of imgs) {
                  const b = classifyAspect(im.naturalWidth, im.naturalHeight);
                  if (!best || b.hi > best.hi) best = b;
                }
                return best || classifyAspect(1, 1);
              }
              const widthBandViolations = [];
              const widthBandImages = [];
              if (checkImageWidthBands) {
                const allImgs = Array.from(scope.querySelectorAll('.transcript-flow img'));
                // Group images by their figure/cluster container so multi-image
                // rows are evaluated once at the group level.
                const groupMap = new Map();
                const standalone = [];
                for (const img of allImgs) {
                  if (img.closest('.phycat-blockquote table')) continue;
                  if (isMarkedCover(img)) continue;
                  if (!img.naturalWidth || !img.naturalHeight) continue;
                  const grp = img.closest('.ocr-image-cluster, figure');
                  if (grp && grp.querySelectorAll('img').length > 1) {
                    const arr = groupMap.get(grp) || [];
                    arr.push(img);
                    groupMap.set(grp, arr);
                  } else {
                    standalone.push(img);
                  }
                }
                const refWidthOf = (node) => sheetBodyWidth(node) || 1;
                // Natural-width cap: an image's effective target band is capped
                // by its own natural width as a fraction of body width, so it is
                // never expected to render wider than its native pixel resolution
                // (which would upscale and blur it).
                function naturalFrac(img, refWidth) {
                  return img.naturalWidth / Math.max(refWidth, 1);
                }
                function capBand(band, capFrac) {
                  if (capFrac <= band.lo) {
                    // natural width is below the band; accept the natural size.
                    return { lo: Math.max(0.12, capFrac - 0.07), hi: capFrac + 0.07, target: capFrac };
                  }
                  const hi = Math.min(band.hi, Math.max(band.lo, capFrac));
                  return { lo: band.lo, hi: hi, target: Math.min(band.target || ((band.lo + band.hi) / 2), capFrac) };
                }
                // Single-image containers: each image checked against its own band.
                for (const img of standalone) {
                  widthBandImages.push(img);
                  const band = classifyAspect(img.naturalWidth, img.naturalHeight);
                  const refWidth = refWidthOf(img);
                  const capped = capBand(band, naturalFrac(img, refWidth));
                  const rect = img.getBoundingClientRect();
                  const frac = rect.width / Math.max(refWidth, 1);
                  // "Near is exempt": allow a small tolerance so images that
                  // are off by a few percentage points (e.g. multi-image rows
                  // where each sibling shares the band) still pass.
                  const ok = frac >= capped.lo - 0.04 && frac <= capped.hi + 0.04;
                  if (!ok) {
                    widthBandViolations.push({
                      ok,
                      mode: 'single',
                      cls: band.cls,
                      aspect: Math.round((img.naturalWidth / img.naturalHeight) * 100) / 100,
                      renderedPct: Math.round(frac * 1000) / 10,
                      band: `${Math.round(capped.lo * 100)}-${Math.round(capped.hi * 100)}%`,
                      src: (img.getAttribute('src') || '').slice(0, 80),
                    });
                  }
                }
                // Multi-image rows: EACH sibling is judged independently against
                // its own aspect-ratio band (with its own natural-width cap). A
                // side-by-side row does NOT justify enlarging each image to fill
                // the row — each image keeps the size it would have alone.
                //
                // EXCEPTION (evolved 2026-06-23): when the siblings'
                // independent widths sum to more than 100% of body width, the
                // row is "over-subscribed" — keeping all siblings on one row
                // requires shrinking each below its own band. In that case the
                // group prefers staying on one row (no wrapping) and the
                // independent-width rule is EXEMPTED for every sibling in that
                // group, rather than forcing a wrap or flagging each as a
                // violation. The C27 side-by-side gate still verifies they
                // stayed in one row.
                for (const [grp, imgs] of groupMap.entries()) {
                  const refWidth = refWidthOf(grp);
                  // sum of each sibling's independent target (capped by its own
                  // natural width) as a fraction of body width
                  let indepTotal = 0;
                  for (const img of imgs) {
                    const band = classifyAspect(img.naturalWidth, img.naturalHeight);
                    const capped = capBand(band, naturalFrac(img, refWidth));
                    indepTotal += capped.target || ((capped.lo + capped.hi) / 2);
                  }
                  const overSubscribed = indepTotal > 1.0;
                  for (const img of imgs) {
                    widthBandImages.push(img);
                    if (overSubscribed) continue; // exempt: forced to one row
                    const band = classifyAspect(img.naturalWidth, img.naturalHeight);
                    const capped = capBand(band, naturalFrac(img, refWidth));
                    const rect = img.getBoundingClientRect();
                    const frac = rect.width / Math.max(refWidth, 1);
                    const ok = frac >= capped.lo - 0.04 && frac <= capped.hi + 0.04;
                    if (!ok) {
                      widthBandViolations.push({
                        ok,
                        mode: 'row-sibling',
                        cls: band.cls,
                        aspect: Math.round((img.naturalWidth / img.naturalHeight) * 100) / 100,
                        renderedPct: Math.round(frac * 1000) / 10,
                        band: `${Math.round(capped.lo * 100)}-${Math.round(capped.hi * 100)}%`,
                        src: (img.getAttribute('src') || '').slice(0, 60),
                      });
                    }
                  }
                }
              }

              // --- Adjacent-image side-by-side check (C27) ---
              // Only inside .ocr-image-cluster and authored <figure>.
              function rectsStacked(a, b) {
                // Two images are "stacked" (not side-by-side) when their vertical
                // bands do not overlap: the lower image's top is at or below the
                // upper image's bottom. Horizontal alignment is irrelevant —
                // stacked images are usually horizontally aligned (both centered).
                const ra = a.getBoundingClientRect();
                const rb = b.getBoundingClientRect();
                const upper = ra.top <= rb.top ? ra : rb;
                const lower = upper === ra ? rb : ra;
                return lower.top >= upper.bottom - 1;
              }
              const sideBySideGroups = checkAdjacentSideBySide
                ? Array.from(scope.querySelectorAll('.ocr-image-cluster, figure'))
                : [];
              const stackedPairs = [];
              sideBySideGroups.forEach((group) => {
                const imgs = Array.from(group.querySelectorAll('img'));
                // A flex-wrap:wrap container may legitimately wrap extra images
                // onto a second row when each image is sized independently (its
                // own aspect-ratio target) and the row total exceeds 100%. That
                // is expected multi-row layout, NOT a "stacked" failure. Only
                // flag when the container does NOT wrap (so wrapping would be a
                // real layout break) or when ALL siblings collapsed into one
                // vertical column (a true stack, e.g. display:block regression).
                const style = getComputedStyle(group);
                const allowsWrap = style.flexWrap === 'wrap' || style.flexWrap === 'wrap-reverse';
                const isVerticalStack = style.display !== 'flex' && style.display !== 'grid';
                for (let i = 0; i < imgs.length; i += 1) {
                  for (let j = i + 1; j < imgs.length; j += 1) {
                    if (rectsStacked(imgs[i], imgs[j])) {
                      // Exempt wrapping in a flex-wrap container that is not a
                      // degenerate single-column stack.
                      if (allowsWrap && !isVerticalStack) continue;
                      stackedPairs.push({
                        container: group.tagName.toLowerCase() + (group.className ? '.' + group.className.split(' ')[0] : ''),
                        srcA: (imgs[i].getAttribute('src') || '').slice(0, 60),
                        srcB: (imgs[j].getAttribute('src') || '').slice(0, 60),
                      });
                    }
                  }
                }
              });

              // --- HTML-local-image-only check (C28) ---
              const remoteImageSrcs = disallowRemoteImages
                ? Array.from(scope.querySelectorAll('img')).map((img) => img.getAttribute('src') || '')
                    .filter((src) => {
                      if (!src) return false;
                      if (src.startsWith('data:') || src.startsWith('file:')) return false;
                      let url;
                      try { url = new URL(src, document.baseURI); } catch (e) { return false; }
                      if (url.protocol === 'file:') return false;
                      const host = url.hostname;
                      if (remoteAllowlist.some((h) => host.includes(h))) return false;
                      return true;
                    })
                : [];

              return {
                htmlElements: scope.querySelectorAll('h1,h2,h3,h4,p,blockquote,table,ul,ol').length,
                handoutReady: document.documentElement.dataset.handoutReady || '',
                sheets: sheets.length,
                specialCoverSheets: specialCoverSheets.length,
                regularSheets: regularSheets.length,
                sheetAlignmentFailures,
                sheetAlignmentTolerancePx,
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
                widthBandImagesChecked: widthBandImages.length,
                widthBandViolations,
                sideBySideGroupsChecked: sideBySideGroups.length,
                stackedPairs,
                remoteImageSrcs,
            };
            }
            """,
            {
                "minChoiceImageWidth": min_choice_image_width,
                "minChoiceImageHeight": min_choice_image_height,
                "checkImageWidthBands": check_image_width_bands,
                "checkAdjacentSideBySide": check_adjacent_side_by_side,
                "disallowRemoteImages": disallow_remote_images,
                "remoteAllowlist": remote_image_allowlist,
            },
        )

    checks: list[tuple[str, bool, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append((name, ok, detail))

    add("browser errors absent", not errors, f"errors={errors[:3] if errors else 0}")
    add("real HTML elements present", result["htmlElements"] > 0, f"elements={result['htmlElements']}")
    if result["sheets"] > 0:
        add("0 overflow sheets", result["overflowSheets"] == 0, f"overflow={result['overflowSheets']}")
        if result["specialCoverSheets"] > 0 and result["regularSheets"] > 0:
            add(
                "special cover sheets align with regular sheets in screen preview",
                len(result["sheetAlignmentFailures"]) == 0,
                (
                    f"special={result['specialCoverSheets']} regular={result['regularSheets']} "
                    f"tolerance={result['sheetAlignmentTolerancePx']}px "
                    f"failures={result['sheetAlignmentFailures'][:3]}"
                ),
            )
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
    if check_image_width_bands:
        add(
            "non-exempt images render within aspect-ratio width band",
            len(result["widthBandViolations"]) == 0,
            (
                f"checked={result['widthBandImagesChecked']} "
                f"violations={len(result['widthBandViolations'])} "
                f"sample={result['widthBandViolations'][:3]}"
            ),
        )
    if check_adjacent_side_by_side:
        add(
            "clustered/figure images are side-by-side, not stacked",
            len(result["stackedPairs"]) == 0,
            (
                f"groups={result['sideBySideGroupsChecked']} "
                f"stackedPairs={len(result['stackedPairs'])} "
                f"sample={result['stackedPairs'][:3]}"
            ),
        )
    if disallow_remote_images:
        add(
            "handout.html uses local image paths only (no remote src)",
            len(result["remoteImageSrcs"]) == 0,
            f"remote={len(result['remoteImageSrcs'])} sample={result['remoteImageSrcs'][:3]}",
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
        args.check_image_width_bands,
        args.check_adjacent_side_by_side,
        args.disallow_remote_images,
        args.remote_image_allowlist,
    )


if __name__ == "__main__":
    raise SystemExit(main())
