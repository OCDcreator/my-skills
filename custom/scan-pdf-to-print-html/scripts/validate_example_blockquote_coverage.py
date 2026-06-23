#!/usr/bin/env python3
"""Detect example/exercise labels that are NOT inside a `>` blockquote region.

The postprocess step (postprocess_handout_for_contract.py) auto-wraps standard
`例/例题/练习 N` paragraphs into `.phycat-blockquote`, but its regex
(`isExampleParagraph`) only matches a fixed set of label shapes. Non-standard
label forms (e.g. `**例题1**`, `【例 1】`, `例题一：`, decorative variants) are
silently left as plain paragraphs and render without the example quote styling.

This gate is a PRE-BUILD source check: it scans source-transcript.md line by
line, tracks whether the current line is inside a `>` blockquote region, and
reports any example/exercise labeled paragraph that falls OUTSIDE such a region.
Fix the transcript (wrap the paragraph with `>` / make it a callout) before
building, so the postprocess auto-wrap and the rendered `.phycat-blockquote`
styling both apply.

Note on the analysis boundary: `解析`/`解`/`证明` paragraphs are intentionally
NOT required to be inside a blockquote (the rewrite skill's lint_analysis
forbids analysis from using blockquote). This gate matches only example/
exercise labels, so analysis paragraphs are never flagged.

Usage:
    python validate_example_blockquote_coverage.py --md source-transcript.md
"""

from __future__ import annotations

import argparse
import re
import sys


# A line whose stripped form starts with `>`, including `> [!question] ...`
# callout title lines and `> text` body lines. A bare blank line does not count.
QUOTE_LINE_PATTERN = re.compile(r"^[ \t]*>")

# Fenced code blocks and inline code spans are protected so that a literal
# `例题` inside a code block is not mistaken for a real example label.
FENCED_CODE_BLOCK_PATTERN = re.compile(r"(^```[^\n]*\n.*?^```[ \t]*$)", re.MULTILINE | re.DOTALL)
INLINE_CODE_SPAN_PATTERN = re.compile(r"(`+)([^`\n]*?)\1")

# An example/exercise label paragraph. The label (例题/练习) must be followed by
# a number (Arabic or Chinese) — this is what distinguishes a real labeled
# example from mid-sentence words like 例如/举例/例外 (which carry no number).
# Optional surrounding bold/italic markers and brackets are tolerated.
#
# Shapes covered:
#   例题1 / 例题 1 / 练习1 / 练习 1
#   【例题1】 / [例题1] / 【练习 1】 / （练习2）
#   **例题1** ... / *练习三*
#   Chinese-numeral variants: 例题一 / 练习十
EXAMPLE_LABEL_PATTERN = re.compile(
    r"^[ \t]*"
    r"(?:\*{1,2}\s*)?"            # optional opening bold/italic marker
    r"(?:【|\[|（|\()?"            # optional opening bracket
    r"\s*"
    r"(?:例题|练习)"               # the label itself (例 alone is too ambiguous)
    r"\s*"
    r"[0-9一二三四五六七八九十百零两]+"  # MANDATORY number — excludes 例如/举例/例外
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, help="Path to source-transcript markdown")
    parser.add_argument(
        "--max-findings",
        type=int,
        default=15,
        help="Maximum uncovered example labels to report (default: 15)",
    )
    return parser


def protect_code_segments(text: str) -> tuple[str, list[str]]:
    segments: list[str] = []

    def stash(match: re.Match[str]) -> str:
        token = f"@@CODESEGMENT{len(segments)}@@"
        segments.append(match.group(0))
        return token

    protected = FENCED_CODE_BLOCK_PATTERN.sub(stash, text)
    protected = INLINE_CODE_SPAN_PATTERN.sub(stash, protected)
    return protected, segments


def restore_code_segments(text: str, segments: list[str]) -> str:
    restored = text
    for index, segment in enumerate(segments):
        restored = restored.replace(f"@@CODESEGMENT{index}@@", segment)
    return restored


def find_uncovered_example_labels(text: str, max_findings: int) -> list[dict[str, str]]:
    protected, code_segments = protect_code_segments(text)

    findings: list[dict[str, str]] = []
    in_quote = False  # True once we are inside a `>` blockquote region.

    for index, raw_line in enumerate(protected.splitlines(), start=1):
        stripped = raw_line.strip()

        # A blank line ends a blockquote region in Markdown semantics.
        if not stripped:
            in_quote = False
            continue

        is_quote_line = bool(QUOTE_LINE_PATTERN.match(raw_line))
        if is_quote_line:
            in_quote = True
            continue

        # A non-blank, non-`>` line: we are now outside any blockquote region.
        in_quote = False

        if EXAMPLE_LABEL_PATTERN.match(raw_line) and not in_quote:
            findings.append(
                {
                    "line": str(index),
                    "snippet": restore_code_segments(stripped, code_segments)[:80],
                }
            )
            if len(findings) >= max_findings:
                break

    return findings


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_path = args.md
    text = sys.stdin.read() if source_path == "-" else open(source_path, encoding="utf-8").read()

    findings = find_uncovered_example_labels(text, args.max_findings)

    if not findings:
        print(f"OK: every example/exercise label is inside a blockquote region in {source_path}")
        return 0

    print(
        f"FAIL: {len(findings)} example/exercise label(s) are NOT inside a `>` "
        f"blockquote region in {source_path}"
    )
    print(
        "  Wrap each flagged paragraph with `>` (or make it an Obsidian "
        "callout) so the postprocess auto-wrap and `.phycat-blockquote` "
        "styling apply. Analysis (解析) paragraphs should stay OUT of blockquotes."
    )
    for finding in findings:
        print(f"  line {finding['line']}: {finding['snippet']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
