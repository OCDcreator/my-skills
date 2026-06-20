#!/usr/bin/env python3
"""Detect structural blockquote markers that leaked into math segments.

Obsidian callouts embed display-math blocks with every line prefixed by '>'.
If the builder does not strip those structural prefixes before protecting
math segments, MarkdownIt keeps the '>' inside the formula and they render as
literal '>' characters in the output.

Usage:
    python validate_math_quote_leakage.py --md source-transcript.md
"""

from __future__ import annotations

import argparse
import re
import sys


FENCED_CODE_BLOCK_PATTERN = re.compile(r"(^```[^\n]*\n.*?^```[ \t]*$)", re.MULTILINE | re.DOTALL)
INLINE_CODE_SPAN_PATTERN = re.compile(r"(`+)([^`\n]*?)\1")
MATH_SEGMENT_PATTERN = re.compile(r"\$\$.*?\$\$|\$.*?\$", re.DOTALL)
LEAK_PATTERN = re.compile(r"(?m)^[ \t]*>")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, help="Path to source-transcript markdown")
    parser.add_argument(
        "--max-snippets",
        type=int,
        default=10,
        help="Maximum leak snippets to print (default: 10)",
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


def find_math_leaks(text: str, max_snippets: int) -> list[dict[str, str]]:
    protected, code_segments = protect_code_segments(text)

    leaks: list[dict[str, str]] = []
    for match in MATH_SEGMENT_PATTERN.finditer(protected):
        segment = match.group(0)
        # Only multi-line display blocks can carry structural blockquote prefixes
        # on interior lines. Inline math ($...$) is not expected to span lines.
        if "\n" not in segment:
            continue

        # Check interior lines only; the opening/closing delimiter lines are
        # allowed to carry the structural blockquote prefix (e.g. "> $$").
        lines = segment.splitlines()

        # If neither delimiter line is a blockquote line, the block is not
        # embedded in a callout; leading '>' on interior lines is legitimate
        # formula content (e.g. aligned inequality chains).
        delimiter_is_quote = LEAK_PATTERN.match(lines[0]) or LEAK_PATTERN.match(lines[-1])
        if not delimiter_is_quote:
            continue

        for line_number, line in enumerate(lines[1:-1], start=2):
            if LEAK_PATTERN.match(line):
                # Map line offset back into the original (restored) text for reporting.
                prefix_lines = protected[: match.start()].count("\n") + line_number
                leaks.append(
                    {
                        "line": str(prefix_lines),
                        "snippet": restore_code_segments(line.strip(), code_segments),
                    }
                )
                break

            if len(leaks) >= max_snippets:
                break
        if len(leaks) >= max_snippets:
            break

    return leaks


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_path = args.md
    text = sys.stdin.read() if source_path == "-" else open(source_path, encoding="utf-8").read()

    leaks = find_math_leaks(text, args.max_snippets)

    if not leaks:
        print(f"OK: no blockquote markers leaked into math segments in {source_path}")
        return 0

    print(f"FAIL: {len(leaks)} math segment(s) contain leaked blockquote markers in {source_path}")
    for leak in leaks:
        print(f"  line {leak['line']}: {leak['snippet']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
