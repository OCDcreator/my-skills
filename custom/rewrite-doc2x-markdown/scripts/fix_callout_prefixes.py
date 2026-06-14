#!/usr/bin/env python3
"""Fix callout prefix issues in canonical Markdown from Doc2X OCR.

This script fixes:
1. Missing `>` prefix on `[!question]` / `[!example]` lines inside callouts
2. `> >` double-prefix artifacts
3. Stray orphaned `>` lines at callout boundaries
4. Missing `>` prefix on lines inside callout blocks (between `[!question]` and `**解析**`)

Usage:
    py -3 fix_callout_prefixes.py --md "path/to/source-transcript.md" [--fix]

Without --fix, reports issues. With --fix, writes corrected file.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


CALLOUT_START_PATTERN = re.compile(r"^\s*(>\s*)?\[!question\]|^\s*(>\s*)?\[!example\]")
CALLOUT_END_PATTERN = re.compile(r"^\s*\*\*解析\*\*|^\s*\*\*解\*\*|^\s*#{1,6}\s+|^\s*$|^\s*---\s*$")


def find_callout_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Find start and end line indices (0-based) of each callout block."""
    blocks: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        if CALLOUT_START_PATTERN.match(lines[i]):
            start = i
            # Find end: next line that is NOT part of the callout
            j = i + 1
            while j < len(lines):
                line = lines[j]
                # Callout ends when we hit a non-quoted line that looks like a new section
                if not line.strip().startswith(">") and CALLOUT_END_PATTERN.match(line):
                    break
                # Also end if we see another callout start
                if CALLOUT_START_PATTERN.match(line):
                    break
                j += 1
            blocks.append((start, j - 1))
            i = j
        else:
            i += 1
    return blocks


def fix_callout_prefixes(lines: list[str]) -> tuple[list[str], list[str]]:
    """Fix missing `>` prefixes inside callout blocks. Returns (fixed_lines, changes)."""
    fixed = list(lines)
    changes: list[str] = []
    blocks = find_callout_blocks(fixed)

    for start, end in blocks:
        for idx in range(start, end + 1):
            line = fixed[idx]
            stripped = line.strip()
            
            # Skip empty lines (keep them as-is or add > if needed)
            if not stripped:
                continue
            
            # Already has > prefix — check for double prefix
            if stripped.startswith("> "):
                # Check for > > artifact
                if stripped.startswith("> > "):
                    fixed[idx] = line.replace("> > ", "> ", 1)
                    changes.append(f"line {idx + 1}: removed double '> >' prefix")
                continue
            
            if stripped.startswith(">"):
                # Has > but no space after
                if not stripped.startswith("> "):
                    fixed[idx] = line.replace(">", "> ", 1)
                    changes.append(f"line {idx + 1}: added space after '>' prefix")
                continue
            
            # Missing > prefix — add it
            # Preserve indentation
            indent = line[:len(line) - len(line.lstrip())]
            fixed[idx] = indent + "> " + stripped
            changes.append(f"line {idx + 1}: added missing '> ' prefix to callout line")

    # Remove orphaned > lines (lines with just > that are not inside callouts)
    i = 0
    while i < len(fixed):
        line = fixed[i]
        if line.strip() == ">" and not any(start <= i <= end for start, end in blocks):
            fixed[i] = ""
            changes.append(f"line {i + 1}: removed orphaned '>' line")
        i += 1

    return fixed, changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", required=True, help="Path to source-transcript.md")
    parser.add_argument("--fix", action="store_true", help="Apply fixes to the file")
    args = parser.parse_args()

    md_path = Path(args.md)
    if not md_path.exists():
        print(f"ERROR: file not found: {md_path}")
        return

    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    fixed_lines, changes = fix_callout_prefixes(lines)

    if not changes:
        print("OK: no callout prefix issues found")
        return

    print(f"Found {len(changes)} callout issue(s):")
    for change in changes:
        print(f"  - {change}")

    if args.fix:
        fixed_text = "\n".join(fixed_lines)
        if not fixed_text.endswith("\n"):
            fixed_text += "\n"
        md_path.write_text(fixed_text, encoding="utf-8")
        print(f"\nFixed: {md_path}")
    else:
        print("\nUse --fix to apply changes")


if __name__ == "__main__":
    main()
