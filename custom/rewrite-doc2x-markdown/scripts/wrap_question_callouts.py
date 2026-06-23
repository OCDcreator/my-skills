#!/usr/bin/env python3
"""Wrap bare example/exercise stems into canonical Obsidian question callouts.

This is a conservative fixer for existing canonical transcripts that still have
plain `【例题】` / `【练习】` stems outside `> [!question]`.

It only wraps the immediately contiguous question-stem region:
- stem line
- following blank lines
- subparts like `(1)` / `(2)` / `①`
- adjacent figures/tables that still belong to the stem

It stops before analysis/solution sections, hints, method lists, or the next
question/heading.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


QUESTION_START_PATTERN = re.compile(
    r"^\s*(?:【\s*)?(?P<label>例题|练习)(?:\s*(?P<num>[0-9一二三四五六七八九十百零]+))?(?:\s*[】)])?(?P<rest>.*)$"
)
SUBPART_PATTERN = re.compile(r"^\s*(?:[(（]\s*[\dIVXivx]+\s*[)）]|[①②③④⑤⑥⑦⑧⑨⑩])")
ANALYSIS_START_PATTERN = re.compile(
    r"^\s*(?:\*\*(?:解析|解答|证明|分析|备注|归纳总结|总结)\*\*|#{3,}\s*(?:解析|解答|证明|分析|备注|归纳总结|总结)|(?:【\s*)?(?:解析|解答|证明|分析|备注|归纳总结|总结)(?:\s*[】:：])?)"
)
METHOD_OR_HINT_PATTERN = re.compile(
    r"^\s*(?:提示[:：]|方法[一二三四五六七八九十0-9]|法[一二三四五六七八九十0-9]|策略[一二三四五六七八九十0-9])"
)
QUESTION_CONTINUATION_PATTERN = re.compile(r"^\s*(?:证明|求证|说明|求|若|设)[:：]")
HEADING_PATTERN = re.compile(r"^\s*#{2,6}\s+")
QUESTION_CALLOUT_PATTERN = re.compile(r"^\s*>\s*\[!question\]")
HTML_TABLE_LINE_PATTERN = re.compile(r"^\s*<(?:(?:table|tr|td|th|thead|tbody)\b|/table|/tr|/td|/th|/thead|/tbody)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, help="Path to source-transcript.md")
    parser.add_argument("--fix", action="store_true", help="Write fixes back to the file")
    return parser


def is_question_start(line: str) -> bool:
    stripped = line.strip()
    match = QUESTION_START_PATTERN.match(stripped)
    if not match:
        return False
    rest = (match.group("rest") or "").strip()
    return bool(rest) or "】" in stripped or "(" in stripped or "（" in stripped


def is_quoted(line: str) -> bool:
    return line.lstrip().startswith(">")


def callout_title(line: str) -> str:
    match = QUESTION_START_PATTERN.match(line.strip())
    if not match:
        return line.strip()
    label = match.group("label")
    num = (match.group("num") or "").strip()
    rest = (match.group("rest") or "").strip()
    title = label + (f" {num}" if num else "")
    return f"{title} {rest}".strip()


def should_keep_in_stem(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if is_question_start(stripped):
        return False
    if HEADING_PATTERN.match(stripped):
        return False
    if QUESTION_CALLOUT_PATTERN.match(stripped):
        return False
    if ANALYSIS_START_PATTERN.match(stripped):
        return False
    if METHOD_OR_HINT_PATTERN.match(stripped):
        return False
    if QUESTION_CONTINUATION_PATTERN.match(stripped):
        return True
    if SUBPART_PATTERN.match(stripped):
        return True
    if stripped.startswith("<figure") or stripped.startswith("</figure>"):
        return True
    if stripped.startswith("<img") or stripped.startswith("<figcaption"):
        return True
    if HTML_TABLE_LINE_PATTERN.match(stripped):
        return True
    return True


def wrap_questions(lines: list[str]) -> tuple[list[str], list[str]]:
    out: list[str] = []
    changes: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if is_quoted(line) or not is_question_start(line):
            out.append(line)
            i += 1
            continue

        start = i
        block: list[str] = [line]
        i += 1
        while i < len(lines) and should_keep_in_stem(lines[i]):
            block.append(lines[i])
            i += 1

        title = callout_title(block[0])
        out.append(f"> [!question] {title}")
        for body_line in block[1:]:
            if body_line.strip():
                out.append(f"> {body_line}")
            else:
                out.append(">")
        out.append("")
        changes.append(f"wrapped bare question stem starting at line {start + 1}")

    return out, changes


def merge_question_continuations(lines: list[str]) -> tuple[list[str], list[str]]:
    merged: list[str] = []
    changes: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        merged.append(line)
        if QUESTION_CALLOUT_PATTERN.match(line):
            j = i + 1
            # consume existing quoted body
            while j < len(lines) and (lines[j].startswith(">") or not lines[j].strip()):
                if not lines[j].strip():
                    merged.append(">")
                else:
                    merged.append(lines[j])
                j += 1

            while j < len(lines):
                candidate = lines[j]
                stripped = candidate.strip()
                if not stripped:
                    merged.append(">")
                    j += 1
                    continue
                if QUESTION_CONTINUATION_PATTERN.match(stripped):
                    merged.append(f"> {candidate}")
                    changes.append(f"merged question continuation at line {j + 1} into preceding callout")
                    j += 1
                    continue
                if stripped.startswith("<figure") or stripped.startswith("</figure>") or stripped.startswith("<img") or stripped.startswith("<figcaption") or HTML_TABLE_LINE_PATTERN.match(stripped):
                    merged.append(f"> {candidate}")
                    changes.append(f"merged question figure/table line at {j + 1} into preceding callout")
                    j += 1
                    continue
                break

            i = j
            continue

        i += 1
    return merged, changes


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    md_path = Path(args.md).expanduser().resolve()
    if not md_path.exists():
        raise SystemExit(f"file not found: {md_path}")

    original_text = md_path.read_text(encoding="utf-8")
    lines = original_text.splitlines()
    fixed_lines, changes = wrap_questions(lines)
    fixed_lines, merge_changes = merge_question_continuations(fixed_lines)
    changes.extend(merge_changes)

    if not changes:
        print("OK: no bare question stems found")
        return

    print(f"Found {len(changes)} bare question block(s):")
    for change in changes:
        print(f"  - {change}")

    if args.fix:
        fixed_text = "\n".join(fixed_lines)
        if original_text.endswith("\n") or not fixed_text.endswith("\n"):
            fixed_text += "\n"
        md_path.write_text(fixed_text, encoding="utf-8")
        print(f"Fixed: {md_path}")


if __name__ == "__main__":
    main()
