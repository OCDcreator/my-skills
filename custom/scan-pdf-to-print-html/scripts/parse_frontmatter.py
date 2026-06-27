#!/usr/bin/env python3
"""Minimal YAML frontmatter parser for source-transcript.md.

This module reads a leading `---\\n...\\n---\\n` block at the very top of a
markdown file, parses flat `key: value` lines into a dict, and returns the
dict alongside the markdown body with the frontmatter stripped.

Why hand-written (not pyyaml):
  The frontmatter here is deliberately simple — flat key:value pairs, no
  nesting, no lists, no quoting gymnastics. A 40-line parser avoids adding a
  pyyaml dependency just for two fields (pagination-level, cover).

Spec: see references/frontmatter-spec.md.

Contract:
  - Only a frontmatter block at the ABSOLUTE START of the text is recognized
    (anchored with \\A / start-of-string). A `---` that appears later in the
    body is a thematic break / table separator and is left untouched.
  - The opening `---` must be the first non-empty content. A leading BOM or
    leading blank lines before `---` are tolerated and skipped.
  - Unknown keys (not in META_FIELDS) are ignored but reported via warnings
    so typos surface instead of silently dropping intent.
  - Malformed frontmatter (e.g. missing closing `---`) is treated as "no
    frontmatter" — the whole text is returned as the body. This keeps the
    build resilient: a bad block never breaks rendering, it just yields no
    metadata (the caller falls back to defaults + AskUserQuestion).

Usage:
    from parse_frontmatter import parse_frontmatter
    meta, body = parse_frontmatter(markdown_text)
    # meta == {"pagination-level": "h3", "cover": "true"} or {} if none
    # body  == markdown_text with the leading ---...--- block removed
"""

from __future__ import annotations

import re
import sys

# Whitelist of recognized frontmatter keys. See references/frontmatter-spec.md.
# Anything else is ignored + warned, so a typo does not silently drop intent.
META_FIELDS: dict[str, set[str]] = {
    "pagination-level": {"h2", "h3"},
    "cover": {"true", "false"},
}

# A leading frontmatter block: optional BOM/blank lines, then --- ... ---.
# DOTALL so the inner .* spans newlines. Non-greedy so we stop at the FIRST
# closing --- (a frontmatter block is always the first thing in the file).
_FRONTMATTER_RE = re.compile(
    r"\A(?:\ufeff)?(?:[ \t]*\r?\n)*"   # optional BOM + leading blank lines
    r"---[ \t]*\r?\n"                  # opening fence
    r"(?P<body>.*?)"                   # frontmatter content (non-greedy)
    r"---[ \t]*\r?\n",                 # closing fence
    re.DOTALL,
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse a leading YAML frontmatter block.

    Returns (metadata_dict, stripped_text):
      - metadata_dict: {key: value} for recognized fields, lowercased values.
        Empty dict if there is no frontmatter or it is malformed.
      - stripped_text: the original text with the frontmatter block removed.
        If no frontmatter, stripped_text == text unchanged.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    raw_body = match.group("body")
    stripped_text = text[match.end():]

    metadata: dict[str, str] = {}
    warnings: list[str] = []

    for line in raw_body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            # Blank lines and YAML comments inside frontmatter are ignored.
            continue
        if ":" not in stripped:
            # A non-empty, non-comment line without a colon is malformed.
            # Abort: treat the whole thing as "no frontmatter" so the body
            # stays intact and the caller falls back to defaults. This is
            # safer than half-parsing.
            return {}, text
        key, _, value = stripped.partition(":")
        key = key.strip().lower()
        value = value.strip().lower()

        if key not in META_FIELDS:
            warnings.append(f"unknown frontmatter key (ignored): {key!r}")
            continue
        if value not in META_FIELDS[key]:
            warnings.append(
                f"frontmatter {key!r} has invalid value {value!r}; "
                f"allowed: {sorted(META_FIELDS[key])} (ignored)"
            )
            continue
        metadata[key] = value

    for w in warnings:
        print(f"WARNING [frontmatter]: {w}", file=sys.stderr)

    return metadata, stripped_text


def _self_test() -> int:
    """Quick sanity checks. Run: py -3 parse_frontmatter.py --self-test."""
    cases = [
        # (name, input, expected_meta_keys, expected_body_starts_with)
        (
            "normal frontmatter",
            "---\npagination-level: h3\ncover: true\n---\n# Title\nbody",
            {"pagination-level": "h3", "cover": "true"},
            "# Title",
        ),
        (
            "no frontmatter (starts with heading)",
            "# Title\nbody",
            {},
            "# Title",
        ),
        (
            "unknown key ignored + warned",
            "---\npagination-level: h3\nbogus: x\n---\n# T",
            {"pagination-level": "h3"},
            "# T",
        ),
        (
            "invalid value ignored + warned",
            "---\npagination-level: h5\n---\n# T",
            {},
            "# T",
        ),
        (
            "malformed (no closing fence) -> no frontmatter, body intact",
            "---\npagination-level: h3\n# Title",
            {},
            "---\npagination-level: h3\n# Title",
        ),
        (
            "leading blank lines before frontmatter tolerated",
            "\n\n---\ncover: false\n---\n# T",
            {"cover": "false"},
            "# T",
        ),
        (
            "body --- thematic break NOT eaten (only leading block parsed)",
            "# Title\n\n---\n\nmore text",
            {},
            "# Title",
        ),
        (
            "comment line in frontmatter ignored",
            "---\n# this is a comment\ncover: true\n---\n# T",
            {"cover": "true"},
            "# T",
        ),
    ]
    failed = 0
    for name, inp, exp_meta, exp_body_prefix in cases:
        meta, body = parse_frontmatter(inp)
        ok_meta = meta == exp_meta
        ok_body = body.startswith(exp_body_prefix)
        status = "PASS" if (ok_meta and ok_body) else "FAIL"
        if status == "FAIL":
            failed += 1
        print(f"[{status}] {name}")
        if not ok_meta:
            print(f"        meta expected={exp_meta} got={meta}")
        if not ok_body:
            print(f"        body expected to start with {exp_body_prefix!r}")
            print(f"        body actually starts: {body[:40]!r}")
    print(f"\n{'ALL PASS' if failed == 0 else f'{failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run built-in sanity checks")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(_self_test())
    parser.print_help()
