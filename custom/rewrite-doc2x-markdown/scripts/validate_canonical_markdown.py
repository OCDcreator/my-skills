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
MARKDOWN_IMAGE_PATH_PATTERN = re.compile(r"!\[[^\]]*]\(([^)]+)\)")
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
DISPLAY_MATH_PATTERN = re.compile(r"(?<!\$)\$\$(.+?)\$\$(?!\$)", re.DOTALL)
CALLOUT_TYPE_PATTERN = re.compile(r"^\s*>\s*\[!([^\]]+)\]", re.IGNORECASE)
QA_ANALYSIS_LINE_PATTERN = re.compile(r"\*\*(?:解析|解答|解|证明|分析)\*\*")
QA_SUBPART_PATTERN = re.compile(r"^\s*[(（]\s*(?:\d+|[IVXivx]+)\s*[)）]")
BARE_QUESTION_START_PATTERN = re.compile(
    r"^\s*(?:【\s*)?(?:例题|练习)(?:\s*[0-9一二三四五六七八九十百零]+)?(?:\s*[】)])?(?:\s+\S|[（(])"
)
# A plain-Markdown analysis opener: a line that starts (after optional `>` or
# list marker) with **解析**/**解**/**证明**/**解答**/**分析**. Used by the
# Step 2.7 paragraph-length lint to find where a Markdown analysis section
# begins. (Distinct from QA_ANALYSIS_LINE_PATTERN, which matches the marker
# anywhere on a line.)
MARKDOWN_ANALYSIS_OPENER_PATTERN = re.compile(
    r"^\s*(?:>\s*)?(?:[-*]\s+)?\*\*(?:解析|解答|解|证明|分析)\*\*\s*[:：]?\s*$"
)

# --- question-callout title-line lint (Step 2.7 structural evidence) ---
# Matches the example/exercise label at the START of a question callout's
# title line (after the `[!question]` marker is stripped). The label is the
# only part that is universal across all math PDFs: 例题N / 例N / 练习N (Arabic
# or Chinese numerals). We anchor on the label — NOT on the source format —
# because source labels vary wildly (round/angle brackets, 【】, year digits,
# exam names like 新课标/全国卷, or no source at all).
QUESTION_LABEL_PREFIX_PATTERN = re.compile(
    r"^\s*(?:例题|例|练习)\s*[0-9一二三四五六七八九十百零]+\s*"
)
# A loose source suffix that may follow the label: matched repeatedly so the
# many legal source shapes all collapse to nothing. Brackets (round/angle/【】
# Chinese) are matched as whole units so their INNER punctuation cannot be
# mistaken for stem text; year digits and exam/region tokens are also eaten.
QUESTION_SOURCE_SUFFIX_PATTERN = re.compile(
    r"(?:"
    r"\([^()]*\)"            # (...)
    r"|（[^（）]*）"         # （...）
    r"|【[^【】]*】"         # 【...】
    r"|\[[^\[\]]*\]"        # [...]
    r"|<[^<>]*>"            # <...>
    r"|・"                  # 中点（2017・新课标 的分隔符）
    r"|、"
    r"|\d{4}"               # 年份
    r"|新课标|全国|课标|卷[ⅠIIII1-3IVX]{1,4}|文科|理科|年|届|省|市"
    r"|Ⅰ|Ⅱ|III|[I]+"
    r")"
)
# Stem-start signal words: when the prose remaining after stripping the label
# and source suffix BEGINS with one of these, the title line has glued the
# stem body to the label — report it. (Chinese math stems overwhelmingly start
# with one of these.) Kept internal to the validator; the rewrite guide states
# the rule in prose so subagents rely on semantic understanding, not a list.
QUESTION_STEM_START_PATTERN = re.compile(
    r"^(?:已知|设|若|求|求证|如图|记|函数|曲线|椭圆|抛物线|双曲线|三角形|"
    r"数列|集合|在|某|把|从|过|给定|定义|点|线|面|圆|向量|矩阵|不等式|"
    r"方程|命题|对于|对任|存在|当|设函数|设数列|已知函数|已知数列|已知集合)"
)


@dataclass(frozen=True)
class LintMessage:
    line: int
    text: str
    # "error" (default) raises the exit code to 1; "hint" is printed as NOTE:
    # without failing the run. Evolved 2026-07-02 to support the medium band of
    # lint_long_inline_formula (judge-in-context, no hard FAIL).
    severity: str = "error"


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
    parser.add_argument(
        "--only",
        help=(
            "Comma-separated lint function names to run (e.g. 'lint_fraction_nesting,lint_tables'). "
            "When set, only those lints execute; everything else is skipped. "
            "Used by the refinement-agent-chain self-check so each role sees only its own lints. "
            "Unknown names are reported and abort the run."
        ),
    )
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


def strip_math_for_count(text: str) -> str:
    """Remove math spans from text so paragraph-length checks count prose,
    not LaTeX. Strips `$$...$$` (DOTALL) first, then `$...$` inline, then
    `\\(...\\)` / `\\[...\\]` non-Obsidian delimiters. This prevents the
    "long formula, short prose" false positive — a 200-char LaTeX display
    formula that renders as half a line must not inflate the prose count.

    Note: per the skill's Hard Contract, `\\(...\\)`/`\\[...\\]` should not
    appear in canonical output, but stripping them here is harmless defense.
    """
    without_display = DISPLAY_MATH_PATTERN.sub("", text)
    without_inline = INLINE_MATH_PATTERN.sub("", without_display)
    without_paren = PAREN_MATH_PATTERN.sub("", without_inline)
    without_bracket = BRACKET_MATH_PATTERN.sub("", without_paren)
    return without_bracket


def lint_markdown_analysis_paragraphs(
    lines: list[str],
    max_chars: int = 300,
) -> list[LintMessage]:
    """Enforce the Step 2.5 / Step 2.7 rule that no Markdown analysis
    paragraph exceeds `max_chars` of PROSE (math content excluded).

    Why this lint exists: the existing `lint_html_analysis_blocks` only
    checks paragraphs inside `<div class="analysis-block">` HTML blocks.
    But the canonical rules mandate PLAIN Markdown (`**解析**` + `$...$`)
    for formula-heavy analysis — so most math-doc analysis is never checked.
    This lint closes that gap. It is the structural signal that Step 2.7
    (question-block rewrite against the raw transcript) actually ran: a
    skipped Step 2.7 leaves OCR's one-giant-paragraph dumps intact, which
    this lint catches.

    Algorithm:
      1. Find each `**解析**`/`**解**`/`**证明**`/`**解答**`/`**分析**` opener
         (a line whose stripped form IS just the bold marker, optionally
         followed by a colon).
      2. Scan the whole analysis region (until a heading, another opener,
         a callout, or an 例题/练习 label) and split it into paragraphs on
         blank lines. A line entirely of math is exempt (does not count,
         does not split).
      3. For each paragraph, count prose chars (math stripped). If >
         `max_chars`, report the paragraph's first line.
    """
    messages: list[LintMessage] = []
    index = 0
    total = len(lines)
    while index < total:
        if not MARKDOWN_ANALYSIS_OPENER_PATTERN.match(lines[index]):
            index += 1
            continue
        # Scan the whole analysis region under this opener.
        para_start: int | None = None
        para_lines: list[str] = []
        scan = index + 1
        in_display_math = False
        html_depth = 0

        def flush_paragraph(start: int | None, collected: list[str]) -> None:
            if start is None or not collected:
                return
            prose = "".join(collected)
            prose_len = len(re.sub(r"\s+", "", prose))
            if prose_len > max_chars:
                messages.append(
                    LintMessage(
                        start,
                        f"analysis paragraph too long after Step 2.7 rewrite; "
                        f"split into logical paragraphs (prose chars={prose_len}, "
                        f"math excluded, limit={max_chars})",
                    )
                )

        while scan < total:
            raw = lines[scan]
            content = strip_quote_marker(raw) if is_quote_line(raw) else raw
            stripped = content.strip()
            delta = html_depth_delta(content)
            if html_depth > 0 or delta > 0:
                flush_paragraph(para_start, para_lines)
                para_start = None
                para_lines = []
                html_depth += delta
                if html_depth < 0:
                    html_depth = 0
                scan += 1
                continue
            if stripped.startswith("$$"):
                flush_paragraph(para_start, para_lines)
                para_start = None
                para_lines = []
                if not (stripped.endswith("$$") and len(stripped) > 4):
                    in_display_math = not in_display_math
                scan += 1
                continue
            if in_display_math:
                scan += 1
                continue
            # Hard exits from the analysis region entirely.
            if HEADING_LEVEL_PATTERN.match(stripped):
                break
            if MARKDOWN_ANALYSIS_OPENER_PATTERN.match(raw):
                break
            if CALLOUT_TYPE_PATTERN.match(raw):
                break
            if stripped.startswith(("例题", "练习")):
                break
            # Blank line: end the current paragraph, but KEEP scanning the
            # region — the same analysis may contain several paragraphs.
            if not stripped:
                flush_paragraph(para_start, para_lines)
                para_start = None
                para_lines = []
                scan += 1
                continue
            # Pure display-math line: exempt, skip without splitting.
            prose_here = strip_math_for_count(stripped).strip()
            if not prose_here:
                scan += 1
                continue
            if para_start is None:
                para_start = scan + 1
                para_lines = [stripped]
            else:
                para_lines.append(stripped)
            scan += 1
        # Flush the last paragraph if the region ended without a trailing blank.
        flush_paragraph(para_start, para_lines)
        index = scan if scan > index else index + 1
    return messages


def lint_paragraph_separator(lines: list[str]) -> list[LintMessage]:
    """Flag two PROSE lines joined by a single `\\n` anywhere in the document.

    Obsidian/Typora/CommonMark treat a single line break as a SOFT break and
    merge the next line into the SAME paragraph; only a blank line ends a
    paragraph. This is the whole-document hard-enforcer for the skill rule
    "separate paragraphs with a blank line, never a single `\\n`" — added
    2026-07-01 (rework: user reported the "换行让人头疼，一个换行混在一段里"
    failure where Obsidian merged single-`\\n`-joined lines into one paragraph).

    Scope: ALL prose — body narrative, callout (`> `) prose, AND analysis
    paragraphs (`**解析**`/`**解**`/...). Inside a callout the required
    paragraph separator is a blank `>` line (`>\\n> prose`), not a bare `>`.

    False-positive guards (these intentionally use single `\\n` between
    consecutive lines and are EXEMPT — never flagged):
      - YAML frontmatter (between the first two `---` fences)
      - fenced / indented code blocks
      - HTML blocks (anywhere html_depth_delta keeps depth > 0): <table>,
        <div>, <span>, <figure>, <math>, etc.
      - Markdown pipe-table rows (lines starting with `|`)
      - display-math blocks (`$$...$$`) and math-only lines
      - list items (`-`, `*`, `+`, `1.`)
      - heading lines (`#`)
    """
    messages: list[LintMessage] = []
    in_frontmatter = False
    fence: str | None = None  # current code-fence delimiter char run or None
    html_depth = 0
    in_display_math = False
    # Track the last prose line number (1-based) per channel. A naked blank line
    # resets the body channel; a blank `>` line resets the callout channel.
    prev_body_prose: int | None = None
    prev_callout_prose: int | None = None
    list_item_re = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
    pipe_table_re = re.compile(r"^\s*\|")
    display_math_re = re.compile(r"^\$\$")
    html_inline_re = re.compile(r"^\s*<")
    fence_open_re = re.compile(r"^(\s*)(`{3,}|~{3,})")
    for index, raw in enumerate(lines):
        line_no = index + 1
        stripped_raw = raw.strip()
        # --- YAML frontmatter (only at the very top of the file) ---
        if index == 0 and stripped_raw == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped_raw == "---":
                in_frontmatter = False
            continue  # everything inside frontmatter is exempt
        # --- fenced code blocks ---
        fence_match = fence_open_re.match(raw)
        if fence_match:
            delim_char = fence_match.group(2)[0]
            delim = delim_char * len(fence_match.group(2))
            if fence is None:
                fence = delim
            elif raw.lstrip().startswith(delim):
                fence = None
            prev_body_prose = None
            prev_callout_prose = None
            continue
        if fence is not None:
            continue  # inside a fenced code block
        # --- indented code block (4+ spaces, not a list item) ---
        if re.match(r"^    \S", raw) and not list_item_re.match(raw):
            prev_body_prose = None
            prev_callout_prose = None
            continue
        # --- HTML block depth tracking (quote-marker stripped first) ---
        content_for_html = strip_quote_marker(raw) if is_quote_line(raw) else raw
        delta = html_depth_delta(content_for_html)
        if html_depth > 0 or delta > 0:
            html_depth += delta
            if html_depth < 0:
                html_depth = 0
            prev_body_prose = None
            prev_callout_prose = None
            continue
        # --- display math toggle (single-line $$X$$ is self-contained) ---
        if display_math_re.match(stripped_raw):
            if stripped_raw.endswith("$$") and len(stripped_raw) > 4:
                pass  # single-line $$X$$ — self contained, no region toggle
            else:
                in_display_math = not in_display_math
            prev_body_prose = None
            prev_callout_prose = None
            continue
        if in_display_math:
            continue
        # --- headings ---
        if HEADING_LEVEL_PATTERN.match(stripped_raw):
            prev_body_prose = None
            prev_callout_prose = None
            continue
        # --- pipe-table rows ---
        if pipe_table_re.match(raw):
            prev_body_prose = None
            prev_callout_prose = None
            continue
        # --- list items ---
        if list_item_re.match(raw):
            prev_body_prose = None
            prev_callout_prose = None
            continue
        # --- naked blank line ends a body paragraph ---
        if not stripped_raw:
            prev_body_prose = None
            continue
        is_callout = is_quote_line(raw)
        if is_callout:
            # A callout TYPE opener (e.g. `> [!question] 例题1`) is a block
            # boundary, not paragraph prose — it does not start/continue a
            # prose run, and does not merge with the line that follows.
            if CALLOUT_TYPE_PATTERN.match(raw):
                prev_callout_prose = None
                continue
            callout_content = strip_quote_marker(raw)
            callout_stripped = callout_content.strip()
            # A `>` line with empty content = blank-callout-line → paragraph
            # separator INSIDE the callout; resets the callout prose run.
            if callout_stripped == "":
                prev_callout_prose = None
                continue
            # Exempt callout lines that are HTML (choice-grid, etc.), a Markdown
            # pipe-table row (`> | ... |`), or math-only.
            prose_here = strip_math_for_count(callout_stripped).strip()
            if (
                html_inline_re.match(callout_stripped)
                or pipe_table_re.match(callout_content)
                or not prose_here
            ):
                prev_callout_prose = None
                continue
            if prev_callout_prose is not None:
                messages.append(
                    LintMessage(
                        line_no,
                        "missing blank `>` line between callout paragraphs: two `>` prose "
                        "lines joined by a single `\\n` render as ONE paragraph in "
                        "Obsidian/CommonMark — separate with a blank `>` line",
                    )
                )
            prev_callout_prose = line_no
            continue
        # --- body prose line ---
        prose_here = strip_math_for_count(stripped_raw).strip()
        # HTML-inline-only or math-only body line: exempt, resets run.
        if html_inline_re.match(stripped_raw) or not prose_here:
            prev_body_prose = None
            continue
        if prev_body_prose is not None:
            messages.append(
                LintMessage(
                    line_no,
                    "missing blank line between paragraphs: two prose lines joined by a "
                    "single `\\n` render as ONE paragraph in Obsidian/Typora/CommonMark "
                    "— separate paragraphs with a blank line (`\\n\\n`)",
                )
            )
        prev_body_prose = line_no
    return messages


def lint_block_separator(lines: list[str]) -> list[LintMessage]:
    """Flag a block-level element (pipe table, HTML block such as <figure>, or
    display-math `$$`) glued directly to the preceding PROSE line by a single
    `\\n` with no blank line between them.

    Why this exists separately from `lint_paragraph_separator`: that lint only
    catches PROSE↔PROSE joins — it deliberately resets its prose-run cursor at
    every table / HTML / math line, treating "prose glued to a block" as a
    legal boundary. But Obsidian/CommonMark merge a block-opening line into the
    preceding paragraph too when only a single `\\n` separates them: a pipe
    table whose first row follows prose on the next line does NOT render as a
    table, and a `<figure>` glued to prose gets pulled into that paragraph.
    <!-- evolved 2026-07-02 — user correction: "只要换行就必须两次换行";
         the callout 题干↔表格 case in 必修二-向量万能建系法 was the trigger,
         but the rule is universal, not callout-specific. -->

    Only PROSE → block-opener joins are flagged. A block-opener preceded by a
    heading, list item, another block, a blank line, or start-of-file is NOT
    flagged (those are legitimate block boundaries that already terminate the
    previous element). This mirrors lint_paragraph_separator's prose model.
    """
    messages: list[LintMessage] = []
    in_frontmatter = False
    fence: str | None = None
    html_depth = 0
    list_item_re = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
    pipe_table_re = re.compile(r"^\s*\|")
    fence_open_re = re.compile(r"^(\s*)(`{3,}|~{3,})")
    html_block_open_re = re.compile(r"^\s*<(?:figure|table|div|span|math)\b", re.I)
    # Was the immediately-preceding line a PROSE line in this channel? Only a
    # prose predecessor makes a glued block-opener a defect.
    prev_body_prose = False
    prev_callout_prose = False

    def is_block_opener(stripped_content: str) -> str | None:
        if pipe_table_re.match(stripped_content):
            return "table"
        if html_block_open_re.match(stripped_content):
            return "figure/HTML block"
        # NOTE: display-math `$$` is intentionally NOT flagged here. Obsidian's
        # KaTeX/MathJax parser recognizes `$$` boundaries independently of
        # Markdown paragraph splitting, so a `$$` glued to prose still renders
        # as a standalone display block. Only Markdown/HTML block elements
        # (tables, <figure>) rely on paragraph separation to render correctly.
        return None

    for index, raw in enumerate(lines):
        line_no = index + 1
        stripped_raw = raw.strip()
        # --- frontmatter ---
        if index == 0 and stripped_raw == "---":
            in_frontmatter = True
            prev_body_prose = False
            continue
        if in_frontmatter:
            if stripped_raw == "---":
                in_frontmatter = False
            prev_body_prose = False
            continue
        # --- code fences ---
        fence_match = fence_open_re.match(raw)
        if fence_match:
            delim_char = fence_match.group(2)[0]
            delim = delim_char * len(fence_match.group(2))
            if fence is None:
                fence = delim
            elif raw.lstrip().startswith(delim):
                fence = None
            prev_body_prose = False
            prev_callout_prose = False
            continue
        if fence is not None:
            continue
        # --- HTML block depth tracking ---
        content_for_html = strip_quote_marker(raw) if is_quote_line(raw) else raw
        delta = html_depth_delta(content_for_html)
        if html_depth > 0 or delta > 0:
            # Is this line a block OPENER (depth 0 → >0) glued to preceding
            # prose? Check BEFORE updating depth. Detect on the raw line.
            opening_now = html_depth == 0 and delta > 0
            is_callout_here = is_quote_line(raw)
            if opening_now:
                # determine opener label via the raw stripped content
                raw_stripped_for_label = (strip_quote_marker(raw) if is_callout_here else raw).strip()
                if html_block_open_re.match(raw_stripped_for_label):
                    if is_callout_here and prev_callout_prose:
                        messages.append(
                            LintMessage(
                                line_no,
                                "missing blank `>` line before figure/HTML block: a block "
                                "element glued to the preceding prose line by a single "
                                "`\\n` does not render as a new block in Obsidian/CommonMark "
                                "— separate with a blank `>` line",
                            )
                        )
                    elif not is_callout_here and prev_body_prose:
                        messages.append(
                            LintMessage(
                                line_no,
                                "missing blank line before figure/HTML block: a block element "
                                "glued to the preceding prose line by a single `\\n` does not "
                                "render as a new block in Obsidian/CommonMark — separate with "
                                "a blank line (`\\n\\n`)",
                            )
                        )
            html_depth += delta
            if html_depth < 0:
                html_depth = 0
            prev_body_prose = False
            prev_callout_prose = False
            continue
        # Things that terminate a prose run WITHOUT being prose themselves
        # (headings, lists, blank lines, display-math, table rows): reset both.
        is_callout = is_quote_line(raw)
        # blank line (body) / blank `>` (callout)
        if not stripped_raw:
            prev_body_prose = False
            continue
        if HEADING_LEVEL_PATTERN.match(stripped_raw):
            prev_body_prose = False
            prev_callout_prose = False
            continue
        if list_item_re.match(raw):
            prev_body_prose = False
            prev_callout_prose = False
            continue

        if is_callout:
            callout_content = strip_quote_marker(raw)
            callout_stripped = callout_content.strip()
            if CALLOUT_TYPE_PATTERN.match(raw):
                prev_callout_prose = False
                continue
            if callout_stripped == "":
                prev_callout_prose = False
                continue
            # Is THIS line a block opener glued to preceding callout prose?
            opener = is_block_opener(callout_stripped)
            if opener and prev_callout_prose:
                messages.append(
                    LintMessage(
                        line_no,
                        f"missing blank `>` line before {opener}: a block element glued "
                        "to the preceding prose line by a single `\\n` does not render as "
                        "a new block in Obsidian/CommonMark — separate with a blank `>` "
                        "line",
                    )
                )
            # Update prose cursor: block openers / HTML / math-only lines are
            # NOT prose; everything else (题干 prose) is.
            prose_here = strip_math_for_count(callout_stripped).strip()
            if opener or html_block_open_re.match(callout_stripped) or not prose_here or pipe_table_re.match(callout_content):
                prev_callout_prose = False
            else:
                prev_callout_prose = True
            continue

        # --- BODY channel ---
        opener = is_block_opener(stripped_raw)
        if opener and prev_body_prose:
            messages.append(
                LintMessage(
                    line_no,
                    f"missing blank line before {opener}: a block element glued to the "
                    "preceding prose line by a single `\\n` does not render as a new "
                    "block in Obsidian/CommonMark — separate with a blank line (`\\n\\n`)",
                )
            )
        prose_here = strip_math_for_count(stripped_raw).strip()
        if opener or html_block_open_re.match(stripped_raw) or not prose_here or pipe_table_re.match(raw) or list_item_re.match(raw):
            prev_body_prose = False
        else:
            prev_body_prose = True
    return messages


def lint_question_callout_title_attached(
    lines: list[str],
    blocks: list[QuoteBlock],
    min_cjk_chars: int = 8,
) -> list[LintMessage]:
    """Enforce the rule that a question callout's TITLE line holds only the
    example/exercise label and its source tag — never the stem body.

    Why this lint exists: OCR frequently glues the stem's first sentence onto
    the same line as the `例题N (来源)` label, producing
    `> [!question] 例题 1 (2017・新课标 I ) 已知椭圆 $C: ...$` instead of
    splitting the stem to its own `>` line. This is a structural defect (the
    title line is simultaneously the "题号" and the "题干第一句"), and like the
    over-long-analysis lint it is **non-auto-fixable**: deciding where to
    break is a semantic judgment, so the fix is to re-run Step 2.7 against the
    raw transcript.

    Algorithm (anchored on the universal label, NOT on the source format):
      1. For each question callout, take its first content line (the text
         after `[!question]`).
      2. Match the label prefix `例题N` / `例N` / `练习N`. If no label, skip
         (not a labeled example/exercise).
      3. Repeatedly strip a LOOSE source suffix — round/angle/【】/[...] brackets
         as whole units, year digits, and exam/region tokens (新课标/全国/卷/年…).
         This collapses every legal source shape (`(2017・新课标 I)`,
         `【2018全国I】`, `2017年`, or none) to nothing.
      4. After stripping, inspect the remaining prose (math stripped via
         `strip_math_for_count` so a glued formula's LaTeX does not inflate the
         CJK count). Report the callout if EITHER:
           - the remaining prose BEGINS with a stem-start signal word
             (已知/设/若/求/如图/函数/曲线/椭圆/…) — strong evidence the stem
             body was glued on; OR
           - the remaining prose has ≥ `min_cjk_chars` CJK characters — a long
             tail after the label/source is almost certainly stem text.

    This two-condition test avoids false positives on legit long source labels
    (e.g. `例题 1 (2017・新课标 I · 文科) 选填题`): after stripping the bracketed
    source, `选填题` neither begins with a stem signal nor reaches the CJK
    threshold, so it is not flagged.
    """
    messages: list[LintMessage] = []
    for block in blocks:
        if not _is_question_callout(block):
            continue
        title = _first_content_line_of_block(block)
        if not title:
            continue
        if not QUESTION_LABEL_PREFIX_PATTERN.match(title):
            # No `例题N`/`例N`/`练习N` label → not in scope (e.g. a bare
            # `[!question] 题干` title with the stem starting on the same
            # line is covered by other structure rules, not this one).
            continue
        # Strip the label prefix itself.
        rest = QUESTION_LABEL_PREFIX_PATTERN.sub("", title, count=1)
        # Repeatedly strip the loose source suffix until a fixed point —
        # a source tag like `(2017・新课标 I)` is one bracket unit, but
        # `2017・新课标 I 文科` (no brackets) needs several passes. After each
        # pass, drop any leading whitespace/punctuation noise (`・`, `、`,
        # stray spaces) the source tag leaves behind, so the next pass sees
        # the real remaining content.
        previous = None
        while previous != rest and rest:
            previous = rest
            rest = QUESTION_SOURCE_SUFFIX_PATTERN.sub("", rest, count=1)
            rest = re.sub(r"^[・、，,\s]+", "", rest)
        if not rest:
            continue
        # Strip math before judging the remaining prose: a glued formula such
        # as `$C : \dfrac{x^2}{a^2} + ...$` should not inflate the CJK count.
        prose = strip_math_for_count(rest).strip()
        if not prose:
            continue
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", prose))
        begins_with_stem_signal = bool(QUESTION_STEM_START_PATTERN.match(prose))
        if begins_with_stem_signal or cjk_count >= min_cjk_chars:
            reason = (
                "stem-start signal word" if begins_with_stem_signal
                else f"≥{min_cjk_chars} CJK chars after label/source ({cjk_count})"
            )
            messages.append(
                LintMessage(
                    block.start_line,
                    f"question callout title line has the stem body glued after "
                    f"the label/source ({reason}); move the stem to its own '>' "
                    f"line — the title line should hold only the label and source",
                )
            )
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


def lint_bare_question_starts(lines: list[str], blocks: list[QuoteBlock]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    question_callout_line_numbers = {
        line_no
        for block in blocks
        if _is_question_callout(block)
        for line_no in range(block.start_line, block.end_line + 1)
    }
    for index, line in enumerate(lines, start=1):
        if index in question_callout_line_numbers:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ">")):
            continue
        if BARE_QUESTION_START_PATTERN.match(stripped):
            messages.append(
                LintMessage(
                    index,
                    "example/exercise stem must be wrapped in a `> [!question]` callout",
                )
            )
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


def lint_tables(lines: list[str], blocks: list[QuoteBlock]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    callout_line_numbers = quote_line_numbers_for_kind(blocks, "callout")
    for index, line in enumerate(lines, start=1):
        if MARKDOWN_TABLE_SEPARATOR_PATTERN.match(line) or MARKDOWN_TABLE_PATTERN.match(line):
            if index not in callout_line_numbers:
                messages.append(LintMessage(index, "Markdown tables are not allowed outside question callouts; use centered HTML tables"))

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


def lint_image_path(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for index, line in enumerate(lines, start=1):
        content = strip_quote_marker(line) if is_quote_line(line) else line

        for match in HTML_IMAGE_PATTERN.finditer(content):
            src = html_attributes(match.group(0)).get("src", "")
            message = _classify_image_path(src)
            if message is not None:
                messages.append(LintMessage(index, message))

        for match in MARKDOWN_IMAGE_PATH_PATTERN.finditer(content):
            src = match.group(1).strip()
            message = _classify_image_path(src)
            if message is not None:
                messages.append(LintMessage(index, message))

    return messages


def _classify_image_path(path: str) -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://")) or path.startswith("data:"):
        return None
    if path.startswith("doc2x/export/images/"):
        return None
    if path.startswith("images/"):
        return (
            "image path 'images/...' is likely wrong; use 'doc2x/export/images/...' "
            "(relative to source-transcript.md)"
        )
    return f"image path '{path}' does not match expected pattern 'doc2x/export/images/...'"


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


def lint_adjacent_figures_must_merge(lines: list[str]) -> list[LintMessage]:
    """Adjacent standalone <figure> blocks (separated only by blank lines) that
    each contain a single image must be merged into one side-by-side figure.

    Catches the regression where OCR cleanup emits each crop as its own
    `<figure>...</figure>` (each a single-image figure, so the existing
    multi-image-in-one-figure lint does not fire), leaving logically-grouped
    images as a vertical stack. Canonical rule: adjacent images belong in one
    `display:flex` figure.

    Only flags runs of >=2 single-image figures separated solely by blank
    lines (no prose between them). A run interrupted by a non-blank,
    non-figure line is treated as independent figures and not flagged.
    """
    messages: list[LintMessage] = []
    n = len(lines)
    i = 0
    # A "single-image figure block" = one `<figure ...>` line (possibly spanning
    # multiple lines until `</figure>`) that contains exactly one <img ...>.
    def parse_single_image_figure(start: int):
        """If lines[start] begins a single-image figure, return (end_index_exclusive, line1_number).
        Otherwise return None."""
        line = strip_quote_marker(lines[start]) if is_quote_line(lines[start]) else lines[start]
        if not HTML_FIGURE_START_PATTERN.search(line):
            return None
        # gather the full figure text (may span lines)
        idx = start
        buf = [line]
        # if the figure does not close on this line, walk forward
        if not HTML_FIGURE_END_PATTERN.search(line):
            while idx + 1 < n:
                idx += 1
                nxt = strip_quote_marker(lines[idx]) if is_quote_line(lines[idx]) else lines[idx]
                buf.append(nxt)
                if HTML_FIGURE_END_PATTERN.search(nxt):
                    break
        text = "\n".join(buf)
        img_count = len(HTML_IMAGE_PATTERN.findall(text))
        if img_count != 1:
            return None
        return idx + 1  # exclusive end

    while i < n:
        result = parse_single_image_figure(i)
        if result is None:
            i += 1
            continue
        # found a single-image figure at line i (1-based i+1); look ahead for a run
        run_start_line = i + 1
        run_count = 1
        cursor = result
        while cursor < n:
            # skip only blank lines between figures
            j = cursor
            while j < n and lines[j].strip() == "":
                j += 1
            if j >= n or j == cursor:
                break  # no blank gap or end of file
            nxt_result = parse_single_image_figure(j)
            if nxt_result is None:
                break
            run_count += 1
            cursor = nxt_result
        if run_count >= 2:
            messages.append(
                LintMessage(
                    run_start_line,
                    f"{run_count} adjacent single-image figures must be merged into one side-by-side figure (display:flex); "
                    "each crop as its own figure stacks them vertically. Merge `<figure>..</figure>\\n\\n<figure>..</figure>` "
                    "into one `<figure style=\"display:flex;...\">` with both <img> inside.",
                )
            )
        i = cursor if cursor > i else result
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


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def is_single_math_dollar(text: str, index: int) -> bool:
    if text[index] != "$" or is_escaped(text, index):
        return False
    if index > 0 and text[index - 1] == "$":
        return False
    if index + 1 < len(text) and text[index + 1] == "$":
        return False
    return True


def normalize_inline_math_boundary_spacing(text: str) -> tuple[str, bool]:
    """Trim spaces inside paired inline math without crossing between formulas."""
    result: list[str] = []
    changed = False
    index = 0
    while index < len(text):
        if not is_single_math_dollar(text, index):
            result.append(text[index])
            index += 1
            continue

        close = index + 1
        while close < len(text) and not is_single_math_dollar(text, close):
            close += 1

        if close >= len(text):
            result.append(text[index:])
            break

        body = text[index + 1 : close]
        fixed_body = body.strip()
        if fixed_body != body:
            changed = True
        result.append(f"${fixed_body}$")
        index = close + 1

    return "".join(result), changed


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

        # Rule: fill-in blank normalization. Do not rewrite Markdown table
        # separators such as `| :---: |`, which are used for choice grids.
        if not MARKDOWN_TABLE_SEPARATOR_PATTERN.match(body):
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

        # Rule: inline math spacing. Use paired-dollar scanning so adjacent
        # table cells such as `$x$ | B. $y$` are not collapsed into `$x$| B.$y$`.
        new_body, spacing_changed = normalize_inline_math_boundary_spacing(body)
        if spacing_changed:
            body = new_body
            changes.append(f"line {index}: normalized inline math boundary spacing")

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
            indent = line[: len(line) - len(line.lstrip())]
            fixed_lines.append(f"{indent}> {body}")
        elif is_quote and not body.strip():
            indent = line[: len(line) - len(line.lstrip())]
            fixed_lines.append(f"{indent}>")
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

def lint_qa_ordering(lines: list[str], blocks: list[QuoteBlock]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    question_blocks = [block for block in blocks if _is_question_callout(block)]
    for index in range(len(question_blocks) - 1):
        q1 = question_blocks[index]
        q2 = question_blocks[index + 1]
        if QA_SUBPART_PATTERN.match(_first_content_line_of_block(q2)):
            continue
        has_analysis = False
        has_interstitial_content = False
        for line_idx in range(q1.end_line, q2.start_line - 1):
            if 0 <= line_idx < len(lines):
                raw = lines[line_idx]
                content = strip_quote_marker(raw) if is_quote_line(raw) else raw
                if QA_ANALYSIS_LINE_PATTERN.search(content) or HTML_ANALYSIS_BLOCK_PATTERN.search(content):
                    has_analysis = True
                    break
                if content.strip():
                    has_interstitial_content = True
        if has_analysis or has_interstitial_content:
            continue

        later_analysis_before_heading = False
        for line_idx in range(q2.end_line, len(lines)):
            raw = lines[line_idx]
            content = strip_quote_marker(raw) if is_quote_line(raw) else raw
            stripped = content.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                break
            if QA_ANALYSIS_LINE_PATTERN.search(content) or HTML_ANALYSIS_BLOCK_PATTERN.search(content):
                later_analysis_before_heading = True
                break

        if later_analysis_before_heading:
            messages.append(
                LintMessage(
                    q1.start_line,
                    f"question at line {q1.start_line} has no analysis before next question at line {q2.start_line} — analysis must follow its question directly",
                )
            )
    return messages


def _collect_math_spans(lines: list[str]) -> list[tuple[int, str]]:
    cleaned: list[str] = []
    for raw in lines:
        content = strip_quote_marker(raw) if is_quote_line(raw) else raw
        cleaned.append(strip_mathml(content))
    full_text = "\n".join(cleaned)

    spans: list[tuple[int, str]] = []
    masked = list(full_text)
    for match in DISPLAY_MATH_PATTERN.finditer(full_text):
        inner = match.group(1)
        start_line = full_text.count("\n", 0, match.start(1)) + 1
        spans.append((start_line, inner))
        for k in range(match.start(), match.end()):
            if masked[k] != "\n":
                masked[k] = " "
    masked_text = "".join(masked)
    for match in INLINE_MATH_PATTERN.finditer(masked_text):
        inner = match.group(1)
        start_line = full_text.count("\n", 0, match.start(1)) + 1
        spans.append((start_line, inner))
    return spans


def _scan_fraction_context(math: str) -> list[tuple[int, str]]:
    nested_kinds = {"frac_num", "frac_den", "exp", "sub", "sqrt"}
    stack: list[tuple[str, str | None]] = []
    issues: list[tuple[int, str]] = []
    pending: str | None = None
    valid = True

    i = 0
    n = len(math)
    while i < n:
        ch = math[i]
        if ch == "\\":
            if i + 1 < n and ("a" <= math[i + 1] <= "z" or "A" <= math[i + 1] <= "Z"):
                j = i + 1
                while j < n and ("a" <= math[j] <= "z" or "A" <= math[j] <= "Z"):
                    j += 1
                word = math[i + 1:j]
                if word in ("dfrac", "tfrac"):
                    stack_kinds = {frame[0] for frame in stack}
                    is_nested = bool(stack_kinds & nested_kinds)
                    if word == "dfrac" and is_nested:
                        nearest = next(frame[0] for frame in reversed(stack) if frame[0] in nested_kinds)
                        issues.append((i, f"\\dfrac inside {nearest} should be \\tfrac (nested fraction rule)"))
                    elif word == "tfrac" and not is_nested:
                        issues.append((i, "\\tfrac in non-nested context should be \\dfrac"))
                    pending = "frac_num"
                elif word == "sqrt":
                    pending = "sqrt"
                i = j
                continue
            i += 2
            continue
        if ch == "^":
            if i + 1 < n and math[i + 1] == "{":
                pending = "exp"
            i += 1
            continue
        if ch == "_":
            if i + 1 < n and math[i + 1] == "{":
                pending = "sub"
            i += 1
            continue
        if ch == "[" and pending == "sqrt":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if math[j] == "[":
                    depth += 1
                elif math[j] == "]":
                    depth -= 1
                j += 1
            if depth != 0:
                valid = False
                break
            i = j
            continue
        if ch == "{":
            kind = pending if pending is not None else "other"
            if kind == "frac_num":
                stack.append(("frac_num", "frac_den"))
            else:
                stack.append((kind, None))
            pending = None
            i += 1
            continue
        if ch == "}":
            if not stack:
                valid = False
                break
            _frame_kind, next_after = stack.pop()
            if next_after == "frac_den":
                pending = "frac_den"
            i += 1
            continue
        i += 1

    if not valid or stack:
        return []
    return issues


def lint_fraction_nesting(lines: list[str]) -> list[LintMessage]:
    messages: list[LintMessage] = []
    for start_line, math in _collect_math_spans(lines):
        if "{" not in math:
            continue
        for rel_pos, text in _scan_fraction_context(math):
            line_no = start_line + math.count("\n", 0, rel_pos)
            messages.append(LintMessage(line_no, text))
    return messages


def _callout_type(block: QuoteBlock) -> str:
    for line in block.lines:
        match = CALLOUT_TYPE_PATTERN.match(line)
        if match:
            return match.group(1).lower()
    return ""


def _is_question_callout(block: QuoteBlock) -> bool:
    return block.kind == "callout" and _callout_type(block) == "question"


def _first_content_line_of_block(block: QuoteBlock) -> str:
    for line in block.lines:
        content = strip_quote_marker(line).strip()
        if not content:
            continue
        if content.startswith("[!"):
            rest = re.sub(r"^\[![^\]]*\]\s*", "", content).strip()
            if rest:
                return rest
            continue
        return content
    return ""


def lint_formula_dangling_tail(lines: list[str]) -> list[LintMessage]:
    """C1 (2026-06-29): catch a formula that ends mid-expression with its tail
    left outside math delimiters. The classic OCR/cleaning defect is
    `$...=$ 0.0296` or `$...+$ x` where the trailing operand/result leaked
    out as plain prose because the inline span was closed too early.

    Conservative structural heuristic (NOT a LaTeX parser):
    - scan each inline `$...$` span;
    - if the span body ENDS with a dangling operator or relation
      (`=`, `+`, `-`, `\times`, `\div`, `\cdot`, `\approx`, `\le`, `\ge`,
      `\Rightarrow`, `\sim`, `>`, `<`) followed by nothing meaningful;
    - AND the text right after the closing `$` looks like a stray value
      (a number, a `{...}` group, or math-looking token), not punctuation/
      prose;
    -> flag it. The fix is to extend the `$` span to include the tail
    (or move the whole thing to a `$$...$$` block).
    Acceptable prose after `$` (Chinese punctuation, `，`, `。`, `；`, a
    space + Chinese/English word, `**`, `<`) does NOT trigger.
    """
    messages: list[LintMessage] = []
    # operators/relations that signal "equation continues" if they are the
    # last meaningful token inside the span.
    dangling_ops = [
        "=", "+", "-", r"\times", r"\div", r"\cdot", r"\approx",
        r"\le", r"\ge", r"\leq", r"\geq", r"\Rightarrow", r"\rightarrow",
        r"\sim", ">", "<", r"\ne", r"\neq",
    ]
    # what counts as a "stray value tail" right after the closing `$`
    tail_value = re.compile(r"^\s*(?:-?\d|[0-9.]+|\{|\\|[a-zA-Z]\b)")
    # what is acceptable prose after `$` (no flag)
    safe_after = re.compile(r"^\s*(?:[，。；：、）》」』\]\)\.\,]|\*\*|<|$|\s+[^\d{\\])")
    for index, raw in enumerate(lines, start=1):
        line_without_mathml = strip_mathml(raw)
        cursor = 0
        for match in INLINE_MATH_PATTERN.finditer(line_without_mathml):
            body = match.group(1).strip()
            if not body:
                continue
            # does the body end with a dangling operator/relation?
            body_ends_dangling = any(body.rstrip().endswith(op) for op in dangling_ops)
            if not body_ends_dangling:
                continue
            after = line_without_mathml[match.end():]
            if safe_after.match(after):
                continue
            if tail_value.match(after):
                messages.append(
                    LintMessage(
                        index,
                        "formula appears truncated: it ends with an operator/relation "
                        "inside `$...$` but its trailing value is left outside as plain "
                        "text (e.g. `$...=$ 0.0296`). Extend the math span to include the "
                        "tail, or move the whole equation to a `$$...$$` display block.",
                    )
                )
                break
    return messages


def lint_list_inside_math(lines: list[str]) -> list[LintMessage]:
    """C2 (2026-06-29; reworked 2026-07-02): independent math UNITS crammed
    into one inline `$...$` span, separated by commas that should be OUTSIDE
    the math. Five shapes now detected:

      - multiple intervals: `$\\lbrack 5.31, 5.33), \\lbrack 5.33, 5.35), \\cdots$`
      - percentage/value series: `${60}\\% , {60}\\% , {65}\\%$`
      - comma-chained equations (added 2026-07-02): `${AM}=3, {BC}=10$`,
        `$f(0)=1, f(2)=3$` — independent equalities fused by a comma.
      - multiple labeled coordinate points (added 2026-07-02):
        `$A(0,0), B(3,-2), C(5,1)$` — each point is independent; the comma
        INSIDE `(x,y)` is structural and stays.
      - multiple independent single-letter variables (added 2026-07-02):
        `$A, B, C$`, `$k, l_1$`.

    Each unit should be its own `$...$` with the separator comma outside:
      `$\\lbrack 5.31, 5.33)$, $\\lbrack 5.33, 5.35)$, $\\cdots$`

    The KEY discriminant is bracket DEPTH: a comma at depth 0 (outside all
    `()`/`[]`/`{}`) between two independent units is a separator that should
    be outside the math; a comma inside `(x,y)` / `[a,b)` / `f(x,y)` / `{...}`
    is structural and is NEVER a split point. This depth-tracking is what lets
    the equation/point shapes be detected without false-flagging coordinates
    and function arguments.

    A single interval `$(0,1)$`, a single coordinate `$A(0,0)$`, or a function
    arg `$f(x,y)$` is NOT flagged (no depth-0 comma, or only one unit).

    <!-- evolved 2026-07-02 — the 2026-06-29 conservative heuristic only matched
    interval-list / percent-series (repeating-unit openers); it was SILENT on
    equation-chain / multi-point / multi-variable shapes, which are the COMMON
    cases in real transcripts (57 spans in one 必修二 file). Since this lint is
    the ③ math-comma-splitter role's self-check, a green lint falsely signaled
    the role was done. The depth-tracking detector closes that gap. -->
    """
    messages: list[LintMessage] = []
    # candidate repeating-unit openers (legacy interval/percent shapes).
    unit_openers = [
        re.compile(r"\\lbrack|\\left\\lbrack"),
        re.compile(r"\\\}\\\\?%|\\}\\\\?%|\}%"),
    ]
    CLOSERS = set(")]}")
    PAIR_OPEN = {"(": ")", "[": "]", "{": "}"}

    def depth_zero_comma_positions(body: str) -> list[int]:
        """Indices of commas at bracket depth 0 (the splittable separators).

        Skips `\\,` (LaTeX thin-space) — the backslash makes it a command, not
        a separator. Tracks `()`/`[]`/`{}` nesting."""
        depth = 0
        positions = []
        for i, ch in enumerate(body):
            if ch in PAIR_OPEN:
                depth += 1
            elif ch in CLOSERS:
                depth = max(0, depth - 1)
            elif depth == 0 and ch == ",":
                # exclude \, (thin space)
                if i > 0 and body[i - 1] == "\\":
                    continue
                positions.append(i)
        return positions

    def split_at(body: str, positions: list[int]) -> list[str]:
        """Split body at the given comma indices, dropping the commas."""
        segs = []
        prev = 0
        for pos in positions:
            segs.append(body[prev:pos])
            prev = pos + 1
        segs.append(body[prev:])
        return [s.strip() for s in segs if s.strip()]

    # multi-point shape: a unit starting with an uppercase letter followed by
    # `(` or `\left(` — e.g. `A(0,0)`, `B\left(3,-2\right)`.
    point_unit = re.compile(r"^[A-Z](?:\\left)?\(")
    # multi-variable shape: a unit is a single letter (optionally with sub/sup)
    single_letter_unit = re.compile(r"^[A-Za-z](?:[_^][A-Za-z0-9])?$")

    for index, raw in enumerate(lines, start=1):
        line_without_mathml = strip_mathml(raw)
        for match in INLINE_MATH_PATTERN.finditer(line_without_mathml):
            body = match.group(1)
            reason = None

            # --- legacy: interval-list / percent-series (repeating openers) ---
            if body.count(",") >= 2:
                for opener in unit_openers:
                    hits = opener.findall(body)
                    if len(hits) >= 2:
                        first = body.find(hits[0]) if hits else -1
                        last = body.rfind(hits[-1]) if hits else -1
                        segment = body[first:last] if first >= 0 and last > first else ""
                        if segment.count(",") >= 1:
                            reason = "a list of independent math units (intervals / values)"
                            break

            # --- new: depth-0-comma shapes (equation chain / multi-point /
            #     multi-variable) ---
            if reason is None:
                comma_positions = depth_zero_comma_positions(body)
                if len(comma_positions) >= 1:
                    units = split_at(body, comma_positions)
                    # need >= 2 units to be a "list"
                    if len(units) >= 2:
                        # equation chain: >= 2 units each containing '='
                        eq_units = [u for u in units if "=" in u]
                        if len(eq_units) >= 2:
                            reason = (
                                "comma-chained equations fused in one `$...$` span "
                                "(e.g. `${AM}=3, {BC}=10$`)"
                            )
                        # multi-point: >= 2 units shaped `A(...)` (and the comma
                        # inside the parens was correctly NOT a split point)
                        elif sum(1 for u in units if point_unit.match(u)) >= 2:
                            reason = (
                                "multiple labeled coordinate points fused in one `$...$` "
                                "span (e.g. `$A(0,0), B(3,-2)$`); the comma inside `(x,y)` "
                                "stays, the comma BETWEEN points should be outside"
                            )
                        # multi-variable: >= 3 units each a single letter (require 3
                        # to avoid false positives on 2-letter prose-like spans)
                        elif (
                            len(units) >= 3
                            and all(single_letter_unit.match(u) for u in units)
                        ):
                            reason = (
                                "multiple independent variables fused in one `$...$` span "
                                "(e.g. `$A, B, C$`)"
                            )

            if reason is not None:
                messages.append(
                    LintMessage(
                        index,
                        f"{reason}; split each unit into its own `$...$` with the "
                        "comma outside. Structural commas inside `(x,y)` / `[a,b)` / "
                        "`f(x,y)` / `{...}` are NOT split points — only depth-0 "
                        "commas between independent units are.",
                    )
                )
                break
    return messages


def lint_long_inline_formula(lines: list[str]) -> list[LintMessage]:
    """C4: a CHAIN inline `$...$` span — multiple equalities (an `a = b = c`
    chain) rendered so wide it overflows the A4 text area — is hard to read on
    one line and should be a `$$...$$` display block folded with
    `\\begin{aligned}`. A single long expression (one `=` or none) is a
    legitimate inline span and is NOT flagged (filtered by ``min_equals``).

    Width is measured by REAL rendered pixels via headless Chromium + KaTeX
    (``measure_inline_formula_width.measure_widths``), not by source-char count
    or regex macro folding. Three bands relative to the A4 text area (695px):

      * long   > 625px (90% A4): hard FAIL — almost certainly overflows/wraps
        ugly; fold to ``\\begin{aligned}``.
      * medium 464–625px (2/3..90%): NOTE hint — judge in context; may fit one
        line or need folding. Does NOT raise the exit code.
      * short  ≤ 464px: pass, keep inline.

    Evolved 2026-07-02: was a two-stage design (coarse regex estimate here as a
    HARD-GATE lint, then a separate manual ``measure_inline_formula_width.py``
    run to get the true px). The regex estimate was unsalvageable — it could
    not distinguish a 101-glyph medium chain from a 100-glyph long chain
    because macro folding has no notion of A4 geometry. The two stages are now
    collapsed: this lint measures the true width directly.

    HARD DEPENDENCY: requires Playwright + Chromium and network access to the
    KaTeX CDN. If Playwright is unavailable or a body renders to 0px (KaTeX
    failure / no network), the affected formula is reported as a hard FAIL
    ("measurement returned 0 — cannot judge") rather than silently passing.
    """
    # Imported lazily so the rest of the validator (and its tests for OTHER
    # lints) can run without Playwright installed.
    try:
        from measure_inline_formula_width import (
            A4_TEXT_WIDTH_PX,
            NINETY_PCT_PX,
            TWO_THIRDS_PX,
            measure_widths,
        )
    except ImportError as exc:
        raise RuntimeError(
            "lint_long_inline_formula requires measure_inline_formula_width.py "
            "(sibling module). " + str(exc)
        ) from exc

    messages: list[LintMessage] = []
    min_equals = 2

    # Collect every inline `$...$` candidate (>= min_equals equalities) across
    # the whole file, remembering the line of each occurrence. Bodies are
    # deduped for a single batched browser session (one launch measures all).
    occurrences: list[tuple[int, str]] = []  # (line_no, body)
    for index, raw in enumerate(lines, start=1):
        line_without_mathml = strip_mathml(raw)
        for match in INLINE_MATH_PATTERN.finditer(line_without_mathml):
            body = match.group(1)
            if body.count("=") >= min_equals:
                occurrences.append((index, body))

    if not occurrences:
        return messages

    unique_bodies: list[str] = []
    body_to_width: dict[str, float] = {}
    for _, body in occurrences:
        if body not in body_to_width:
            unique_bodies.append(body)
            body_to_width[body] = 0.0  # placeholder, filled after measurement

    widths = measure_widths(unique_bodies)
    for body, width in zip(unique_bodies, widths):
        body_to_width[body] = width

    pct = lambda px: round(px * 100 / A4_TEXT_WIDTH_PX)
    for line_no, body in occurrences:
        width = body_to_width[body]
        eq = body.count("=")
        if width <= 0.0:
            messages.append(
                LintMessage(
                    line_no,
                    f"inline math span width measurement returned 0px ({eq} equalities); "
                    "KaTeX render failed or no network — cannot judge. Ensure "
                    "Playwright+Chromium are installed and the KaTeX CDN is "
                    "reachable.",
                )
            )
        elif width > NINETY_PCT_PX:
            messages.append(
                LintMessage(
                    line_no,
                    f"inline math span renders {width:.0f}px wide (~{pct(width)}% of the "
                    f"{A4_TEXT_WIDTH_PX}px A4 text area) with {eq} equalities; fold into "
                    "a `$$...$$` display block with `\\begin{aligned}`.",
                )
            )
        elif width > TWO_THIRDS_PX:
            messages.append(
                LintMessage(
                    line_no,
                    f"inline math span renders {width:.0f}px wide (~{pct(width)}% of the "
                    f"{A4_TEXT_WIDTH_PX}px A4 text area) with {eq} equalities; judge in "
                    "context — may fit one line or read better folded.",
                    severity="hint",
                )
            )
        # short (<= TWO_THIRDS_PX): no message.
    return messages
    return messages


def lint_markdown(
    markdown_text: str,
    max_analysis_lines: int,
    max_analysis_paragraphs: int,
    max_analysis_line_chars: int,
    only: str | None = None,
) -> list[LintMessage]:
    lines = markdown_text.splitlines()
    blocks = collect_quote_blocks(lines)

    # Build the full lint registry as (name, callable) pairs. Keeping this as a
    # named registry (instead of a flat messages.extend chain) is what lets the
    # `--only` filter select individual lints by name — see the refinement-agent-chain
    # role->lint mapping in references/refinement-agent-chain.md.
    registry: list[tuple[str, callable]] = [
        ("lint_headings_and_print_noise", lambda: lint_headings_and_print_noise(lines)),
        ("lint_tables", lambda: lint_tables(lines, blocks)),
        ("lint_images", lambda: lint_images(lines)),
        ("lint_image_path", lambda: lint_image_path(lines)),
        ("lint_multi_image_figures", lambda: lint_multi_image_figures(lines)),
        ("lint_adjacent_figures_must_merge", lambda: lint_adjacent_figures_must_merge(lines)),
        ("lint_formulas", lambda: lint_formulas(lines)),
        ("lint_inline_math_spacing", lambda: lint_inline_math_spacing(lines)),
        ("lint_html_math", lambda: lint_html_math(lines)),
        ("lint_numeric_outline_labels", lambda: lint_numeric_outline_labels(lines, blocks)),
        ("lint_bare_blank_splits", lambda: lint_bare_blank_splits(lines)),
        (
            "lint_analysis",
            lambda: lint_analysis(
                lines,
                blocks,
                max_analysis_lines,
                max_analysis_paragraphs,
                max_line_chars=max_analysis_line_chars,
            ),
        ),
        ("lint_choice_options", lambda: lint_choice_options(lines, blocks)),
        ("lint_bare_question_starts", lambda: lint_bare_question_starts(lines, blocks)),
        ("lint_fraction_nesting", lambda: lint_fraction_nesting(lines)),
        ("lint_qa_ordering", lambda: lint_qa_ordering(lines, blocks)),
        ("lint_markdown_analysis_paragraphs", lambda: lint_markdown_analysis_paragraphs(lines)),
        ("lint_paragraph_separator", lambda: lint_paragraph_separator(lines)),
        ("lint_block_separator", lambda: lint_block_separator(lines)),
        ("lint_question_callout_title_attached", lambda: lint_question_callout_title_attached(lines, blocks)),
        ("lint_formula_dangling_tail", lambda: lint_formula_dangling_tail(lines)),
        ("lint_list_inside_math", lambda: lint_list_inside_math(lines)),
        ("lint_long_inline_formula", lambda: lint_long_inline_formula(lines)),
    ]

    # Apply the --only filter when set. Unknown names are a caller bug (a stale
    # role->lint mapping), so fail loudly rather than silently running nothing.
    if only:
        wanted = {name.strip() for name in only.split(",") if name.strip()}
        known = {name for name, _ in registry}
        unknown = wanted - known
        if unknown:
            raise SystemExit(
                f"ERROR: --only has unknown lint name(s): {sorted(unknown)}. "
                f"Known: {sorted(known)}"
            )
        registry = [item for item in registry if item[0] in wanted]

    messages: list[LintMessage] = []
    for _name, fn in registry:
        messages.extend(fn())
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
        only=args.only,
    )
    messages.extend(lint_rewrite_plan(job_dir, md_path))

    if messages:
        # exit code is raised only by error-severity messages; hints (severity
        # == "hint") print as NOTE: but do not fail the run.
        hard = [m for m in messages if m.severity != "hint"]
        if hard:
            update_job_status(job_dir, "failed")
        for message in sorted(messages, key=lambda item: item.line):
            prefix = f"line {message.line}: " if message.line else ""
            tag = "FAIL" if message.severity != "hint" else "NOTE"
            print(f"{tag}: {prefix}{message.text}")
        if hard:
            return 1

    update_job_status(job_dir, "passed")
    print(f"OK: canonical markdown passed for {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
