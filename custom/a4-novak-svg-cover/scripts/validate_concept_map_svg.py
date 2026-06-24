#!/usr/bin/env python3
"""Validate the A4 concept-map SVG for print readability.

Checks only artifact-level behavior: stable glyphs, A4 sizing, inline styling,
and non-overlapping card rectangles with a minimum visual gap.
"""

from __future__ import annotations

import argparse
import itertools
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


FORBIDDEN_GLYPHS = {
    "⇄": "double arrow is often missing in CJK/SVG/PDF viewers",
    "→": "right arrow is often missing in CJK/SVG/PDF viewers",
    "′": "prime mark can render as tofu in fallback fonts",
    "₀": "subscript zero can render as tofu in fallback fonts",
    "₁": "subscript one can render as tofu in fallback fonts",
    "₂": "subscript two can render as tofu in fallback fonts",
    "·": "middle dot can render as tofu in fallback fonts",
    "–": "en dash can render as tofu in fallback fonts",
}

REMOVED_PHRASES = (
    "概念  题型  方法的树形关联图谱",
    "导数与切线 | 树形知识图谱 | A4 portrait concept map",
    "A4 portrait concept map",
)

MATH_TEXT_PATTERNS = (
    (re.compile(r"\\(?:frac|sqrt|sum|int|lim|sin|cos|tan|ln|log|exp|alpha|beta|gamma|theta|lambda|omega|pi|Delta|begin|end)\b"), "LaTeX/math command"),
    (re.compile(r"\$|\\\(|\\\)|\\\[|\\\]"), "LaTeX math delimiter"),
    (re.compile(r"[A-Za-z0-9)}\]]\s*\^\s*[-+A-Za-z0-9({\\]"), "superscript marker"),
    (re.compile(r"[A-Za-z0-9)}\]]\s*_\s*[-+A-Za-z0-9({\\]"), "subscript marker"),
    (re.compile(r"\b(?:sin|cos|tan|ln|log|exp)\s*[A-Za-z(]"), "function name"),
    (re.compile(r"\b[a-zA-Z]\s*'\s*\("), "derivative function notation"),
    (re.compile(r"\b[a-zA-Z]\s*\([^)]*[a-zA-Z0-9][^)]*\)"), "function notation"),
    (re.compile(r"[A-Za-z0-9)}\]]\s*[=<>]\s*[-+A-Za-z0-9({\[]"), "equation/comparison"),
    (re.compile(r"[≤≥≈≠∈∉⊂⊆∪∩]"), "math symbol"),
    (re.compile(r"\b(?:x|y|t|u|v|n|m|k)\d+\b"), "indexed variable"),
    (re.compile(r"\b(?:alpha|beta|gamma|theta|lambda|omega|Delta|pi)\b"), "spelled math symbol"),
)


def local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def as_float(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(value)


def rect_bbox(el: ET.Element) -> tuple[float, float, float, float]:
    x = as_float(el.attrib.get("x"))
    y = as_float(el.attrib.get("y"))
    w = as_float(el.attrib.get("width"))
    h = as_float(el.attrib.get("height"))
    return x, y, x + w, y + h


def rect_label(el: ET.Element) -> str:
    cls = el.attrib.get("class", "") or "rect"
    x1, y1, x2, y2 = rect_bbox(el)
    return f"{cls} ({x1:.1f},{y1:.1f})-({x2:.1f},{y2:.1f})"


def class_tokens(el: ET.Element) -> set[str]:
    return set((el.attrib.get("class", "") or "").split())


def element_text(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


def has_ancestor_class(parent_map: dict[ET.Element, ET.Element], el: ET.Element, cls: str) -> bool:
    current = parent_map.get(el)
    while current is not None:
        if cls in class_tokens(current):
            return True
        current = parent_map.get(current)
    return False


def math_text_reason(text: str) -> str | None:
    normalized = " ".join(text.split())
    for pattern, reason in MATH_TEXT_PATTERNS:
        if pattern.search(normalized):
            return reason
    return None


def has_min_gap(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
    min_gap: float,
) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    separated_x = ax2 + min_gap <= bx1 or bx2 + min_gap <= ax1
    separated_y = ay2 + min_gap <= by1 or by2 + min_gap <= ay1
    return separated_x or separated_y


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", type=Path)
    parser.add_argument("--min-gap-mm", type=float, default=3.0)
    parser.add_argument(
        "--allow-raw-math-text",
        action="store_true",
        help="Human-approved escape hatch: permit formula-like visible <text> outside MathJax formula-fit groups.",
    )
    args = parser.parse_args(argv)

    root = ET.parse(args.svg).getroot()
    parent_map = {child: parent for parent in root.iter() for child in parent}
    errors: list[str] = []

    if root.attrib.get("width") != "210mm":
        errors.append(f"width must be 210mm, got {root.attrib.get('width')!r}")
    if root.attrib.get("height") != "297mm":
        errors.append(f"height must be 297mm, got {root.attrib.get('height')!r}")
    if root.attrib.get("viewBox") != "0 0 210 297":
        errors.append(f"viewBox must be '0 0 210 297', got {root.attrib.get('viewBox')!r}")

    style_count = sum(1 for el in root.iter() if local_name(el.tag) == "style")
    if style_count:
        errors.append(f"SVG must not depend on embedded CSS style blocks, found {style_count}")

    all_text = "".join(element_text(el) for el in root.iter() if local_name(el.tag) == "text")
    for phrase in REMOVED_PHRASES:
        if phrase in all_text:
            errors.append(f"removed phrase still present: {phrase}")
    for glyph, reason in FORBIDDEN_GLYPHS.items():
        if glyph in all_text:
            errors.append(f"forbidden glyph {glyph!r}: {reason}")

    formula_groups = [
        el
        for el in root.iter()
        if local_name(el.tag) == "g" and "formula-fit" in class_tokens(el)
    ]
    for index, el in enumerate(formula_groups, start=1):
        if not (el.attrib.get("data-formula-id") or "").strip():
            errors.append(f"formula-fit group #{index} missing data-formula-id")

    rects = [
        el
        for el in root.iter()
        if local_name(el.tag) == "rect"
        and "bg" not in class_tokens(el)
        and "label-shield" not in class_tokens(el)
        and "shadow" not in class_tokens(el)
        and not has_ancestor_class(parent_map, el, "formula-fit")
    ]
    for el in rects:
        if "fill" not in el.attrib:
            errors.append(f"rect missing fill: {rect_label(el)}")
        if "stroke" not in el.attrib:
            errors.append(f"rect missing stroke: {rect_label(el)}")

    texts = [el for el in root.iter() if local_name(el.tag) == "text"]
    raw_math_texts: list[tuple[str, str]] = []
    for el in texts:
        if "fill" not in el.attrib:
            errors.append(f"text missing fill: {element_text(el)!r}")
        if not has_ancestor_class(parent_map, el, "formula-fit"):
            text = element_text(el)
            if text:
                reason = math_text_reason(text)
                if reason:
                    raw_math_texts.append((text, reason))

    if raw_math_texts and not args.allow_raw_math_text:
        if not formula_groups:
            errors.append(
                "formula-like visible SVG text found but no MathJax "
                "g.formula-fit[data-formula-id] groups exist; run formulas.json "
                "through render_mathjax_svg.mjs and embed formula-fit groups"
            )
        for text, reason in raw_math_texts:
            errors.append(
                "raw formula-like SVG <text> must be rendered through the MathJax "
                f"formula pipeline: {text!r} ({reason})"
            )

    for left, right in itertools.combinations(rects, 2):
        if not has_min_gap(rect_bbox(left), rect_bbox(right), args.min_gap_mm):
            errors.append(
                "rects overlap or are too close "
                f"(< {args.min_gap_mm:g}mm): {rect_label(left)} <-> {rect_label(right)}"
            )

    if errors:
        print("FAIL concept map validation", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"PASS concept map validation: rects={len(rects)} texts={len(texts)} "
        f"formula_groups={len(formula_groups)} raw_math_texts=0 "
        f"min_gap_mm={args.min_gap_mm:g} forbidden_glyphs=0 style_blocks=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
