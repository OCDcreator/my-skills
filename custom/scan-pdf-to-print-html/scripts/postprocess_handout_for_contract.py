#!/usr/bin/env python3
"""Post-process a built handout.html so it meets current render contracts.

This script is intentionally job-local/final-output oriented:
- switch MathJax SVG bootstrap/waiting to KaTeX auto-render
- widen images according to the skill's aspect-ratio width contract
- override old fixed-width OCR cluster layout so grouped images can stay readable
- inject an authored SVG cover as the first A4 sheet when available
- wrap plain example/exercise paragraphs into `.phycat-blockquote`
- force each `第 N 讲` section to start on a fresh sheet
- expose heading metadata in the DOM for downstream PDF bookmark generation

It does NOT edit source-transcript.md.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


MATHJAX_BOOTSTRAP = """
<script>
window.MathJax = {
  tex: {
    inlineMath: [['\\\\(', '\\\\)'], ['$', '$']],
    displayMath: [['\\\\[', '\\\\]'], ['$$', '$$']]
  },
  svg: {
    fontCache: 'none'
  },
  startup: {
    typeset: false
  }
};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
"""

KATEX_BOOTSTRAP = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<script>
window.KATEX_RENDER_OPTIONS = {
  delimiters: [
    {left: "$$", right: "$$", display: true},
    {left: "$", right: "$", display: false},
    {left: "\\\\(", right: "\\\\)", display: false},
    {left: "\\\\[", right: "\\\\]", display: true}
  ],
  ignoredTags: ["script", "style", "code", "pre", "textarea", "math", "option"],
  throwOnError: false,
  strict: false
};
</script>
"""

OLD_MATH_WAIT = """
  if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
    try {
      await window.MathJax.startup.promise;
    } catch (_err) {
      // Keep print flow alive even if MathJax startup reports an issue.
    }
  }

  if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
    try {
      await window.MathJax.typesetPromise([root]);
    } catch (_err) {
      // Keep print flow alive even if MathJax reports a typeset issue.
    }
  }
  await nextHandoutFrame();
"""

NEW_MATH_WAIT = """
  try {
    await new Promise((resolve) => {
      const start = Date.now();
      const tick = () => {
        if (window.renderMathInElement || Date.now() - start > 15000) {
          resolve();
          return;
        }
        setTimeout(tick, 30);
      };
      tick();
    });
    if (window.renderMathInElement) {
      window.renderMathInElement(root, window.KATEX_RENDER_OPTIONS);
    }
    if (document.fonts && document.fonts.ready) {
      await document.fonts.ready;
    }
  } catch (_err) {
    // Keep print flow alive even if KaTeX reports an issue.
  }
  await nextHandoutFrame();
"""

CSS_OVERRIDES = """
/* Post-process contract overrides: KaTeX final math + aspect-ratio figure widths */
.transcript-flow .ocr-image-cluster {
  display: flex !important;
  flex-wrap: nowrap;
  justify-content: center;
  align-items: flex-start;
  gap: 0.55rem !important;
  width: 100% !important;
  max-width: 100% !important;
  margin: 3mm auto !important;
}

.transcript-flow .ocr-image-cluster > img {
  max-width: none !important;
  margin: 0 !important;
}

.transcript-flow figure {
  width: 100%;
  max-width: 100%;
  margin: 4mm auto;
}

.transcript-flow figure > img {
  max-width: none !important;
}

/* Authored full-page concept cover should behave like a regular A4 sheet in preview. */
.sheet.concept-map-sheet {
  padding: 0 !important;
  overflow: hidden;
}

.sheet.concept-map-sheet .concept-map-front-image,
.sheet.concept-map-sheet svg,
.sheet.concept-map-sheet object {
  display: block;
  width: 100% !important;
  height: 100% !important;
  max-width: none !important;
  max-height: none !important;
  object-fit: fill;
  margin: 0 !important;
}

@media print {
  .sheet.concept-map-sheet {
    box-shadow: none;
    margin: 0;
  }
}
"""

TIGHTEN_VERTICAL_SPACING = """
/* Optional job-local tightening for bottom-margin repair */
.transcript-flow h2,
.transcript-flow h3,
.transcript-flow h4 {
  margin-bottom: 2.2mm !important;
}

.transcript-flow p,
.transcript-flow li {
  margin-bottom: 0.48em !important;
}

.transcript-flow ul,
.transcript-flow ol {
  margin-bottom: 0.62em !important;
}

.transcript-flow table {
  margin: 2.2mm 0 3mm !important;
}

.transcript-flow figure,
.transcript-flow .ocr-image-cluster {
  margin: 2.2mm auto !important;
}

.transcript-flow .phycat-blockquote {
  margin: 2.4mm 0 3mm !important;
  padding: 2.4mm 2.8mm !important;
}

.transcript-flow .phycat-blockquote p,
.transcript-flow .phycat-blockquote li {
  margin-bottom: 0.42em !important;
}
"""

IMAGE_WIDTH_HELPERS = """
function smoothTargetPct(aspectRatio) {
  const pts = [
    [0.0, 18], [0.7, 22], [0.9, 27], [1.0, 30], [1.2, 35],
    [1.5, 45], [2.0, 58], [2.5, 68], [3.5, 78], [6.0, 82],
  ];
  if (aspectRatio <= pts[0][0]) return pts[0][1];
  if (aspectRatio >= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
  for (let i = 0; i < pts.length - 1; i += 1) {
    const [a0, t0] = pts[i];
    const [a1, t1] = pts[i + 1];
    if (a0 <= aspectRatio && aspectRatio <= a1) {
      const r = (aspectRatio - a0) / (a1 - a0);
      return t0 + (t1 - t0) * r;
    }
  }
  return 30;
}

function naturalCapPct(img, refWidth) {
  return (img.naturalWidth / Math.max(refWidth, 1)) * 100;
}

function cappedTargetPct(img, refWidth) {
  const ar = img.naturalWidth / Math.max(img.naturalHeight, 1);
  return Math.min(smoothTargetPct(ar), naturalCapPct(img, refWidth));
}

function applySingleImageWidth(img, refWidth, pct) {
  img.style.width = `${pct.toFixed(1)}%`;
  img.style.maxWidth = `${img.naturalWidth}px`;
  img.style.height = 'auto';
  img.style.display = 'block';
  img.style.margin = '0 auto';
}

function configureImageGroup(group, imgs, refWidth) {
  const targets = imgs.map((img) => cappedTargetPct(img, refWidth));
  const total = targets.reduce((sum, value) => sum + value, 0);
  const scale = total > 100 ? 95 / total : 1;

  group.style.display = 'flex';
  group.style.flexWrap = 'nowrap';
  group.style.justifyContent = 'center';
  group.style.alignItems = 'flex-start';
  group.style.gap = imgs.length >= 3 ? '0.45rem' : '0.6rem';
  group.style.width = '100%';
  group.style.maxWidth = '100%';
  group.style.margin = '3mm auto';

  imgs.forEach((img, index) => {
    applySingleImageWidth(img, refWidth, targets[index] * scale);
    img.style.margin = '0';
  });
}

function applyFigureWidthBands(root) {
  const refWidth = root.getBoundingClientRect().width || 650;
  const seenGroups = new Set();
  const imgs = Array.from(root.querySelectorAll('.transcript-flow img'));

  imgs.forEach((img) => {
    if (!img.naturalWidth || !img.naturalHeight) return;
    if (img.closest('.phycat-blockquote table')) return;

    const group = img.closest('.ocr-image-cluster, figure');
    if (group) {
      const groupImgs = Array.from(group.querySelectorAll('img')).filter(
        (node) => node.naturalWidth && node.naturalHeight && !node.closest('.phycat-blockquote table')
      );
      if (groupImgs.length > 1) {
        if (seenGroups.has(group)) return;
        seenGroups.add(group);
        configureImageGroup(group, groupImgs, refWidth);
        return;
      }
      group.style.width = '100%';
      group.style.maxWidth = '100%';
    }

    applySingleImageWidth(img, refWidth, cappedTargetPct(img, refWidth));
  });
}
"""

BOOKMARK_PAGINATION_HELPERS = """
function findFirstTopLevelHeading(block) {
  return block.querySelector(':scope > h2, :scope > h3');
}

function isLectureHeading(text) {
  // NOTE: no trailing \b — \b is an ASCII word boundary that fails after a
  // CJK character (e.g. "第3讲" ends with 讲, a non-word char to \b, so the
  // boundary never fires). The 第N{讲|章|...} shape is distinctive enough;
  // the trailing group requires a delimiter or end-of-string instead.
  return /^第\\s*[0-9一二三四五六七八九十百零]+\\s*(?:讲|章|节|部分|篇|单元)(?:\\s|$|[：:．、。])/.test((text || '').trim());
}

// A chapter-shaped h2 that should also force a fresh sheet. Broader than
// isLectureHeading: catches 单元N, numeric outlines like "1. 力学", and English
// Module/Lesson/Chapter. Pure-exposition h2 like "## 补充说明" intentionally
// does NOT match — only headings that clearly start a new chapter/section.
function isChapterBreakHeading(text) {
  return /^(?:第\\s*[0-9一二三四五六七八九十百零]+\\s*(?:讲|章|节|部分|篇|单元)|单元\\s*[0-9一二三四五六七八九十百零]+|[0-9]+\\s*[\\.、]\\s*[\\u4e00-\\u9fff]|(?:Module|Lesson|Chapter)\\s+\\d)/.test((text || '').trim());
}

function normalizeTextForBookmark(text) {
  return (text || '').replace(/\\s+/g, ' ').trim();
}

function firstMeaningfulParagraph(block) {
  return Array.from(block.querySelectorAll(':scope > p')).find((p) => {
    return normalizeTextForBookmark(p.textContent).length > 0;
  }) || null;
}

function isExampleParagraph(paragraph) {
  if (!paragraph) return false;
  const badge = paragraph.querySelector('.lead-tag-example');
  if (badge) return true;
  const text = normalizeTextForBookmark(paragraph.textContent);
  return /^(?:【\\s*)?(?:例题|练习)(?:\\s*[0-9一二三四五六七八九十百零]+)?(?:\\s*】)?/.test(text);
}

function isDecoratedExampleQuote(block) {
  return !!block.querySelector(':scope > blockquote.phycat-blockquote');
}

function blockStartsExample(block) {
  if (isDecoratedExampleQuote(block)) {
    const firstQuoteParagraph = block.querySelector(':scope > blockquote.phycat-blockquote > p');
    return isExampleParagraph(firstQuoteParagraph);
  }
  const firstParagraph = firstMeaningfulParagraph(block);
  return isExampleParagraph(firstParagraph);
}

function paragraphStartsAnalysis(paragraph) {
  if (!paragraph) return false;
  if (paragraph.querySelector('.lead-tag')) return true;
  const text = normalizeTextForBookmark(paragraph.textContent);
  return /^(?:【\\s*)?(?:分析|解析|解答|证明|总结|备注|归纳总结|注意|方法[一二三四五六七八九十百零0-9]?)(?:\\s*】)?/.test(text);
}

function blockStartsHeading(block) {
  return !!findFirstTopLevelHeading(block);
}

function ensureExampleQuote(block) {
  if (isDecoratedExampleQuote(block)) return block;
  const firstParagraph = firstMeaningfulParagraph(block);
  if (!isExampleParagraph(firstParagraph)) return block;
  const quote = document.createElement('blockquote');
  quote.className = 'phycat-blockquote';
  while (block.firstChild) {
    quote.appendChild(block.firstChild);
  }
  block.appendChild(quote);
  return block;
}

function mergeExampleRuns(blocks) {
  const merged = [];
  for (let i = 0; i < blocks.length; i += 1) {
    const block = ensureExampleQuote(blocks[i]);
    if (!blockStartsExample(block)) {
      merged.push(block);
      continue;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'flow-block';
    wrapper.dataset.sourcePage = block.dataset.sourcePage || '';
    const quote = block.querySelector(':scope > blockquote.phycat-blockquote') || document.createElement('blockquote');
    if (!quote.classList.contains('phycat-blockquote')) {
      quote.className = 'phycat-blockquote';
    }
    if (!block.contains(quote)) {
      while (block.firstChild) {
        quote.appendChild(block.firstChild);
      }
    }
    wrapper.appendChild(quote);

    let cursor = i + 1;
    while (cursor < blocks.length) {
      const next = blocks[cursor];
      if (blockStartsExample(next) || blockStartsHeading(next)) break;
      const nextParagraph = firstMeaningfulParagraph(next);
      if (paragraphStartsAnalysis(nextParagraph)) break;
      while (next.firstChild) {
        quote.appendChild(next.firstChild);
      }
      cursor += 1;
    }

    merged.push(wrapper);
    i = cursor - 1;
  }
  return merged;
}

function cloneBlockPreservingMeta(block) {
  const clone = block.cloneNode(true);
  if (block.dataset && block.dataset.sourcePage) {
    clone.dataset.sourcePage = block.dataset.sourcePage;
  }
  return clone;
}

function headingLevelNumber(tagName) {
  const m = /H([1-6])/.exec(tagName || '');
  return m ? Number(m[1]) : 6;
}

function bookmarkLevelForHeading(node) {
  if (!node) return 2;
  const text = normalizeTextForBookmark(node.textContent);
  if (isLectureHeading(text)) return 1;
  const rank = headingLevelNumber(node.tagName);
  if (rank <= 2) return 2;
  if (rank === 3) return 3;
  return 4;
}

function collectBlockBookmarks(block, pageNumber, sink) {
  const headings = Array.from(block.querySelectorAll(':scope > h2, :scope > h3, :scope > h4'));
  headings.forEach((heading) => {
    const title = normalizeTextForBookmark(heading.textContent);
    if (!title) return;
    sink.push({
      title,
      level: bookmarkLevelForHeading(heading),
      page: pageNumber,
    });
  });
}

function attachBookmarkPayload(root, entries) {
  if (!root) return;
  root.dataset.pdfBookmarks = JSON.stringify(entries);
}

function injectConceptCover(root) {
  if (!root || root.dataset.coverInjected === 'true') return false;
  if (root.querySelector('.concept-map-sheet')) {
    root.dataset.coverInjected = 'true';
    return false;
  }
  const coverHref = root.dataset.coverHref || '';
  if (!coverHref) return false;

  const cover = document.createElement('article');
  cover.className = 'sheet concept-map-sheet';
  cover.dataset.fitState = 'ready';
  cover.dataset.sheetRole = 'cover';
  cover.dataset.coverSheet = 'true';

  const body = document.createElement('section');
  body.className = 'sheet-body transcript-flow';
  const image = document.createElement('img');
  image.className = 'concept-map-front-image';
  image.src = coverHref;
  image.alt = root.dataset.coverAlt || (root.dataset.title ? `${root.dataset.title} 概念图` : '概念图');
  body.appendChild(image);

  // Covers show no footer — no page number, no heading breadcrumb. The cover
  // still counts toward the total page count N used by regular sheets.
  cover.append(body);
  root.insertBefore(cover, root.firstChild);
  root.dataset.coverInjected = 'true';
  return true;
}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, help="Path to handout.html")
    parser.add_argument(
        "--tighten-vertical-spacing",
        action="store_true",
        help="Add a small job-local spacing reduction to improve bottom-margin validation.",
    )
    return parser


def replace_mathjax_with_katex(html: str) -> str:
    if MATHJAX_BOOTSTRAP in html:
        html = html.replace(MATHJAX_BOOTSTRAP, KATEX_BOOTSTRAP, 1)
    if OLD_MATH_WAIT in html:
        html = html.replace(OLD_MATH_WAIT, NEW_MATH_WAIT, 1)
    return html


def inject_css_overrides(html: str, tighten_vertical_spacing: bool) -> str:
    css = CSS_OVERRIDES
    if tighten_vertical_spacing:
        css += "\n" + TIGHTEN_VERTICAL_SPACING
    if css in html:
        return html
    if "</style>" not in html:
        raise SystemExit("closing </style> not found in handout.html")
    return html.replace("</style>", css + "\n</style>", 1)


def inject_js_overrides(html: str) -> str:
    if "function applyFigureWidthBands(root)" not in html:
        anchor = "async function paginateHandout() {"
        if anchor not in html:
            raise SystemExit("paginateHandout() anchor not found in handout.html")
        html = html.replace(anchor, IMAGE_WIDTH_HELPERS + "\n\n" + BOOKMARK_PAGINATION_HELPERS + "\n\n" + anchor, 1)

    marker = "  const title = printRoot.dataset.title || '';\n"
    if "applyFigureWidthBands(sourceRoot);" not in html:
        if marker not in html:
            raise SystemExit("paginateHandout title marker not found in handout.html")
        html = html.replace(marker, "  applyFigureWidthBands(sourceRoot);\n\n" + marker, 1)

    old_paginate_tail = """  const title = printRoot.dataset.title || '';
  const sourceLabel = printRoot.dataset.sourceLabel || 'OCR Transcript';
  const blocks = collectFlowBlocks(sourceRoot);
  printRoot.replaceChildren();

  let pageNumber = 1;
  let sheet = createSheet(pageNumber, title, sourceLabel, true);
  printRoot.appendChild(sheet);

  for (const block of blocks) {
    if (appendBlockToSheet(sheet, block)) {
      continue;
    }
    pageNumber += 1;
    sheet = createSheet(pageNumber, title, sourceLabel, false);
    printRoot.appendChild(sheet);
    appendBlockToSheet(sheet, block);
  }

  renumberSheets(printRoot);
  sourceRoot.remove();
  document.documentElement.dataset.handoutReady = 'true';
}
"""

    new_paginate_tail = """  const title = printRoot.dataset.title || '';
  const hasCover = !!printRoot.dataset.coverHref;
  const sourceLabel = printRoot.dataset.sourceLabel || 'OCR Transcript';
  const blocks = mergeExampleRuns(collectFlowBlocks(sourceRoot));
  const bookmarkEntries = [];
  printRoot.replaceChildren();

  let pageNumber = 1;
  let sheet = createSheet(pageNumber, title, sourceLabel, !hasCover);
  printRoot.appendChild(sheet);

  for (const originalBlock of blocks) {
    const block = cloneBlockPreservingMeta(originalBlock);
    const heading = findFirstTopLevelHeading(block);
    const headingText = normalizeTextForBookmark(heading ? heading.textContent : '');
    const body = sheetBody(sheet);
    const hasBodyContent = body
      ? body.querySelectorAll(':scope > .flow-block').length > 0
      : false;

    const isBreakHeading = isLectureHeading(headingText) ||
      (heading && heading.tagName === 'H2' && isChapterBreakHeading(headingText));
    if (heading && isBreakHeading && hasBodyContent) {
      sheet.dataset.endsBeforeLecture = 'true';
      pageNumber += 1;
      sheet = createSheet(pageNumber, title, sourceLabel, false);
      printRoot.appendChild(sheet);
    }

    if (!appendBlockToSheet(sheet, block)) {
      pageNumber += 1;
      sheet = createSheet(pageNumber, title, sourceLabel, false);
      printRoot.appendChild(sheet);
      appendBlockToSheet(sheet, block);
    }

    collectBlockBookmarks(block, pageNumber, bookmarkEntries);
  }

  const coverInjected = injectConceptCover(printRoot);
  if (coverInjected) {
    bookmarkEntries.forEach((entry) => {
      entry.page += 1;
    });
  }
  renumberSheets(printRoot);
  attachBookmarkPayload(printRoot, bookmarkEntries);
  sourceRoot.remove();
  document.documentElement.dataset.handoutReady = 'true';
}
"""

    if new_paginate_tail not in html:
        if old_paginate_tail not in html:
            raise SystemExit("paginateHandout tail block not found in handout.html")
        html = html.replace(old_paginate_tail, new_paginate_tail, 1)

    return html


def inject_cover_metadata(html_path: Path, html_text: str) -> str:
    # PNG-first: HTML-cover jobs (a4-novak-html-cover) render concept-map.png;
    # SVG remains a fallback for legacy jobs that never migrated to the HTML流派.
    cover_candidates = ("concept-map.png", "concept-map.svg", "concept-map-preview.png")
    cover_path = next((html_path.parent / name for name in cover_candidates if (html_path.parent / name).exists()), None)
    if cover_path is None:
        return html_text

    attrs_to_add: list[str] = []
    if ' data-cover-href="' not in html_text:
        attrs_to_add.append(f'data-cover-href="{html.escape(cover_path.name, quote=True)}"')
    if ' data-cover-alt="' not in html_text:
        cover_alt = f"{html_path.parent.name} 概念图"
        attrs_to_add.append(f'data-cover-alt="{html.escape(cover_alt, quote=True)}"')
    if not attrs_to_add:
        return html_text

    pattern = re.compile(r'(<div\s+id="handout-print-root"[^>]*?)>')
    match = pattern.search(html_text)
    if not match:
        raise SystemExit("handout-print-root tag not found")
    insertion = match.group(1) + " " + " ".join(attrs_to_add) + ">"
    return html_text[: match.start()] + insertion + html_text[match.end() :]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file not found: {html_path}")

    html = html_path.read_text(encoding="utf-8")
    html = replace_mathjax_with_katex(html)
    html = inject_css_overrides(html, args.tighten_vertical_spacing)
    html = inject_js_overrides(html)
    html = inject_cover_metadata(html_path, html)
    html_path.write_text(html, encoding="utf-8")
    print(f"postprocessed: {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
