#!/usr/bin/env python3
"""Validate the A4 concept-map SVG for print readability.

Checks only artifact-level behavior: stable glyphs, A4 sizing, inline styling,
and non-overlapping card rectangles with a minimum visual gap.
"""

from __future__ import annotations

import argparse
import itertools
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


def has_ancestor_class(parent_map: dict[ET.Element, ET.Element], el: ET.Element, cls: str) -> bool:
    current = parent_map.get(el)
    while current is not None:
        if cls in class_tokens(current):
            return True
        current = parent_map.get(current)
    return False


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

    all_text = "".join(el.text or "" for el in root.iter() if local_name(el.tag) == "text")
    for phrase in REMOVED_PHRASES:
        if phrase in all_text:
            errors.append(f"removed phrase still present: {phrase}")
    for glyph, reason in FORBIDDEN_GLYPHS.items():
        if glyph in all_text:
            errors.append(f"forbidden glyph {glyph!r}: {reason}")

    rects = [
        el
        for el in root.iter()
        if local_name(el.tag) == "rect"
        and "bg" not in class_tokens(el)
        and "label-shield" not in class_tokens(el)
        and not has_ancestor_class(parent_map, el, "formula-fit")
    ]
    for el in rects:
        if "fill" not in el.attrib:
            errors.append(f"rect missing fill: {rect_label(el)}")
        if "stroke" not in el.attrib:
            errors.append(f"rect missing stroke: {rect_label(el)}")

    texts = [el for el in root.iter() if local_name(el.tag) == "text"]
    for el in texts:
        if "fill" not in el.attrib:
            errors.append(f"text missing fill: {el.text!r}")

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
        f"min_gap_mm={args.min_gap_mm:g} forbidden_glyphs=0 style_blocks=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
