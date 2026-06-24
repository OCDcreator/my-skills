#!/usr/bin/env python3
"""Build a fidelity-first A4 HTML handout from OCR markdown."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from markdown_it import MarkdownIt


PAGE_SPLIT_PATTERN = re.compile(r"^##\s+Page\s+(\d+)\s*$", re.MULTILINE)
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
MATH_SEGMENT_PATTERN = re.compile(r"\$\$.*?\$\$|\$.*?\$", re.DOTALL)
FENCED_CODE_BLOCK_PATTERN = re.compile(r"(^```[^\n]*\n.*?^```[ \t]*$)", re.MULTILINE | re.DOTALL)
INLINE_CODE_SPAN_PATTERN = re.compile(r"(`+)([^`\n]*?)\1")
# Matches a $$...$$ block whose opening and closing delimiters are both on
# blockquote lines (typical of Obsidian callouts). The interior lines will
# have their structural '>' prefix stripped so they do not leak into the formula.
CALLOUT_DISPLAY_MATH_PATTERN = re.compile(
    r"(?m)^([ \t]*>[ \t]*)\$\$[ \t]*$\n"
    r"(.*?)\n"
    r"^[ \t]*>[ \t]*\$\$[ \t]*$",
    re.DOTALL,
)
FORBIDDEN_FRAGMENT_PATTERN = re.compile(
    r"<!DOCTYPE|<html\b|</html>|<head\b|</head>|<body\b|</body>|<style\b|</style>|<script\b|</script>",
    re.IGNORECASE,
)
RENDERED_HTML_TAG_PATTERN = re.compile(r"<[A-Za-z][^>]*>|</[A-Za-z][^>]*>")
IMG_TAG_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
IMG_ONLY_PARAGRAPH_PATTERN = re.compile(r"<p>\s*(<img\b[^>]*>)\s*</p>", re.IGNORECASE)
IMG_SEQUENCE_PATTERN = re.compile(r"(?P<sequence>(?:<img\b[^>]*>\s*(?:<br\s*/?>\s*)?){2,})", re.IGNORECASE)
# Author <figure> blocks carry their own layout (flex/grid, max-width %,
# captions) and must pass through untouched. Protecting them from the OCR-crop
# normalizer below prevents intentional figures from collapsing to ~20mm.
FIGURE_BLOCK_PATTERN = re.compile(r"<figure\b[^>]*>.*?</figure>", re.IGNORECASE | re.DOTALL)
IMG_SRC_PATTERN = re.compile(r"""\bsrc=(?:"([^"]+)"|'([^']+)')""", re.IGNORECASE)
DOC2X_CROP_PATTERN = re.compile(r"[?&]w=(\d+)&h=(\d+)(?:&|$)", re.IGNORECASE)
PAGE_WRAPPER_PATTERN = re.compile(
    r"^\s*<(section|article|div)\b(?P<attrs>[^>]*)>(?P<body>.*)</\1>\s*$",
    re.IGNORECASE | re.DOTALL,
)
PAGE_WRAPPER_HINT_PATTERN = re.compile(
    r'(?:\bdata-source-page\s*=|\bclass\s*=\s*(?:"[^"]*\b(?:source-page-fragment|source-page|source-fragment)\b[^"]*"|\'[^\']*\b(?:source-page-fragment|source-page|source-fragment)\b[^\']*\'))',
    re.IGNORECASE,
)
FILL_BLANK_PATTERN = re.compile(r"(?<!_)_{3,}(?!_)|＿{2,}|﹍{2,}|‗{2,}")
PARAGRAPH_PATTERN = re.compile(r"<p(?P<attrs>[^>]*)>(?P<body>.*?)</p>", re.DOTALL)
LIST_ITEM_PATTERN = re.compile(r"<li(?P<attrs>[^>]*)>(?P<body>.*?)</li>", re.DOTALL)
BLOCKQUOTE_PATTERN = re.compile(r"<blockquote(?P<attrs>[^>]*)>(?P<body>.*?)</blockquote>", re.DOTALL)
CHOICE_LIST_PATTERN = re.compile(r"<ul>(?P<body>.*?)</ul>", re.DOTALL)
CHOICE_OPTION_GROUP_PATTERN = re.compile(
    r"(?P<group>(?:<p>\s*[A-FＡ-Ｆ][\.\uFF0E、:：].*?</p>\s*){2,6})",
    re.DOTALL,
)
CHOICE_LABEL_PATTERN = re.compile(r"^[A-FＡ-Ｆ][\.\uFF0E、:：]")
FRACTION_COMPLEXITY_PATTERN = re.compile(
    r"\\(?:frac|dfrac|tfrac|sqrt|sum|prod|int|lim|left|right)\b|[+\-*/=<>]"
)
EXPLICIT_MARGIN_NOISE_PATTERNS = (
    re.compile(r"^MST高中基础知识与二级结论$"),
    re.compile(r"^老唐说题$"),
    re.compile(r"^第\s*\d+\s*章\s*立体几何$"),
)
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def read_asset_text(name: str) -> str:
    return (ASSETS_DIR / name).read_text(encoding="utf-8")


KAMI_KERNEL_CSS = read_asset_text("kami-default-kernel.css")
PHYCAT_BLOCKQUOTE_CSS = read_asset_text("phycat-blockquote.css")
TABLE_CONSISTENT_CSS = read_asset_text("table-consistent.css")
LEAD_TAGS_CSS = read_asset_text("lead-tags.css")

PRINT_BASE_CSS = """
@page {
  size: A4;
  margin: 0;
}

:root {
  --page-width: 210mm;
  --page-height: 297mm;
}

* {
  box-sizing: border-box;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

html {
  background: var(--desk);
  color: var(--ink);
}

body {
  margin: 0;
  background: radial-gradient(circle at top, #f8fbff 0%, var(--desk) 58%, #dde4ee 100%);
  color: var(--ink);
  font-family: var(--font-body);
  font-size: 12px;
  line-height: 1.56;
}

.sheet {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  width: var(--page-width);
  min-height: var(--page-height);
  height: var(--page-height);
  margin: 0 auto 12mm;
  padding: 14mm 13mm 15mm;
  background: var(--paper);
  box-shadow: 0 16px 40px rgba(33, 41, 53, 0.16);
  page-break-after: always;
  break-after: page;
  overflow: hidden;
}

.sheet:last-child {
  margin-bottom: 0;
}

#handout-source {
  position: absolute;
  left: -10000px;
  top: 0;
  width: calc(var(--page-width) - 26mm);
  visibility: hidden;
  pointer-events: none;
}

#handout-print-root {
  padding: 12mm 0;
}

html[data-handout-ready="loading"] #handout-print-root {
  visibility: hidden;
}

@media print {
  html,
  body {
    background: none;
  }

  #handout-print-root {
    padding: 0;
  }

  .sheet {
    margin: 0;
    box-shadow: none;
  }
}

.sheet-footer {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 6mm;
  color: var(--muted);
  font-size: 9px;
}

.sheet-footer {
  margin-top: 6mm;
  padding-top: 3mm;
  border-top: 1px solid var(--line);
}

.sheet-trail-label {
  flex: 1 1 auto;
  min-width: 0;
  margin-right: 6mm;
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sheet-page-label {
  flex: 0 0 auto;
  white-space: nowrap;
}

.sheet-emph {
  font-weight: 700;
  color: #FB8B05;
}

.doc-title {
  margin: 0 0 5mm;
  font-family: var(--font-display);
  font-size: 24px;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.sheet-body {
  min-height: 0;
  overflow: hidden;
}

.sheet[data-fit-state="overflow"] {
  outline: 1px dashed color-mix(in srgb, var(--accent) 45%, transparent);
}

.transcript-flow > :first-child {
  margin-top: 0;
}

.transcript-flow h1,
.transcript-flow h2,
.transcript-flow h3,
.transcript-flow h4 {
  margin: 0 0 3mm;
  font-family: var(--font-display);
  line-height: 1.22;
  color: var(--ink);
}

.transcript-flow h1 { font-size: 22px; }
.transcript-flow h2 { font-size: 18px; }
.transcript-flow h3 { font-size: 15px; }
.transcript-flow h4 { font-size: 13px; }

.transcript-flow p,
.transcript-flow li {
  margin-top: 0;
  margin-bottom: 0.62em;
}

.transcript-flow ul,
.transcript-flow ol {
  margin-top: 0;
  margin-bottom: 0.8em;
  padding-left: 1.3em;
}

.transcript-flow table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 4mm;
  font-size: 11.4px;
  background: var(--surface);
}

.transcript-flow th,
.transcript-flow td {
  padding: 2.4mm 2.6mm;
  border: 1px solid var(--line);
  text-align: center;
  vertical-align: middle;
}

.transcript-flow th {
  background: var(--surface-soft);
}

.transcript-flow td img,
.transcript-flow td mjx-container[display="true"][jax="SVG"],
.transcript-flow td .mjx-container[display="true"][jax="SVG"] {
  display: block;
  margin: 0 auto;
}

.transcript-flow td mjx-container[display="true"][jax="SVG"],
.transcript-flow td .mjx-container[display="true"][jax="SVG"] {
  max-width: 100%;
}

.transcript-flow blockquote {
  margin: 3mm 0 4mm;
  padding: 3mm 3.2mm;
  background: var(--surface-soft);
  border: 1px solid var(--line);
}

.transcript-flow pre {
  margin: 3mm auto 4mm;
  padding: 3mm 3.2mm;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  width: fit-content;
  max-width: 100%;
  text-align: center;
  white-space: pre-wrap;
}

.transcript-flow code,
.transcript-flow pre {
  font-family: var(--font-mono);
}

.transcript-flow pre code {
  display: block;
  text-align: center;
  white-space: pre-wrap;
}

.transcript-flow img {
  display: block;
  max-width: min(100%, 72mm);
  height: auto;
  margin: 3mm auto;
  border: none;
  background: transparent;
}

.transcript-flow .ocr-crop-image--small {
  max-width: min(100%, 34mm);
}

.transcript-flow .ocr-crop-image--medium {
  max-width: min(100%, 48mm);
}

.transcript-flow .ocr-crop-image--wide {
  max-width: min(100%, 64mm);
}

.transcript-flow .ocr-image-cluster {
  display: grid;
  gap: 2.4mm;
  justify-items: center;
  align-items: start;
  width: min(100%, 92mm);
  margin: 3mm auto;
}

.transcript-flow .ocr-image-cluster--2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.transcript-flow .ocr-image-cluster--3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.transcript-flow .ocr-image-cluster--4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.transcript-flow .ocr-image-cluster > img {
  margin: 0;
  max-width: 100%;
}

.transcript-flow td .ocr-image-cluster {
  width: 100%;
  margin: 0 auto;
}

.transcript-flow hr {
  border: 0;
  border-top: 1px dashed var(--line-strong);
  margin: 5mm 0;
}

.flow-block {
  break-inside: avoid;
  page-break-inside: avoid;
}

.mjx-container {
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
}

.mjx-container[display="true"] {
  margin: 3mm 0;
}

.transcript-flow .choice-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2.6mm 4mm;
  list-style: none;
  padding-left: 0;
  margin: 2.6mm 0 0;
}

.transcript-flow .choice-option {
  margin: 0;
  min-width: 0;
}

.transcript-flow .choice-option p {
  margin: 0;
}

.transcript-flow .choice-options > :last-child:nth-child(odd) {
  grid-column: 1 / -1;
}

/* lead-tag / lead-tag-example / lead-para styles are in assets/lead-tags.css */
"""

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

PAGINATION_SCRIPT = """
<script>
function nextHandoutFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

function normalizeFlowNode(node) {
  if (node.nodeType === Node.ELEMENT_NODE) {
    return node;
  }
  if (node.nodeType === Node.TEXT_NODE && node.textContent && node.textContent.trim()) {
    const paragraph = document.createElement('p');
    paragraph.textContent = node.textContent.trim();
    return paragraph;
  }
  return null;
}

function createFlowBlock(node, sourcePage) {
  const block = document.createElement('div');
  block.className = 'flow-block';
  block.dataset.sourcePage = sourcePage;
  block.appendChild(node);
  return block;
}

function collectFlowBlocks(sourceRoot) {
  const blocks = [];
  const fragments = Array.from(sourceRoot.querySelectorAll('.source-fragment'));
  for (const fragment of fragments) {
    const sourcePage = fragment.dataset.sourcePage || '';
    for (const child of Array.from(fragment.childNodes)) {
      const normalized = normalizeFlowNode(child);
      if (!normalized) {
        continue;
      }
      blocks.push(createFlowBlock(normalized, sourcePage));
    }
  }
  return blocks;
}

async function waitForHandoutAssets(root) {
  const images = Array.from(root.querySelectorAll('img'));
  await Promise.all(images.map((img) => {
    if (img.complete) {
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      const done = () => resolve();
      img.addEventListener('load', done, { once: true });
      img.addEventListener('error', done, { once: true });
    });
  }));

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
}

function createSheet(pageNumber, title, sourceLabel, showTitle) {
  const sheet = document.createElement('article');
  sheet.className = 'sheet';
  sheet.dataset.pageNumber = String(pageNumber);
  sheet.dataset.fitState = 'ready';

  const body = document.createElement('section');
  body.className = 'sheet-body transcript-flow';
  if (showTitle && title) {
    const titleNode = document.createElement('h1');
    titleNode.className = 'doc-title';
    titleNode.textContent = title;
    body.appendChild(titleNode);
  }

  const footer = document.createElement('footer');
  footer.className = 'sheet-footer';
  const footerTrail = document.createElement('span');
  footerTrail.className = 'sheet-trail-label';
  const footerPage = document.createElement('span');
  footerPage.className = 'sheet-page-label';
  footerPage.textContent = `第 ${pageNumber} 页`;
  footer.append(footerTrail, footerPage);

  sheet.append(body, footer);
  return sheet;
}

function sheetBody(sheet) {
  return sheet.querySelector('.sheet-body');
}

function sheetOverflows(sheet) {
  const body = sheetBody(sheet);
  if (!body) {
    return false;
  }
  return body.scrollHeight > body.clientHeight + 1;
}

function setSheetState(sheet) {
  sheet.dataset.fitState = sheetOverflows(sheet) ? 'overflow' : 'ready';
}

function appendBlockToSheet(sheet, block) {
  const body = sheetBody(sheet);
  if (!body) {
    return true;
  }
  body.appendChild(block);
  const overflow = sheetOverflows(sheet);
  const blockCount = body.querySelectorAll(':scope > .flow-block').length;
  if (overflow && blockCount > 1) {
    body.removeChild(block);
    setSheetState(sheet);
    return false;
  }
  setSheetState(sheet);
  return true;
}

function trailHeadingLevel(heading) {
  const text = (heading.textContent || '').replace(/\\s+/g, ' ').trim();
  // Lecture/chapter-shaped headings (第N讲/章/节/部分/篇/单元, 单元N, numeric
  // outline "1. 力学", Module/Lesson/Chapter N) sit one level above a plain
  // h2 — they are the document's top bookmark tier. Matches the postprocess
  // isChapterBreakHeading/isLectureHeading shape.
  const isChapterShaped = /^(?:第\\s*[0-9一二三四五六七八九十百零]+\\s*(?:讲|章|节|部分|篇|单元)|单元\\s*[0-9一二三四五六七八九十百零]+|[0-9]+\\s*[\\.、]\\s*[\\u4e00-\\u9fff]|(?:Module|Lesson|Chapter)\\s+\\d)/.test(text);
  const rank = /H([1-6])/.exec(heading.tagName || '');
  const numeric = rank ? Number(rank[1]) : 6;
  if (isChapterShaped) return 1;
  if (numeric <= 2) return 2;
  if (numeric === 3) return 3;
  return 4;
}

function renumberSheets(root) {
  const sheets = Array.from(root.querySelectorAll('.sheet'));
  const total = sheets.length;
  // Document-level heading stack: every h2/h3/h4 advances it, and a sheet's
  // breadcrumb is the full ancestor chain at the DEEPEST (last) heading it
  // contains — so a page spanning a level change shows the level it ends on
  // (the user's "临界页取最后一级" rule).
  const stack = [];
  sheets.forEach((sheet, index) => {
    const pageNumber = index + 1;
    sheet.dataset.pageNumber = String(pageNumber);
    const isCover = sheet.classList.contains('concept-map-sheet') ||
      sheet.dataset.sheetRole === 'cover' ||
      sheet.dataset.coverSheet === 'true';
    if (!isCover) {
      const body = sheet.querySelector('.sheet-body');
      let pageStackSnapshot = null;
      if (body) {
        const headings = Array.from(body.querySelectorAll('.flow-block h2, .flow-block h3, .flow-block h4, h2, h3, h4'));
        headings.forEach((heading) => {
          const title = (heading.textContent || '').replace(/\\s+/g, ' ').trim();
          if (!title) return;
          const level = trailHeadingLevel(heading);
          while (stack.length && stack[stack.length - 1].level >= level) {
            stack.pop();
          }
          stack.push({ level, title });
          pageStackSnapshot = stack.map((entry) => entry.title);
        });
      }
      const trailLabel = sheet.querySelector('.sheet-trail-label');
      if (trailLabel) {
        // A page with no heading of its own is a continuation page (content
        // spilled from the previous page). It still belongs to the current
        // chapter/level, so inherit the running global stack snapshot rather
        // than showing an empty breadcrumb. This is the "同章节页都显示该
        // 章节面包屑" rule: only pages before ANY heading (or after a
        // completed subtree) legitimately have no breadcrumb.
        if (!pageStackSnapshot && stack.length) {
          pageStackSnapshot = stack.map((entry) => entry.title);
        }
        if (pageStackSnapshot && pageStackSnapshot.length) {
          // Render the path as "前 › 前 › 前 › <emph>最后一级</emph>" — every
          // segment except the last is muted, the last (current) level is
          // bold + accent (the page's actual heading tier).
          const parts = pageStackSnapshot.slice();
          const last = parts.pop();
          trailLabel.replaceChildren();
          if (parts.length) {
            trailLabel.append(document.createTextNode(parts.join(' › ') + ' › '));
          }
          const emph = document.createElement('span');
          emph.className = 'sheet-emph';
          emph.textContent = last;
          trailLabel.append(emph);
        } else {
          trailLabel.textContent = '';
        }
      }
    }
    sheet.querySelectorAll('.sheet-page-label').forEach((node) => {
      // "第 <emph>X</emph> / N 页" — bold + accent on the current page number.
      node.replaceChildren(
        document.createTextNode('第 '),
        (() => {
          const e = document.createElement('span');
          e.className = 'sheet-emph';
          e.textContent = String(pageNumber);
          return e;
        })(),
        document.createTextNode(` / ${total} 页`),
      );
    });
  });
}

async function paginateHandout() {
  const sourceRoot = document.getElementById('handout-source');
  const printRoot = document.getElementById('handout-print-root');
  if (!sourceRoot || !printRoot) {
    return;
  }

  document.documentElement.dataset.handoutReady = 'loading';
  await waitForHandoutAssets(sourceRoot);

  const title = printRoot.dataset.title || '';
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

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    void paginateHandout();
  }, { once: true });
} else {
  void paginateHandout();
}
</script>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, help="Path to source-transcript markdown")
    parser.add_argument("--out-html", required=True, help="Output HTML path")
    parser.add_argument("--title", help="Document title shown on the first page")
    parser.add_argument("--source-label", default="OCR Transcript", help="Short header label")
    return parser


def _strip_callout_display_math_prefixes(text: str) -> str:
    """Remove '>' prefixes from every line of a callout-embedded $$...$$ block.

    Example:
        > $$          $$
        > a      ->   a
        > b           b
        > $$          $$
    """
    def replacer(match: re.Match[str]) -> str:
        prefix = match.group(1)
        body = match.group(2)
        escaped_prefix = re.escape(prefix.rstrip())
        stripped_body = re.sub(rf"(?m)^{escaped_prefix}[ \t]?", "", body)
        return f"$$\n{stripped_body}\n$$"

    return CALLOUT_DISPLAY_MATH_PATTERN.sub(replacer, text)


def clean_markdown(text: str) -> str:
    normalized = text.replace("\r\n", "\n").strip()
    literal_segments: list[str] = []

    def protect_literal_segment(match: re.Match[str]) -> str:
        token = f"@@LITERALSEGMENT{len(literal_segments)}@@"
        literal_segments.append(match.group(0))
        return token

    normalized = FENCED_CODE_BLOCK_PATTERN.sub(protect_literal_segment, normalized)
    normalized = INLINE_CODE_SPAN_PATTERN.sub(protect_literal_segment, normalized)
    normalized = HTML_COMMENT_PATTERN.sub("", normalized)
    # Strip Obsidian callout markers: "> [!question] text" → "> text"
    # Evolved 2026-06-15: Obsidian callout syntax leaked into HTML as raw text.
    # Use horizontal whitespace only after the marker so a marker at the end
    # of a line does not swallow the newline and merge with the next quote line.
    normalized = re.sub(
        r"(?m)^(\s*>\s*)\[!\w+\][ \t]*", r"\1", normalized
    )
    # Strip leading blockquote markers from interior lines of display-math
    # blocks embedded in Obsidian callouts. Otherwise protect_math_segments()
    # captures the '>' prefixes as part of the formula, and they render as
    # literal '>' inside the math. Legitimate '>' inequalities inside the
    # formula are preserved because only the structural blockquote prefix is
    # removed. Evolved 2026-06-20.
    normalized = _strip_callout_display_math_prefixes(normalized)
    # Doc2X emits TeX with \( ... \) / \[ ... \] delimiters, but MarkdownIt
    # strips the backslashes in plain paragraph text. Normalize before render so
    # MathJax still receives intact delimiters across both Markdown and raw HTML.
    normalized = normalized.replace(r"\[", "$$").replace(r"\]", "$$")
    normalized = normalized.replace(r"\(", "$").replace(r"\)", "$")

    for index, segment in enumerate(literal_segments):
        normalized = normalized.replace(f"@@LITERALSEGMENT{index}@@", segment)
    return normalized


def protect_math_segments(text: str) -> tuple[str, list[str]]:
    segments: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        token = f"@@MATHSEGMENT{len(segments)}@@"
        segments.append(normalize_math_segment(match.group(0)))
        return token

    return MATH_SEGMENT_PATTERN.sub(replacer, text), segments


def restore_math_segments(text: str, segments: list[str]) -> str:
    restored = text
    for index, segment in enumerate(segments):
        # Math is restored after MarkdownIt renders HTML. Keep it as text for
        # MathJax by escaping HTML-sensitive characters. Without this,
        # expressions like `$0<a<2$` are parsed by the browser as malformed
        # `<a...` tags before MathJax can typeset them.
        restored = restored.replace(f"@@MATHSEGMENT{index}@@", html.escape(segment, quote=False))
    return restored


def is_explicit_margin_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    return any(pattern.fullmatch(stripped) for pattern in EXPLICIT_MARGIN_NOISE_PATTERNS)


def edge_line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if len(stripped) > 40:
        return None
    if "<" in stripped or ">" in stripped:
        return None
    return stripped


def first_nonempty_line(lines: list[str]) -> str | None:
    for line in lines:
        if line.strip():
            return line.strip()
    return None


def last_nonempty_line(lines: list[str]) -> str | None:
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    return None


def strip_page_margin_noise(contents: list[str]) -> list[str]:
    top_counts: dict[str, int] = {}
    bottom_counts: dict[str, int] = {}

    for content in contents:
        lines = content.splitlines()
        top = edge_line_key(first_nonempty_line(lines) or "")
        bottom = edge_line_key(last_nonempty_line(lines) or "")
        if top:
            top_counts[top] = top_counts.get(top, 0) + 1
        if bottom:
            bottom_counts[bottom] = bottom_counts.get(bottom, 0) + 1

    cleaned_contents: list[str] = []
    for content in contents:
        lines = content.splitlines()
        start = 0
        end = len(lines)

        while start < end:
            stripped = lines[start].strip()
            if not stripped:
                start += 1
                continue
            repeated_top = top_counts.get(stripped, 0) >= 2 and len(stripped) <= 40
            if is_explicit_margin_noise(stripped) or repeated_top:
                start += 1
                continue
            break

        while end > start:
            stripped = lines[end - 1].strip()
            if not stripped:
                end -= 1
                continue
            repeated_bottom = bottom_counts.get(stripped, 0) >= 2 and len(stripped) <= 40
            if is_explicit_margin_noise(stripped) or repeated_bottom:
                end -= 1
                continue
            break

        cleaned_contents.append("\n".join(lines[start:end]).strip())

    return cleaned_contents


def split_pages(markdown_text: str) -> list[tuple[str, str]]:
    text = clean_markdown(markdown_text)
    if text.startswith("# Source Transcript"):
        text = text.split("\n", 1)[1].lstrip()

    matches = list(PAGE_SPLIT_PATTERN.finditer(text))
    if not matches:
        return [("1", text.strip())]

    raw_pages: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        page_number = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        raw_pages.append((page_number, content))

    cleaned_contents = strip_page_margin_noise([content for _page_number, content in raw_pages])
    return [
        (page_number, cleaned_contents[index])
        for index, (page_number, _content) in enumerate(raw_pages)
    ]


def default_title(pages: list[tuple[str, str]], explicit_title: str | None) -> str:
    if explicit_title:
        return explicit_title
    if not pages:
        return "OCR Handout"
    first_page_content = pages[0][1].strip().splitlines()

    # First: look for a leading "# Title" heading (most reliable).
    # Evolved 2026-06-15: previously the # heading was skipped, causing the
    # builder to grab a body paragraph as the title.
    for line in first_page_content:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            heading = stripped[2:].strip()
            protected_title, math_segments = protect_math_segments(heading)
            return restore_math_segments(protected_title, math_segments)

    # Fallback: first non-heading, non-special line.
    for line in first_page_content:
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "|", "!", "[", ">", "`")):
            protected_title, math_segments = protect_math_segments(stripped)
            return restore_math_segments(protected_title, math_segments)
    return "OCR Handout"


def validate_fragment_html(page_number: str, fragment_html: str) -> str:
    normalized_fragment = fragment_html.strip()
    if not normalized_fragment:
        raise ValueError(f"Fragment for page {page_number} must not be empty.")
    match = FORBIDDEN_FRAGMENT_PATTERN.search(fragment_html)
    if match:
        token = match.group(0)
        if token.startswith("<") and not token.endswith(">") and not token.startswith("</"):
            token = f"{token}>"
        raise ValueError(
            f"Fragment for page {page_number} must be body-only HTML; found forbidden markup {token}"
        )
    if not RENDERED_HTML_TAG_PATTERN.search(normalized_fragment):
        raise ValueError(f"Fragment for page {page_number} must contain rendered HTML markup.")
    return normalized_fragment


def extract_img_src(img_tag: str) -> str | None:
    match = IMG_SRC_PATTERN.search(img_tag)
    if not match:
        return None
    return match.group(1) or match.group(2)


def classify_crop_image(src: str | None) -> str:
    if not src:
        return "ocr-crop-image"
    match = DOC2X_CROP_PATTERN.search(src)
    if not match:
        return "ocr-crop-image"

    width = int(match.group(1))
    height = int(match.group(2))
    classes = ["ocr-crop-image"]
    aspect_ratio = width / max(height, 1)

    if max(width, height) <= 280:
        classes.append("ocr-crop-image--small")
    elif max(width, height) <= 420:
        classes.append("ocr-crop-image--medium")

    if aspect_ratio >= 2.0:
        classes.append("ocr-crop-image--wide")

    return " ".join(classes)


def add_img_class(img_tag: str, classes: str) -> str:
    class_pattern = re.compile(r"""\bclass=(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
    match = class_pattern.search(img_tag)
    if match:
        existing = match.group(1) or match.group(2) or ""
        merged = " ".join(part for part in [existing.strip(), classes.strip()] if part).strip()
        quote = '"' if match.group(1) is not None else "'"
        replacement = f'class={quote}{merged}{quote}'
        return class_pattern.sub(replacement, img_tag, count=1)
    return img_tag.replace("<img", f'<img class="{classes}"', 1)


def decorate_img_tag(img_tag: str) -> str:
    return add_img_class(img_tag, classify_crop_image(extract_img_src(img_tag)))


def build_image_cluster(sequence_html: str) -> str:
    images = [match.group(0) for match in IMG_TAG_PATTERN.finditer(sequence_html)]
    image_count = len(images)
    if image_count < 2:
        return sequence_html
    cluster_class = min(image_count, 4)
    return f'<span class="ocr-image-cluster ocr-image-cluster--{cluster_class}">{"".join(images)}</span>'


def normalize_fragment_media(fragment_html: str) -> str:
    # Author <figure> blocks carry their own layout (flex/grid, max-width %,
    # captions). Protect them from the OCR-crop normalizer below so an
    # intentional figure is not collapsed into a ~20mm cluster row. Later
    # semantic passes (fill-blank, analysis, blockquote) still run over the
    # restored figure, which is fine — only the media-specific transforms are
    # suppressed. Sentinels use Unicode private-use chars so they cannot
    # collide with real math/text content.
    stashed_figures: list[str] = []

    def stash_figure(match: re.Match[str]) -> str:
        stashed_figures.append(match.group(0))
        return f"\uE000FIGURE{len(stashed_figures) - 1}\uE001"

    protected = FIGURE_BLOCK_PATTERN.sub(stash_figure, fragment_html)

    normalized = IMG_ONLY_PARAGRAPH_PATTERN.sub(r"\1", protected)
    normalized = IMG_SEQUENCE_PATTERN.sub(lambda match: build_image_cluster(match.group("sequence")), normalized)
    normalized = IMG_TAG_PATTERN.sub(lambda match: decorate_img_tag(match.group(0)), normalized)

    for index, figure_html in enumerate(stashed_figures):
        normalized = normalized.replace(f"\uE000FIGURE{index}\uE001", figure_html)
    return normalized


def strip_html_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


# Solution/note lead-in labels. A label is followed by a boundary (end,
# whitespace, or punctuation), not by a CJK char that would make it an
# ordinary word (解析几何, 解决, 注意到). 方案N / 法N carry a numeral
# (Chinese, Arabic, or Roman) so bare words like 方案案 / 法案 do not match.
ANALYSIS_LABEL_PATTERN = re.compile(
    r"\A(?:分析|解析|解答|证明|另解|注意|方案[一二三四五六七八九十零两0-9ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|法[一二三四五六七八九十零两0-9ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|解)"
    r"(?=$|[\s\u3000：:。，,\.（(、])"
)


def paragraph_starts_with_analysis_label(body_html: str) -> bool:
    plain_text = strip_html_tags(body_html).strip()
    if plain_text.startswith(("解析：", "解析:", "【解析】")):
        return True
    # Hand-authored markdown writes the lead-in as '**解析** ...' or '**解**',
    # which renders to <strong>解析</strong> ...; after tag-stripping the
    # plain text begins with the bare label. The boundary-guarded pattern
    # catches it without styling nouns like 解析几何 / 解决.
    return bool(ANALYSIS_LABEL_PATTERN.match(plain_text))


def normalize_fill_blank_markers(fragment_html: str) -> str:
    def replace_in_tag(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        body = FILL_BLANK_PATTERN.sub("__________", match.group("body"))
        return f"<p{attrs}>{body}</p>"

    normalized = PARAGRAPH_PATTERN.sub(replace_in_tag, fragment_html)
    normalized = re.sub(
        r"<li(?P<attrs>[^>]*)>(?P<body>.*?)</li>",
        lambda match: (
            f'<li{match.group("attrs")}>'
            f'{FILL_BLANK_PATTERN.sub("__________", match.group("body"))}'
            "</li>"
        ),
        normalized,
        flags=re.DOTALL,
    )
    return normalized


# HTML pattern for the leading 分析/解析/解答/证明/解/另解 label inside a <p> body.
# Matches optional <strong>, the label word, optional </strong>, then separator.
LEADING_ANALYSIS_LABEL_HTML_PATTERN = re.compile(
    r"\A\s*(?:<strong>\s*)?"
    r"(?:【|\[)?"
    r"(?P<label>分析|解析|解答|证明|另解|注意|方案[一二三四五六七八九十零两0-9ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|法[一二三四五六七八九十零两0-9ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|解)"
    r"(?:】|\])?"
    r"(?:\s*</strong>)?"
    r"\s*[：:。\.\s]*"
)

# HTML pattern for leading example/exercise labels. Matches labels such as
# 例1 / 例题1 / 【例题】 / 【例题1】 / 【练习】 / 【练习 1】, optional <strong>.
# Bare `例` is intentionally excluded unless it carries a number, so ordinary
# prose like "例如" is not mis-decorated as an example badge.
LEADING_EXAMPLE_LABEL_HTML_PATTERN = re.compile(
    r"\A\s*(?:<strong>\s*)?"
    r"(?:【|\[)?"
    r"(?P<label>(?:(?:例题|练习)(?:\s*[\d一二三四五六七八九十百零]+)?|例\s*[\d一二三四五六七八九十百零]+))"
    r"(?:】|\])?"
    r"(?:\s*</strong>)?"
    r"\s*[：:。\.\s]*"
)


def decorate_analysis_paragraphs(fragment_html: str) -> str:
    def replace_paragraph(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        body = match.group("body")
        if not paragraph_starts_with_analysis_label(body):
            return match.group(0)

        # Try to extract the label from the HTML body.
        label_match = LEADING_ANALYSIS_LABEL_HTML_PATTERN.match(body)
        if label_match:
            label = label_match.group("label")
            remaining = body[label_match.end():]
            badge_html = f'<span class="lead-tag">{html.escape(label)}</span>'
            new_body = badge_html + remaining

            if 'class="' in attrs or "class='" in attrs:
                class_pattern = re.compile(r"""\bclass=(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
                class_match = class_pattern.search(attrs)
                if class_match:
                    existing = class_match.group(1) or class_match.group(2) or ""
                    merged = " ".join(part for part in [existing.strip(), "lead-para"] if part).strip()
                    quote = '"' if class_match.group(1) is not None else "'"
                    new_attrs = class_pattern.sub(f'class={quote}{merged}{quote}', attrs, count=1)
                    return f"<p{new_attrs}>{new_body}</p>"

            return f'<p{attrs} class="lead-para">{new_body}</p>'

        # Fallback: no label match in HTML, keep old behavior
        return match.group(0)

    return PARAGRAPH_PATTERN.sub(replace_paragraph, fragment_html)


def decorate_example_paragraphs(fragment_html: str) -> str:
    """Wrap leading 例N labels in a lead-tag-example badge."""
    def replace_paragraph(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        body = match.group("body")
        label_match = LEADING_EXAMPLE_LABEL_HTML_PATTERN.match(body)
        if not label_match:
            return match.group(0)

        label = label_match.group("label")
        remaining = body[label_match.end():]
        badge_html = f'<span class="lead-tag-example">{html.escape(label)}</span>'
        new_body = badge_html + remaining

        if 'class="' in attrs or "class='" in attrs:
            class_pattern = re.compile(r"""\bclass=(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
            class_match = class_pattern.search(attrs)
            if class_match:
                existing = class_match.group(1) or class_match.group(2) or ""
                merged = " ".join(part for part in [existing.strip(), "lead-para"] if part).strip()
                quote = '"' if class_match.group(1) is not None else "'"
                new_attrs = class_pattern.sub(f'class={quote}{merged}{quote}', attrs, count=1)
                return f"<p{new_attrs}>{new_body}</p>"

        return f'<p{attrs} class="lead-para">{new_body}</p>'

    return PARAGRAPH_PATTERN.sub(replace_paragraph, fragment_html)


def choice_item_is_option_html(item_html: str) -> bool:
    plain_text = strip_html_tags(item_html).strip()
    return bool(CHOICE_LABEL_PATTERN.match(plain_text))


def decorate_choice_list(list_html: str) -> str:
    items = list(LIST_ITEM_PATTERN.finditer(list_html))
    if not items:
        return list_html
    if not all(choice_item_is_option_html(match.group("body")) for match in items):
        return list_html

    decorated_items = []
    for item in items:
        attrs = item.group("attrs")
        body = item.group("body")
        if 'class="' in attrs or "class='" in attrs:
            class_pattern = re.compile(r"""\bclass=(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
            class_match = class_pattern.search(attrs)
            if class_match:
                existing = class_match.group(1) or class_match.group(2) or ""
                merged = " ".join(part for part in [existing.strip(), "choice-option"] if part).strip()
                quote = '"' if class_match.group(1) is not None else "'"
                attrs = class_pattern.sub(f'class={quote}{merged}{quote}', attrs, count=1)
        else:
            attrs = f'{attrs} class="choice-option"'
        decorated_items.append(f"<li{attrs}>{body}</li>")

    return f'<ul class="choice-options">{"".join(decorated_items)}</ul>'


def decorate_choice_paragraph_group(group_html: str) -> str:
    paragraphs = re.findall(r"<p>(.*?)</p>", group_html, flags=re.DOTALL)
    items = [f'<p class="choice-option">{body}</p>' for body in paragraphs]
    return f'<div class="choice-options">{"".join(items)}</div>'


def decorate_choice_content(body_html: str) -> str:
    normalized = CHOICE_LIST_PATTERN.sub(lambda match: decorate_choice_list(match.group(0)), body_html)
    normalized = CHOICE_OPTION_GROUP_PATTERN.sub(
        lambda match: decorate_choice_paragraph_group(match.group("group")),
        normalized,
    )
    return normalized


def decorate_blockquotes(fragment_html: str) -> str:
    def replace_blockquote(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        body = decorate_choice_content(match.group("body"))
        if 'class="' in attrs or "class='" in attrs:
            class_pattern = re.compile(r"""\bclass=(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
            class_match = class_pattern.search(attrs)
            if class_match:
                existing = class_match.group(1) or class_match.group(2) or ""
                merged = " ".join(part for part in [existing.strip(), "phycat-blockquote"] if part).strip()
                quote = '"' if class_match.group(1) is not None else "'"
                attrs = class_pattern.sub(f'class={quote}{merged}{quote}', attrs, count=1)
        else:
            attrs = f'{attrs} class="phycat-blockquote"'
        return f"<blockquote{attrs}>{body}</blockquote>"

    return BLOCKQUOTE_PATTERN.sub(replace_blockquote, fragment_html)


def fraction_argument_is_complex(expr: str) -> bool:
    compact = expr.strip()
    if not compact:
        return False
    if FRACTION_COMPLEXITY_PATTERN.search(compact):
        return True
    return False


def read_braced_tex_argument(source: str, start: int) -> tuple[str, int] | None:
    if start >= len(source) or source[start] != "{":
        return None

    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1 : index], index + 1
    return None


def normalize_fraction_commands(tex: str) -> str:
    parts: list[str] = []
    index = 0

    while index < len(tex):
        if not tex.startswith(r"\frac", index):
            parts.append(tex[index])
            index += 1
            continue

        numerator_result = read_braced_tex_argument(tex, index + len(r"\frac"))
        if numerator_result is None:
            parts.append(tex[index])
            index += 1
            continue

        numerator_raw, denominator_start = numerator_result
        denominator_result = read_braced_tex_argument(tex, denominator_start)
        if denominator_result is None:
            parts.append(tex[index])
            index += 1
            continue

        denominator_raw, next_index = denominator_result
        numerator = normalize_fraction_commands(numerator_raw)
        denominator = normalize_fraction_commands(denominator_raw)
        command = r"\tfrac" if (
            fraction_argument_is_complex(numerator) or fraction_argument_is_complex(denominator)
        ) else r"\dfrac"
        parts.append(f"{command}{{{numerator}}}{{{denominator}}}")
        index = next_index

    return "".join(parts)


def normalize_math_segment(segment: str) -> str:
    if segment.startswith("$$") and segment.endswith("$$"):
        return f"$${normalize_fraction_commands(segment[2:-2])}$$"
    if segment.startswith("$") and segment.endswith("$"):
        return f"${normalize_fraction_commands(segment[1:-1])}$"
    return segment


def normalize_fragment_semantics(fragment_html: str) -> str:
    normalized = normalize_fragment_media(fragment_html)
    normalized = normalize_fill_blank_markers(normalized)
    normalized = decorate_analysis_paragraphs(normalized)
    normalized = decorate_example_paragraphs(normalized)
    normalized = decorate_blockquotes(normalized)
    return normalized


def unwrap_page_wrapper_fragment(fragment_html: str) -> str:
    stripped = fragment_html.strip()
    match = PAGE_WRAPPER_PATTERN.match(stripped)
    if not match:
        return fragment_html

    attrs = match.group("attrs") or ""
    if not PAGE_WRAPPER_HINT_PATTERN.search(attrs):
        return fragment_html

    body = match.group("body").strip()
    return body or fragment_html


def build_source_fragment_html(page_number: str, page_body_html: str) -> str:
    return (
        f'<section class="source-fragment" data-source-page="{html.escape(page_number)}">'
        f"{page_body_html}"
        "</section>"
    )


def build_html_document_from_fragments(
    pages: list[tuple[str, str]],
    title: str,
    source_label: str,
) -> str:
    source_fragments_html: list[str] = []
    for page_number, page_markdown in pages:
        page_body_html = normalize_fragment_semantics(validate_fragment_html(page_number, page_markdown))
        page_body_html = unwrap_page_wrapper_fragment(page_body_html)
        source_fragments_html.append(build_source_fragment_html(page_number, page_body_html))

    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{html.escape(title)}</title>",
            "  <style>",
            "/* Vendored Kami tokens define the document language. */",
            KAMI_KERNEL_CSS,
            "/* Vendored blockquote template styles example-callout rendering. */",
            PHYCAT_BLOCKQUOTE_CSS,
            "/* OCR-specific CSS keeps scan-specific pagination, table, and media behavior local to this skill. */",
            PRINT_BASE_CSS,
            "/* Locator badges for 解析/例N leading labels. Evolved 2026-06-15. */",
            LEAD_TAGS_CSS,
            "/* Consistent table styling: must come AFTER print-base so transparent bg + uniform th/td win. Evolved 2026-06-15. */",
            TABLE_CONSISTENT_CSS,
            "  </style>",
            MATHJAX_BOOTSTRAP,
            PAGINATION_SCRIPT,
            "</head>",
            "<body>",
            f'  <div id="handout-source" class="transcript-flow">{"".join(source_fragments_html)}</div>',
            (
                f'  <div id="handout-print-root" data-title="{html.escape(title, quote=True)}" '
                f'data-source-label="{html.escape(source_label, quote=True)}"></div>'
            ),
            "</body>",
            "</html>",
            "",
        ]
    )


LEADING_TITLE_HEADING_PATTERN = re.compile(r"\A\s*#\s+(?P<title>.+?)\s*$", re.MULTILINE)


def drop_leading_title_heading(
    pages: list[tuple[str, str]], title: str
) -> list[tuple[str, str]]:
    """Drop a page-1 '# Title' heading when it equals the explicit title.

    The title is already rendered as the per-sheet doc-title header, so
    leaving the matching content H1 in place shows the title twice (once as
    the sheet header, once as a content H1). Only an exact match is dropped;
    any other first heading is preserved as source-faithful content.
    """
    if not title or not pages:
        return pages
    page_number, first_content = pages[0]
    match = LEADING_TITLE_HEADING_PATTERN.match(first_content)
    if not match or match.group("title").strip() != title.strip():
        return pages
    remainder = first_content[match.end():].lstrip()
    if not remainder:
        # The heading is the only page-1 content; dropping it would leave an
        # empty fragment that fails validation. Keep it as content instead.
        return pages
    return [(page_number, remainder), *pages[1:]]


def build_html_document(pages: list[tuple[str, str]], title: str, source_label: str) -> str:
    pages = drop_leading_title_heading(pages, title)
    md = MarkdownIt("commonmark").enable("table")
    rendered_pages: list[tuple[str, str]] = []

    for page_number, page_markdown in pages:
        protected_markdown, math_segments = protect_math_segments(page_markdown)
        page_body = restore_math_segments(md.render(protected_markdown), math_segments)
        rendered_pages.append((page_number, page_body))

    return build_html_document_from_fragments(rendered_pages, title=title, source_label=source_label)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    md_path = Path(args.md).expanduser().resolve()
    out_html = Path(args.out_html).expanduser().resolve()
    if not md_path.exists():
        raise SystemExit(f"Markdown file not found: {md_path}")

    pages = split_pages(md_path.read_text(encoding="utf-8"))
    title = default_title(pages, args.title)
    html_document = build_html_document(pages, title=title, source_label=args.source_label)

    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_document, encoding="utf-8")
    print(str(out_html))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
