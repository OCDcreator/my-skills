#!/usr/bin/env python3
"""Validate canonical Markdown produced from Doc2X OCR artifacts."""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path


CALLOUT_PATTERN = re.compile(r"^\s*>\s*\[![^\]]+\]")
ANALYSIS_QUOTE_PATTERN = re.compile(r"^\s*>\s*解析[:：]")
PLAIN_ANALYSIS_PATTERN = re.compile(r"^\s*解析[:：]")
CHOICE_OPTION_PATTERN = re.compile(r"^\s*(?:[-*]\s*)?[A-H][.．、]\s+")
VERTICAL_CHOICE_OPTION_PATTERN = re.compile(r"^\s*[-*]\s+[A-H][.．、]\s+")
UNCHECKED_CHUNK_PATTERN = re.compile(r"^\s*-\s*\[\s\]\s+", re.MULTILINE)
CHECKED_CHUNK_PATTERN = re.compile(r"^\s*-\s*\[[xX]\]\s+", re.MULTILINE)
GENERIC_TITLE_PATTERN = re.compile(r"^\s*#\s+Source Transcript\s*$", re.IGNORECASE)
PAGE_HEADING_PATTERN = re.compile(r"^\s*#{1,6}\s+Page\s+\d+\s*$", re.IGNORECASE)
NUMERIC_HEADING_PATTERN = re.compile(r"^\s*#{1,6}\s+\d+(?:\.\d+)*\.?\s+")
NUMERIC_OUTLINE_LINE_PATTERN = re.compile(r"^\s*\d+(?:\.\d+)+\.?\s+")
INLINE_NUMERIC_OUTLINE_PATTERN = re.compile(r"(?<!\d)\d+\.\d+(?:\.\d+)*\.\s+[\u4e00-\u9fffA-Za-z]")
PRINT_NOISE_PATTERN = re.compile(r"MST\s*高中基础知识与二级结论")
MARKDOWN_TABLE_PATTERN = re.compile(r"^\s*\|.*\|\s*$")
MARKDOWN_TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\([^)]+\)")
HTML_TABLE_PATTERN = re.compile(r"<table\b[^>]*>", re.IGNORECASE)
HTML_IMAGE_PATTERN = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
HTML_FIGURE_START_PATTERN = re.compile(r"<figure\b[^>]*>", re.IGNORECASE)
HTML_FIGURE_END_PATTERN = re.compile(r"</figure\s*>", re.IGNORECASE)
HTML_ATTRIBUTE_PATTERN = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(['\"])(.*?)\2", re.DOTALL)
HTML_CONTEXT_TAG_PATTERN = re.compile(
    r"</?(?:table|thead|tbody|tr|td|th|div|span|figure|figcaption|p|math|svg)\b",
    re.IGNORECASE,
)
HTML_BLOCK_OPEN_PATTERN = re.compile(r"<(table|thead|tbody|tr|td|th|div|span|figure|figcaption)\b(?![^>]*?/>)", re.IGNORECASE)
HTML_BLOCK_CLOSE_PATTERN = re.compile(r"</(table|thead|tbody|tr|td|th|div|span|figure|figcaption)\s*>", re.IGNORECASE)
HTML_TAG_STRIP_PATTERN = re.compile(r"<[^>]+>")
HTML_MATHML_PATTERN = re.compile(r"<math\b[\s\S]*?</math\s*>", re.IGNORECASE)
HTML_SVG_MATH_OPEN_PATTERN = re.compile(
    r"<svg\b(?=[^>]*\bclass\s*=\s*(['\"])[^'\"]*\bmath-svg\b[^'\"]*\1)[^>]*>",
    re.IGNORECASE,
)
MATHML_TABLE_PATTERN = re.compile(r"<mtable\b", re.IGNORECASE)
STRETCHY_BRACE_PATTERN = re.compile(
    r"<mo\b(?=[^>]*\bstretchy\s*=\s*(['\"])true\1)[^>]*>\s*\{",
    re.IGNORECASE,
)
MATH_CASES_PATTERN = re.compile(r"\bclass\s*=\s*(['\"])[^'\"]*\bmath-cases\b[^'\"]*\1", re.IGNORECASE)
CASE_LINES_PATTERN = re.compile(r"\bclass\s*=\s*(['\"])[^'\"]*\bcase-lines\b[^'\"]*\1", re.IGNORECASE)
HTML_ANALYSIS_BLOCK_PATTERN = re.compile(
    r"<div\b[^>]*\bclass\s*=\s*(['\"])[^'\"]*\banalysis-block\b[^'\"]*\1",
    re.IGNORECASE,
)
HTML_PARAGRAPH_PATTERN = re.compile(r"<p\b[^>]*>(.*?)</p\s*>", re.IGNORECASE | re.DOTALL)
INLINE_MATH_PATTERN = re.compile(r"(?<!\\)(?<!\$)\$([^\n$]+)\$(?!\$)")
HTML_FORMULA_HINT_PATTERN = re.compile(
    r"\\[A-Za-z]+|[_^](?=[{A-Za-z0-9\\])|[∥⊥∩⊂⊄⇒]"
)
PLAIN_FRAC_PATTERN = re.compile(r"\\frac\b")
NON_OBSIDIAN_MATH_DELIMITER_PATTERN = re.compile(r"\\[()\[\]]")
FRAGILE_KATEX_MACRO_PATTERN = re.compile(
    r"\\(?:mspace|left\.|overset\{\\large\\frown\})"
)

LONG_MARKDOWN_LINE_LIMIT = 300
LONG_MARKDOWN_CHAR_LIMIT = 10_000

# --- auto-fix patterns ---
LEADING_ORPHAN_PUNCT_PATTERN = re.compile(r"^[）)]{1,3}\s*")
LEADING_ORPHAN_PERIOD_PATTERN = re.compile(r"^[。，、]{1,2}\s*")
LEADING_ORPHAN_DOTS_PATTERN = re.compile(r"^\.{2,}\s+")
STRAY_BACKSLASH_ESCAPE_PATTERN = re.compile(r"\\([*#_[\]])")
FILLIN_BLANK_PATTERN = re.compile(r"_{2,}|-{2,}")
FRAC_PATTERN = re.compile(r"\\frac\{([^}]*)}\{([^}]*)}")
DOLLAR_SPACE_PATTERN = re.compile(r"\$ (?P<body>[^\n$]+?) \$")
PAREN_MATH_PATTERN = re.compile(r"\\\(([^)]+)\\\)")
BRACKET_MATH_PATTERN = re.compile(r"\\\[([^\]]+)\\\]")
LIST_ARTIFACT_PATTERN = re.compile(r"^(\d+)\.{2,}\s+")
LIST_ARTIFACT_PERIOD_PATTERN = re.compile(r"^(\d+)。{2,}\s*")
CIRCLED_NUM_ARTIFACT_PATTERN = re.compile(r"^([①②③④⑤⑥⑦⑧⑨⑩])\.{1,2}\s*")

# --- proofreading check patterns ---
UNCLOSED_DOLLAR_PATTERN = re.compile(r"(?<!\$)\$[^\n$]*$|(?<!\$)\${3,}|[^$]\$\$[^$]")
HEADING_LEVEL_PATTERN = re.compile(r"^(#{1,6})\s+")
CONFUSABLE_CHINESE_CHARS = {
    "己": "已/巳", "已": "己/巳", "末": "未", "未": "末",
    "千": "干", "干": "千", "人": "入", "入": "人",
    "白": "日", "日": "白", "十": "干", "土": "士",
    "午": "牛", "牛": "午",
}
CONFUSABLE_ASCII = {
    "l": "1/|", "O": "0", "0": "O/o",
    "S": "5", "5": "S/s", "B": "8", "8": "B",
}
GARBLED_LINE_PATTERN = re.compile(r"^[#\$%@!~<>]{3,}$|^[a-zA-Z0-9]{20,}$|###ERROR###")
OPTION_COUNT_PATTERN = re.compile(r"^\s*[-*]\s+([A-H])[.．、]", re.MULTILINE)
CHOICE_GRID_OPTION_PATTERN = re.compile(r"<span>\s*([A-H])[.．、]")


@dataclass(frozen=True)
class LintMessage:
    line: int
    text: str


@dataclass(frozen=True)
class QuoteBlock:
    start_line: int
    end_line: int
    kind: str
    lines: list[str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", help="Canonical markdown path to validate")
    parser.add_argument("--job-dir", help="Job directory containing source-transcript.md")
    parser.add_argument("--max-analysis-lines", type=int, default=12)
    parser.add_argument("--max-analysis-paragraphs", type=int, default=6)
    parser.add_argument("--max-analysis-line-chars", type=int, default=180)
    parser.add_argument("--fix", action="store_true", help="Auto-fix mechanical issues in the markdown file")
    parser.add_argument("--dry-run", action="store_true", help="Preview --fix changes without writing")
    parser.add_argument("--check-proofreading", action="store_true", help="Run proofreading quality checks")
    return parser


def is_quote_line(line: str) -> bool:
    return line.lstrip().startswith(">")


def strip_quote_marker(line: str) -> str:
    stripped = line.lstrip()
    if not stripped.startswith(">"):
        return stripped
    return stripped[1:].lstrip()


def html_attributes(tag: str) -> dict[str, str]:
    return {match.group(1).lower(): match.group(3) for match in HTML_ATTRIBUTE_PATTERN.finditer(tag)}


def css_declarations(style: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for part in style.split(";"):
        if ":" not in part:
            continue
        name, value = part.split(":", 1)
        declarations[name.strip().lower()] = value.strip().lower()
    return declarations


def strip_mathml(text: str) -> str:
    return HTML_MATHML_PATTERN.sub("", text)


def strip_html_tags(text: str) -> str:
    return HTML_TAG_STRIP_PATTERN.sub("", text)


def html_text_content(text: str) -> str:
    return html.unescape(strip_html_tags(strip_mathml(text)))


def html_depth_delta(text: str) -> int:
    return len(HTML_BLOCK_OPEN_PATTERN.findall(text)) - len(HTML_BLOCK_CLOSE_PATTERN.findall(text))


def collect_mathml_blocks(lines: list[str]) -> tuple[list[tuple[int, int, str]], set[int]]:
    blocks: list[tuple[int, int, str]] = []
    line_numbers: set[int] = set()
    index = 0
    while index < len(lines):
        content = strip_quote_marker(lines[index]) if is_quote_line(lines[index]) else lines[index]
        start_match = re.search(r"<math\b", content, re.IGNORECASE)
        if not start_match:
            index += 1
            continue

        start_line = index + 1
        block_lines = [content[start_match.start() :]]
        line_numbers.add(start_line)
        if re.search(r"</math\s*>", content[start_match.end() :], re.IGNORECASE):
            blocks.append((start_line, start_line, "\n".join(block_lines)))
            index += 1
            continue

        while index + 1 < len(lines):
            index += 1
            next_content = strip_quote_marker(lines[index]) if is_quote_line(lines[index]) else lines[index]
            block_lines.append(next_content)
            line_numbers.add(index + 1)
            if re.search(r"</math\s*>", next_content, re.IGNORECASE):
                break
        blocks.append((start_line, index + 1, "\n".join(block_lines)))
        index += 1
    return blocks, line_numbers


def quote_block_kind(lines: list[str]) -> str:
    for line in lines:
        content = strip_quote_marker(line).strip()
        if not content:
            continue
        if content.startswith("[!"):
            return "callout"
        if content.startswith(("解析：", "解析:")):
            return "analysis"
        return "quote"
    return "quote"


def collect_quote_blocks(lines: list[str]) -> list[QuoteBlock]:
    blocks: list[QuoteBlock] = []
    index = 0
    while index < len(lines):
        if not is_quote_line(lines[index]):
            index += 1
            continue
        start = index
        block_lines: list[str] = []
        while index < len(lines) and is_quote_line(lines[index]):
            block_lines.append(lines[index])
            index += 1
        blocks.append(
            QuoteBlock(
                start_line=start + 1,
                end_line=index,
                kind=quote_block_kind(block_lines),
                lines=block_lines,
            )
        )
    return blocks


def next_nonblank_index(lines: list[str], start_index: int) -> int | None:
    for index in range(start_index, len(lines)):
        if lines[index].strip():
            return index
    return None


def previous_nonblank_index(lines: list[str], start_index: int) -> int | None:
    for index in range(start_index, -1, -1):
        if lines[index].strip():
            return index
    return None


def is_new_quote_block_start(line: str) -> bool:
    return bool(CALLOUT_PATTERN.match(line) or ANALYSIS_QUOTE_PATTERN.match(line))


def quote_line_numbers_for_kind(blocks: list[QuoteBlock], kind: str) -> set[int]:
    line_numbers: set[int] = set()
    for block in blocks:
        if block.kind != kind:
            continue
        line_numbers.update(range(block.start_line, block.end_line + 1))
    return line_numbers


def lint_bare_blank_splits(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for index, line in enumerate(lines):
        if line.strip():
            continue
        previous_index = previous_nonblank_index(lines, index - 1)
        next_index = next_nonblank_index(lines, index + 1)
        if previous_index is None or next_index is None:
            continue
        previous_line = lines[previous_index]
        next_line = lines[next_index]
        if is_quote_line(previous_line) and is_quote_line(next_line) and not is_new_quote_block_start(next_line):
            messages.append(
                LintMessage(
                    index + 1,
                    "bare blank line splits a blockquote or callout; use a quoted blank line written as `>`",
                )
            )
    return messages


def lint_analysis(
    lines: list[str],
    blocks: list[QuoteBlock],
    max_lines: int,
    max_paragraphs: int,
    max_line_chars: int,
) -> list[LintMessage]:
    messages: list[LintMessage] = []

    for index, line in enumerate(lines, start=1):
        if PLAIN_ANALYSIS_PATTERN.match(line):
            messages.append(LintMessage(index, "question analysis must use an HTML analysis-block"))
            continue
        if is_quote_line(line) and strip_quote_marker(line).strip().startswith(("解析：", "解析:")):
            messages.append(LintMessage(index, "question analysis must use an HTML analysis-block, not a Markdown blockquote"))

    for block in blocks:
        if block.kind != "analysis":
            continue
        messages.append(LintMessage(block.start_line, "question analysis must use an HTML analysis-block, not a Markdown blockquote"))

    messages.extend(lint_html_analysis_blocks(lines, max_lines, max_paragraphs, max_line_chars))
    return messages


def lint_html_analysis_blocks(
    lines: list[str],
    max_lines: int,
    max_paragraphs: int,
    max_line_chars: int,
) -> list[LintMessage]:
    messages: list[LintMessage] = []
    index = 0
    while index < len(lines):
        content = strip_quote_marker(lines[index]) if is_quote_line(lines[index]) else lines[index]
        if not HTML_ANALYSIS_BLOCK_PATTERN.search(content):
            index += 1
            continue

        start_line = index + 1
        start_tag_match = re.search(r"<div\b[^>]*>", content, re.IGNORECASE)
        if start_tag_match:
            attrs = html_attributes(start_tag_match.group(0))
            style = css_declarations(attrs.get("style", ""))
            if not any(name == "border" or name.startswith("border-") for name in style):
                messages.append(LintMessage(start_line, "analysis block must include a visible border style"))
        block_lines = [content]
        depth = html_depth_delta(content)
        while depth > 0 and index + 1 < len(lines):
            index += 1
            next_content = strip_quote_marker(lines[index]) if is_quote_line(lines[index]) else lines[index]
            block_lines.append(next_content)
            depth += html_depth_delta(next_content)

        block_text = "\n".join(block_lines)
        paragraphs = [
            html_text_content(match.group(1)).strip()
            for match in HTML_PARAGRAPH_PATTERN.finditer(block_text)
        ]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]
        if len(paragraphs) > max_lines:
            messages.append(
                LintMessage(
                    start_line,
                    f"analysis block is too scattered; keep analysis compact (paragraphs={len(paragraphs)})",
                )
            )
        for offset, paragraph in enumerate(paragraphs):
            if len(paragraph) > max_line_chars:
                messages.append(
                    LintMessage(
                        start_line + offset,
                        f"analysis paragraph is too dense; split it into compact paragraphs (chars={len(paragraph)})",
                    )
                )
        index += 1
    return messages


def lint_choice_options(lines: list[str], blocks: list[QuoteBlock]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    callout_line_numbers = quote_line_numbers_for_kind(blocks, "callout")
    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        if not CHOICE_OPTION_PATTERN.match(content):
            continue
        if index not in callout_line_numbers:
            messages.append(LintMessage(index, "choice option must stay inside a question callout"))
        elif VERTICAL_CHOICE_OPTION_PATTERN.match(content):
            messages.append(LintMessage(index, "choice options must use a horizontal HTML choice grid"))
    return messages


def lint_headings_and_print_noise(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for index, line in enumerate(lines, start=1):
        if index == 1 and GENERIC_TITLE_PATTERN.match(line):
            messages.append(LintMessage(index, "top title must describe the document"))
        if PAGE_HEADING_PATTERN.match(line):
            messages.append(LintMessage(index, "page markers must not be visible headings"))
        if NUMERIC_HEADING_PATTERN.match(line):
            messages.append(LintMessage(index, "dotted numeric heading labels are not allowed"))
        if PRINT_NOISE_PATTERN.search(line):
            messages.append(LintMessage(index, "print header/footer noise must be removed"))
    return messages


def lint_numeric_outline_labels(lines: list[str], blocks: list[QuoteBlock]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    callout_line_numbers = quote_line_numbers_for_kind(blocks, "callout")
    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line).strip() if is_quote_line(line) else line.strip()
        if not content:
            continue
        if index in callout_line_numbers:
            continue
        if content.startswith("#"):
            continue
        if NUMERIC_OUTLINE_LINE_PATTERN.match(content) or INLINE_NUMERIC_OUTLINE_PATTERN.search(content):
            messages.append(LintMessage(index, "numeric outline labels are not allowed"))
    return messages


def lint_tables(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for index, line in enumerate(lines, start=1):
        if MARKDOWN_TABLE_SEPARATOR_PATTERN.match(line) or MARKDOWN_TABLE_PATTERN.match(line):
            messages.append(LintMessage(index, "Markdown tables are not allowed; use centered HTML tables"))

        for match in HTML_TABLE_PATTERN.finditer(line):
            attrs = html_attributes(match.group(0))
            style = css_declarations(attrs.get("style", ""))
            text_align = style.get("text-align", "")
            vertical_align = style.get("vertical-align", "")
            if "center" not in text_align or "middle" not in vertical_align:
                messages.append(
                    LintMessage(
                        index,
                        "HTML tables must declare centered horizontal and vertical alignment",
                    )
                )
    return messages


def lint_images(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        if MARKDOWN_IMAGE_PATTERN.search(content):
            messages.append(LintMessage(index, "Markdown image syntax is not allowed; use styled HTML figures"))

        for match in HTML_IMAGE_PATTERN.finditer(content):
            attrs = html_attributes(match.group(0))
            style = css_declarations(attrs.get("style", ""))
            has_size = "max-width" in style or "width" in style
            height_auto = style.get("height") == "auto"
            margin_centered = "auto" in style.get("margin", "") or (
                style.get("margin-left") == "auto" and style.get("margin-right") == "auto"
            )
            block_centered = style.get("display") == "block" and margin_centered
            if not has_size or not height_auto or not block_centered:
                messages.append(
                    LintMessage(
                        index,
                        "HTML images must include sizing and centering styles",
                    )
                )
    return messages


def lint_multi_image_figures(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    index = 0
    while index < len(lines):
        line = strip_quote_marker(lines[index]) if is_quote_line(lines[index]) else lines[index]
        start_match = HTML_FIGURE_START_PATTERN.search(line)
        if not start_match:
            index += 1
            continue

        start_line = index + 1
        same_line_end = HTML_FIGURE_END_PATTERN.search(line, start_match.end())
        if same_line_end:
            figure_text = line[start_match.start() : same_line_end.end()]
        else:
            figure_lines = [line[start_match.start() :]]
            while index + 1 < len(lines):
                if HTML_FIGURE_END_PATTERN.search(figure_lines[-1]):
                    break
                index += 1
                next_line = strip_quote_marker(lines[index]) if is_quote_line(lines[index]) else lines[index]
                figure_lines.append(next_line)
                if HTML_FIGURE_END_PATTERN.search(next_line):
                    break
            figure_text = "\n".join(figure_lines)

        image_count = len(HTML_IMAGE_PATTERN.findall(figure_text))
        start_style = css_declarations(html_attributes(start_match.group(0)).get("style", ""))
        if image_count > 1 and start_style.get("display") != "flex":
            messages.append(LintMessage(start_line, "multi-image figures must use horizontal flex layout"))
        index += 1
    return messages


def lint_formulas(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for index, line in enumerate(lines, start=1):
        line_without_mathml = strip_mathml(line)
        if PLAIN_FRAC_PATTERN.search(line_without_mathml):
            messages.append(LintMessage(index, "plain \\frac is not allowed; use \\dfrac or nested \\tfrac"))
        if NON_OBSIDIAN_MATH_DELIMITER_PATTERN.search(line_without_mathml):
            messages.append(LintMessage(index, "use Obsidian math delimiters `$...$` and `$$...$$`, not `\\(...\\)` or `\\[...\\]`"))
        if FRAGILE_KATEX_MACRO_PATTERN.search(line_without_mathml):
            messages.append(LintMessage(index, "fragile or unsupported KaTeX macro; use a simpler Obsidian-compatible expression"))
    return messages


def lint_inline_math_spacing(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for index, line in enumerate(lines, start=1):
        line_without_mathml = strip_mathml(line)
        for match in INLINE_MATH_PATTERN.finditer(line_without_mathml):
            content = match.group(1)
            if content != content.strip():
                messages.append(LintMessage(index, "inline math must not have boundary spaces; use `$x$`, not `$ x $`"))
                break
    return messages


def lint_html_math(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    mathml_blocks, mathml_line_numbers = collect_mathml_blocks(lines)
    for start_line, _end_line, block_text in mathml_blocks:
        if MATHML_TABLE_PATTERN.search(block_text) and not STRETCHY_BRACE_PATTERN.search(block_text):
            messages.append(
                LintMessage(
                    start_line,
                    "HTML MathML condition groups must use an explicit stretchy left brace",
                )
            )

    html_depth = 0
    math_cases_depth = 0
    math_cases_start_line = 0
    math_cases_has_vertical_lines = False
    for index, raw_line in enumerate(lines, start=1):
        content = strip_quote_marker(raw_line) if is_quote_line(raw_line) else raw_line
        is_html_context = html_depth > 0 or bool(HTML_CONTEXT_TAG_PATTERN.search(content))
        line_without_mathml = strip_mathml(content)

        for svg_match in HTML_SVG_MATH_OPEN_PATTERN.finditer(content):
            attrs = html_attributes(svg_match.group(0))
            if attrs.get("role") != "img" or not attrs.get("aria-label", "").strip():
                messages.append(
                    LintMessage(
                        index,
                        'inline SVG math must include role="img" and a non-empty aria-label',
                    )
                )

        if MATH_CASES_PATTERN.search(content):
            math_cases_depth = max(1, html_depth_delta(content))
            math_cases_start_line = index
            math_cases_has_vertical_lines = False
        elif math_cases_depth > 0:
            math_cases_depth += html_depth_delta(content)

        if math_cases_depth > 0 and CASE_LINES_PATTERN.search(content):
            style = css_declarations(html_attributes(re.search(r"<[^>]+>", content).group(0)).get("style", "")) if re.search(r"<[^>]+>", content) else {}
            if style.get("flex-direction") == "column":
                math_cases_has_vertical_lines = True

        if is_html_context:
            if "$" in line_without_mathml:
                messages.append(LintMessage(index, "HTML content must use MathML or inline SVG for formulas, not `$...$` or `$$...$$`"))
            if NON_OBSIDIAN_MATH_DELIMITER_PATTERN.search(line_without_mathml):
                messages.append(LintMessage(index, "HTML content must use MathML or inline SVG for formulas, not `\\(...\\)` or `\\[...\\]`"))
            visible_text = html_text_content(content)
            if index not in mathml_line_numbers and HTML_FORMULA_HINT_PATTERN.search(visible_text):
                messages.append(LintMessage(index, "HTML formula content must be rendered as MathML or inline SVG"))

        if math_cases_depth == 0 and math_cases_start_line:
            if not math_cases_has_vertical_lines:
                messages.append(
                    LintMessage(
                        math_cases_start_line,
                        "math-cases must include case-lines with `flex-direction:column` so cases render as multiple rows",
                    )
                )
            math_cases_start_line = 0

        html_depth = max(0, html_depth + html_depth_delta(content))
    return messages


def auto_fix_markdown(markdown_text: str) -> tuple[str, list[str]]:
    """Apply mechanical fixes and return (fixed_text, changes_made)."""
    changes: list[str] = []
    lines = markdown_text.splitlines()
    fixed_lines: list[str] = []

    for index, line in enumerate(lines, start=1):
        original = line
        content = strip_quote_marker(line) if is_quote_line(line) else line
        is_quote = is_quote_line(line)
        quote_prefix = line[: len(line) - len(line.lstrip())] if is_quote and line.lstrip().startswith(">") else ""
        body = content

        # Rule: leading orphan punctuation
        if not content.startswith("#") and not content.startswith("```"):
            body = LEADING_ORPHAN_PUNCT_PATTERN.sub("", body)
            body = LEADING_ORPHAN_PERIOD_PATTERN.sub("", body)
            body = LEADING_ORPHAN_DOTS_PATTERN.sub("", body)

        # Rule: list artifacts
        body = LIST_ARTIFACT_PERIOD_PATTERN.sub(r"\1. ", body)
        body = LIST_ARTIFACT_PATTERN.sub(r"\1. ", body)
        body = CIRCLED_NUM_ARTIFACT_PATTERN.sub(r"\1 ", body)

        # Rule: remove numeric outline prefixes from bold text (e.g., **1. 平移变换** → **平移变换**)
        # But preserve question subparts like (1), (2) inside callouts
        NUMERIC_OUTLINE_BOLD_PATTERN = re.compile(r"\*\*\d+\.\s+(.*?)\*\*")
        new_body = NUMERIC_OUTLINE_BOLD_PATTERN.sub(r"**\1**", body)
        if new_body != body:
            body = new_body
            changes.append(f"line {index}: removed numeric outline prefix from bold text")

        # Rule: stray backslash escapes (not inside code blocks)
        if "`" not in content and "```" not in content:
            body = STRAY_BACKSLASH_ESCAPE_PATTERN.sub(r"\1", body)

        # Rule: fill-in blank normalization
        body = FILLIN_BLANK_PATTERN.sub("__________", body)

        # Rule: print noise removal
        if PRINT_NOISE_PATTERN.search(body) and len(body.strip()) < 30:
            body = ""
            changes.append(f"line {index}: removed print noise line")

        # Rule: orphan page number line
        stripped = body.strip()
        if stripped.isdigit() and 1 <= len(stripped) <= 4 and not content.startswith("#"):
            body = ""
            changes.append(f"line {index}: removed orphan page number line")

        # Rule: inline math spacing
        body = DOLLAR_SPACE_PATTERN.sub(r"$\g<body>$", body)

        # Rule: math delimiter normalization
        body = PAREN_MATH_PATTERN.sub(r"$\1$", body)
        body = BRACKET_MATH_PATTERN.sub(r"$$\1$$", body)

        # Rule: fraction standardization - \frac{simple}{simple} → \dfrac
        def replace_frac(match: re.Match[str]) -> str:
            num = match.group(1).strip()
            den = match.group(2).strip()
            if any(op in num or op in den for op in ["\\", "^", "_", "{"]) or len(num) > 30 or len(den) > 30:
                return f"\\tfrac{{{num}}}{{{den}}}"
            return f"\\dfrac{{{num}}}{{{den}}}"

        new_body = FRAC_PATTERN.sub(replace_frac, body)
        if new_body != body:
            body = new_body
            changes.append(f"line {index}: standardized fractions")

        # Reconstruct line
        if is_quote and body:
            body_prefix = strip_quote_marker(line).rstrip()
            indent = line[: len(line) - len(line.lstrip())]
            if indent and not body.strip().startswith(">"):
                body = indent + body
            fixed_lines.append(body)
        elif is_quote and not body.strip():
            fixed_lines.append(">")
        elif not body.strip() and original.strip():
            fixed_lines.append(body)
        else:
            fixed_lines.append(body)

    # Rule: bare blank lines inside blockquotes → add >
    result = fix_bare_blank_splits(fixed_lines, changes)

    return "\n".join(result), changes


def fix_bare_blank_splits(lines: list[str], changes: list[str]) -> list[str]:
    result = list(lines)
    quote_blocks = collect_quote_blocks(result)
    for block in quote_blocks:
        for line_idx in range(block.start_line - 1, block.end_line):
            if not result[line_idx].strip():
                result[line_idx] = ">"
                changes.append(f"line {line_idx + 1}: fixed bare blank line in blockquote -> added `>` prefix")
    return result


def lint_proofreading(markdown_text: str) -> list[LintMessage]:
    """Check for quality issues: unclosed formulas, heading jumps, suspicious chars."""
    messages: list[LintMessage] = []
    lines = markdown_text.splitlines()

    # Check unclosed math delimiters
    dollar_count = 0
    in_display = False
    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        line_without_mathml = strip_mathml(content)
        singles = line_without_mathml.count("$") - line_without_mathml.count("$$")
        if singles % 2 != 0:
            messages.append(LintMessage(index, "possible unclosed inline math `$` delimiter"))

    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        if content.count("$$") % 2 != 0:
            messages.append(LintMessage(index, "possible unclosed display math `$$` delimiter"))

    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        if "$$$" in content:
            messages.append(LintMessage(index, "malformed math delimiter `$$$`"))

    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        if "$" in content and "```" not in content.lower():
            # Skip lines containing LaTeX array constructs — these have legitimate brace imbalances
            # e.g., \left\{ \begin{array}{l} ... \end{array} \right.
            if r"\begin{array}" in content or r"\left\{" in content or r"\right." in content:
                continue
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces and "```" not in content.lower():
            messages.append(LintMessage(index, f"unbalanced braces: {{{open_braces}}} vs {{{close_braces}}}"))

    # Check heading level jumps
    heading_levels: list[tuple[int, int]] = []
    for index, line in enumerate(lines, start=1):
        match = HEADING_LEVEL_PATTERN.match(line)
        if match:
            heading_levels.append((index, len(match.group(1))))

    for i in range(1, len(heading_levels)):
        prev_idx, prev_level = heading_levels[i - 1]
        curr_idx, curr_level = heading_levels[i]
        if curr_level > prev_level + 1:
            messages.append(LintMessage(curr_idx, f"heading jump: ### → {'#' * curr_level} (skipped a level)"))

    # Check for garbled lines
    for index, line in enumerate(lines, start=1):
        if GARBLED_LINE_PATTERN.match(line.strip()):
            messages.append(LintMessage(index, "line looks garbled or corrupted"))

    # Check for confusable Chinese characters (flag as suspicious)
    # But skip lines that contain LaTeX formulas — the backslash+brace patterns
    # like \left\{ are often falsely flagged as containing "已"
    for index, line in enumerate(lines, start=1):
        if line.strip().startswith("```"):
            continue
        # Remove LaTeX math regions before checking confusable chars
        line_without_latex = re.sub(r"\\[A-Za-z]+\{[^}]*\}", "", line)
        line_without_latex = re.sub(r"\$[^\n$]+\$", "", line_without_latex)
        for char, alternates in CONFUSABLE_CHINESE_CHARS.items():
            if char in line_without_latex:
                messages.append(LintMessage(index, f"suspicious character [{char}] near [{alternates}] — verify against page image"))
                break

    # Check option completeness in choice grids
    choice_contexts: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        options_found = CHOICE_GRID_OPTION_PATTERN.findall(content)
        if options_found:
            choice_contexts.append((index, content))

        markdown_options = OPTION_COUNT_PATTERN.findall(content)
        if markdown_options:
            choice_contexts.append((index, content))

    for ctx_index, ctx_content in choice_contexts:
        options_found = CHOICE_GRID_OPTION_PATTERN.findall(ctx_content) or OPTION_COUNT_PATTERN.findall(ctx_content)
        if options_found and len(options_found) < 4:
            messages.append(LintMessage(ctx_index, f"choice options may be incomplete: found {len(options_found)} options, expected 4"))

    # Check TO VERIFY count
    to_verify_count = markdown_text.count("[TO VERIFY:")
    if to_verify_count > 0:
        messages.append(LintMessage(0, f"{to_verify_count} [TO VERIFY: ...] markers found — review needed"))

    # Check for empty image references
    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line
        if re.search(r'!\[[^\]]*\]\(\s*\)', content):
            messages.append(LintMessage(index, "empty image reference — missing file path"))
        if re.search(r'<img\b[^>]*src\s*=\s*["\']\s*["\']', content, re.IGNORECASE):
            messages.append(LintMessage(index, "HTML image with empty src attribute"))

    return messages

def lint_markdown(
    markdown_text: str,
    max_analysis_lines: int,
    max_analysis_paragraphs: int,
    max_analysis_line_chars: int,
) -> list[LintMessage]:
    lines = markdown_text.splitlines()
    blocks = collect_quote_blocks(lines)
    messages: list[LintMessage] = []
    messages.extend(lint_headings_and_print_noise(lines))
    messages.extend(lint_tables(lines))
    messages.extend(lint_images(lines))
    messages.extend(lint_multi_image_figures(lines))
    messages.extend(lint_formulas(lines))
    messages.extend(lint_inline_math_spacing(lines))
    messages.extend(lint_html_math(lines))
    messages.extend(lint_numeric_outline_labels(lines, blocks))
    messages.extend(lint_bare_blank_splits(lines))
    messages.extend(
        lint_analysis(
            lines,
            blocks,
            max_analysis_lines,
            max_analysis_paragraphs,
            max_line_chars=max_analysis_line_chars,
        )
    )
    messages.extend(lint_choice_options(lines, blocks))
    return sorted(messages, key=lambda message: message.line)


def read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_markdown_path(job_dir: Path | None, explicit_md: str | None) -> Path:
    if explicit_md:
        return Path(explicit_md).expanduser().resolve()
    if job_dir is None:
        raise SystemExit("Provide --md or --job-dir.")
    return (job_dir / "source-transcript.md").resolve()


def doc2x_markdown_is_long(job_dir: Path) -> bool:
    candidates = [
        job_dir / "doc2x" / "export" / "export.md",
        job_dir / "doc2x" / "page-transcript.raw.md",
        job_dir / "source-transcript.md",
    ]
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if len(text) >= LONG_MARKDOWN_CHAR_LIMIT or len(text.splitlines()) >= LONG_MARKDOWN_LINE_LIMIT:
            return True
    return False


def lint_plan_file(plan_path: Path, require_plan: bool) -> list[LintMessage]:
    if not plan_path.exists():
        if not require_plan:
            return []
        return [LintMessage(0, "long Doc2X markdown requires markdown-rewrite-plan.md")]

    plan_text = plan_path.read_text(encoding="utf-8")
    if UNCHECKED_CHUNK_PATTERN.search(plan_text):
        return [LintMessage(0, "markdown-rewrite-plan.md has unfinished chunks")]
    if len(CHECKED_CHUNK_PATTERN.findall(plan_text)) < 2:
        return [LintMessage(0, "markdown-rewrite-plan.md must list at least two completed chunks")]
    return []


def lint_rewrite_plan(job_dir: Path | None, md_path: Path) -> list[LintMessage]:
    if job_dir is not None:
        return lint_plan_file(
            job_dir / "markdown-rewrite-plan.md",
            require_plan=doc2x_markdown_is_long(job_dir),
        )

    sibling_plan = md_path.parent / "markdown-rewrite-plan.md"
    return lint_plan_file(sibling_plan, require_plan=False)


def update_job_status(job_dir: Path | None, status: str) -> None:
    if job_dir is None:
        return
    job_path = job_dir / "job.json"
    if not job_path.exists():
        return
    payload = read_json(job_path)
    payload["canonical_markdown_lint_status"] = status
    write_json(job_path, payload)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_dir = Path(args.job_dir).expanduser().resolve() if args.job_dir else None
    md_path = resolve_markdown_path(job_dir, args.md)
    if not md_path.exists():
        raise SystemExit(f"Markdown not found: {md_path}")

    markdown_text = md_path.read_text(encoding="utf-8")

    # --fix mode: auto-correct mechanical issues
    if args.fix:
        fixed_text, changes = auto_fix_markdown(markdown_text)
        result_text = fixed_text
        if args.dry_run:
            print(f"DRY RUN: would auto-fix {len(changes)} issue(s) in {md_path}")
            for change in changes:
                print(f"  - {change}")
            return 0
        md_path.write_text(result_text, encoding="utf-8")
        print(f"OK: auto-fixed {len(changes)} issue(s) in {md_path}")
        for change in changes:
            print(f"  - {change}")
        markdown_text = result_text

    # --check-proofreading: quality checks
    if args.check_proofreading:
        proof_messages = lint_proofreading(markdown_text)
        if proof_messages:
            update_job_status(job_dir, "proofreading_failed")
            for message in sorted(proof_messages, key=lambda item: item.line):
                prefix = f"line {message.line}: " if message.line else ""
                print(f"PROOFREAD FAIL: {prefix}{message.text}")
            return 1
        update_job_status(job_dir, "proofreading_passed")
        print(f"OK: proofreading passed for {md_path}")
        return 0

    # Default: full lint
    messages = lint_markdown(
        markdown_text,
        max_analysis_lines=args.max_analysis_lines,
        max_analysis_paragraphs=args.max_analysis_paragraphs,
        max_analysis_line_chars=args.max_analysis_line_chars,
    )
    messages.extend(lint_rewrite_plan(job_dir, md_path))

    if messages:
        update_job_status(job_dir, "failed")
        for message in sorted(messages, key=lambda item: item.line):
            prefix = f"line {message.line}: " if message.line else ""
            print(f"FAIL: {prefix}{message.text}")
        return 1

    update_job_status(job_dir, "passed")
    print(f"OK: canonical markdown passed for {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
