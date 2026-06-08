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
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def read_asset_text(name: str) -> str:
    return (ASSETS_DIR / name).read_text(encoding="utf-8")


KAMI_KERNEL_CSS = read_asset_text("kami-default-kernel.css")

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
  width: var(--page-width);
  min-height: var(--page-height);
  margin: 0 auto 12mm;
  padding: 14mm 13mm 15mm;
  background: var(--paper);
  box-shadow: 0 16px 40px rgba(33, 41, 53, 0.16);
  page-break-after: always;
  break-after: page;
}

.sheet:last-child {
  margin-bottom: 0;
}

.sheet-header,
.sheet-footer {
  display: flex;
  justify-content: space-between;
  gap: 6mm;
  color: var(--muted);
  font-size: 9px;
}

.sheet-header {
  padding-bottom: 3mm;
  margin-bottom: 4mm;
  border-bottom: 1px solid var(--line);
}

.sheet-footer {
  margin-top: 6mm;
  padding-top: 3mm;
  border-top: 1px solid var(--line);
}

.doc-title {
  margin: 0 0 5mm;
  font-family: var(--font-display);
  font-size: 24px;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.transcript-body > :first-child {
  margin-top: 0;
}

.transcript-body h1,
.transcript-body h2,
.transcript-body h3,
.transcript-body h4 {
  margin: 0 0 3mm;
  font-family: var(--font-display);
  line-height: 1.22;
  color: var(--ink);
}

.transcript-body h1 { font-size: 22px; }
.transcript-body h2 { font-size: 18px; }
.transcript-body h3 { font-size: 15px; }
.transcript-body h4 { font-size: 13px; }

.transcript-body p,
.transcript-body li {
  margin-top: 0;
  margin-bottom: 0.62em;
}

.transcript-body ul,
.transcript-body ol {
  margin-top: 0;
  margin-bottom: 0.8em;
  padding-left: 1.3em;
}

.transcript-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 4mm;
  font-size: 11.4px;
  background: var(--surface);
}

.transcript-body th,
.transcript-body td {
  padding: 2.4mm 2.6mm;
  border: 1px solid var(--line);
  text-align: center;
  vertical-align: middle;
}

.transcript-body th {
  background: var(--surface-soft);
}

.transcript-body td img,
.transcript-body td mjx-container[display="true"][jax="SVG"],
.transcript-body td .mjx-container[display="true"][jax="SVG"] {
  display: block;
  margin: 0 auto;
}

.transcript-body td mjx-container[display="true"][jax="SVG"],
.transcript-body td .mjx-container[display="true"][jax="SVG"] {
  max-width: 100%;
}

.transcript-body blockquote,
.transcript-body pre {
  margin: 3mm 0 4mm;
  padding: 3mm 3.2mm;
  background: var(--surface-soft);
  border: 1px solid var(--line);
}

.transcript-body code,
.transcript-body pre {
  font-family: var(--font-mono);
}

.transcript-body img {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 3mm auto;
  border: none;
  background: transparent;
}

.transcript-body hr {
  border: 0;
  border-top: 1px dashed var(--line-strong);
  margin: 5mm 0;
}

.mjx-container {
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
}

.mjx-container[display="true"] {
  margin: 3mm 0;
}
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
  }
};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, help="Path to source-transcript markdown")
    parser.add_argument("--out-html", required=True, help="Output HTML path")
    parser.add_argument("--title", help="Document title shown on the first page")
    parser.add_argument("--source-label", default="OCR Transcript", help="Short header label")
    return parser


def clean_markdown(text: str) -> str:
    without_comments = HTML_COMMENT_PATTERN.sub("", text)
    return without_comments.replace("\r\n", "\n").strip()


def split_pages(markdown_text: str) -> list[tuple[str, str]]:
    text = clean_markdown(markdown_text)
    if text.startswith("# Source Transcript"):
        text = text.split("\n", 1)[1].lstrip()

    matches = list(PAGE_SPLIT_PATTERN.finditer(text))
    if not matches:
        return [("1", text.strip())]

    pages: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        page_number = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        pages.append((page_number, content))
    return pages


def default_title(pages: list[tuple[str, str]], explicit_title: str | None) -> str:
    if explicit_title:
        return explicit_title
    if not pages:
        return "OCR Handout"
    first_page_content = pages[0][1].strip().splitlines()
    for line in first_page_content:
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "|", "!", "[")):
            return stripped
    return "OCR Handout"


def build_html_document(pages: list[tuple[str, str]], title: str, source_label: str) -> str:
    md = MarkdownIt("commonmark").enable("table")
    sheet_html: list[str] = []

    for index, (page_number, page_markdown) in enumerate(pages, start=1):
        page_body = md.render(page_markdown)
        title_html = f'<h1 class="doc-title">{html.escape(title)}</h1>' if index == 1 else ""
        sheet_html.append(
            "\n".join(
                [
                    '<article class="sheet">',
                    '  <header class="sheet-header">',
                    f'    <span>{html.escape(source_label)}</span>',
                    f'    <span>源页 {html.escape(page_number)}</span>',
                    "  </header>",
                    f"  {title_html}" if title_html else "",
                    f'  <section class="transcript-body">{page_body}</section>',
                    '  <footer class="sheet-footer">',
                    f'    <span>{html.escape(title)}</span>',
                    f'    <span>第 {index} 页</span>',
                    "  </footer>",
                    "</article>",
                ]
            )
        )

    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="zh-CN">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{html.escape(title)}</title>",
            "  <style>",
            KAMI_KERNEL_CSS,
            PRINT_BASE_CSS,
            "  </style>",
            MATHJAX_BOOTSTRAP,
            "</head>",
            "<body>",
            "\n".join(sheet_html),
            "</body>",
            "</html>",
            "",
        ]
    )


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
