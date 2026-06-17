#!/usr/bin/env python3
"""Generate the A4 derivative/tangent concept map SVG with calculated layout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


OUT = Path(__file__).with_name("concept-map.svg")
FONT = 'SimSun, "Source Han Serif SC", "Noto Serif CJK SC", serif'


@dataclass(frozen=True)
class Box:
    key: str
    cls: str
    x: float
    y: float
    w: float
    h: float
    fill: str
    stroke: str
    title: str
    lines: tuple[str, ...] = ()
    title_size: float = 3.25
    line_size: float = 2.25
    title_fill: str = "#172033"
    line_fill: str = "#555d6d"
    stroke_width: float = 0.48
    rx: float = 2.2

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h


def fmt(value: float) -> str:
    if abs(value - round(value)) < 0.001:
        return str(int(round(value)))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def attrs(**kwargs: object) -> str:
    parts: list[str] = []
    for key, value in kwargs.items():
        if value is None:
            continue
        xml_key = "class" if key == "cls" else key.replace("_", "-")
        parts.append(f'{xml_key}="{escape(str(value), {"\"": "&quot;"})}"')
    return " ".join(parts)


def text(
    x: float,
    y: float,
    content: str,
    *,
    size: float,
    fill: str,
    weight: int | None = None,
    anchor: str = "middle",
) -> str:
    return (
        "  <text "
        + attrs(
            x=fmt(x),
            y=fmt(y),
            text_anchor=anchor,
            font_family=FONT,
            fill=fill,
            font_size=f"{size}px",
            font_weight=weight,
            dominant_baseline="middle",
        )
        + f">{escape(content)}</text>"
    )


def rect(box: Box) -> str:
    return (
        "  <rect "
        + attrs(
            cls=box.cls,
            x=fmt(box.x),
            y=fmt(box.y),
            width=fmt(box.w),
            height=fmt(box.h),
            rx=fmt(box.rx),
            ry=fmt(box.rx),
            fill=box.fill,
            stroke=box.stroke,
            stroke_width=box.stroke_width,
        )
        + " />"
    )


def box_group(box: Box, *, shadow: bool = False) -> list[str]:
    out: list[str] = []
    if shadow:
        out.append('  <g filter="url(#softShadow)">')
        indent = "    "
    else:
        out.append("  <g>")
        indent = "    "
    out.append(indent + rect(box).strip())
    row_count = 1 + len(box.lines)
    if box.title_size > 6:
        line_step = 5.0
    elif row_count >= 5:
        line_step = 6.1
    elif row_count >= 3:
        line_step = 4.15
    else:
        line_step = 4.7
    center_y = box.y + box.h / 2
    title_y = center_y - ((row_count - 1) * line_step / 2)
    out.append(
        indent
        + text(
            box.cx,
            title_y,
            box.title,
            size=box.title_size,
            fill=box.title_fill,
            weight=700,
        ).strip()
    )
    for i, line in enumerate(box.lines):
        out.append(
            indent
            + text(
                box.cx,
                title_y + (i + 1) * line_step,
                line,
                size=box.line_size,
                fill=box.line_fill,
            ).strip()
        )
    out.append("  </g>")
    return out


def edge(parent: Box, child: Box, *, dashed: bool = False, strong: bool = False) -> str:
    start_x, start_y = parent.cx, parent.bottom
    end_x, end_y = child.cx, child.top
    mid_y = (start_y + end_y) / 2
    stroke = "#aeb7c6" if strong else "#c9d0dc"
    stroke_width = 0.48 if strong else 0.42
    d = f"M{fmt(start_x)} {fmt(start_y)} C{fmt(start_x)} {fmt(mid_y)} {fmt(end_x)} {fmt(mid_y)} {fmt(end_x)} {fmt(end_y)}"
    return (
        "  <path "
        + attrs(
            cls="edge-strong" if strong else "edge",
            marker_end="url(#arrow)",
            d=d,
            fill="none",
            stroke=stroke,
            stroke_width=stroke_width,
            stroke_opacity="0.58" if not strong else "0.66",
            stroke_linecap="round",
            stroke_linejoin="round",
            stroke_dasharray="2 2" if dashed else None,
        )
        + " />"
    )


def label(x: float, y: float, content: str) -> str:
    shield_w = max(11.0, len(content) * 2.25 + 2.4)
    shield_h = 4.3
    shield = (
        "  <rect "
        + attrs(
            cls="label-shield",
            x=fmt(x - shield_w / 2),
            y=fmt(y - 3.0),
            width=fmt(shield_w),
            height=fmt(shield_h),
            rx="1.2",
            ry="1.2",
            fill="#faf9f5",
            fill_opacity="0.94",
            stroke="none",
        )
        + " />"
    )
    return shield + "\n" + text(x, y, content, size=2.15, fill="#6f788b")


def build() -> str:
    root = Box(
        "root",
        "root",
        57,
        14,
        96,
        20,
        "#172033",
        "#172033",
        "导数与切线",
        (),
        title_size=7.2,
        line_size=3.0,
        title_fill="#fffdf9",
        line_fill="#dbe3f1",
        stroke_width=0.8,
        rx=5,
    )
    core = Box(
        "core",
        "node gold",
        59,
        48,
        92,
        16,
        "#f5efda",
        "#8a6b24",
        "核心转化",
        ("切线条数 对应 切点个数 对应 方程解 对应 零点",),
        title_size=4.35,
        line_size=2.6,
        line_fill="#687083",
        stroke_width=0.65,
        rx=2.8,
    )

    branches = [
        Box("basic", "node blue", 12, 84, 42, 18, "#e8eef7", "#244c7f", "切线基本问题", ("在点 / 过点",), 4.1, 2.6, line_fill="#687083", stroke_width=0.65, rx=2.8),
        Box("common", "node orange", 58, 84, 44, 18, "#f7ede5", "#c46f3b", "公切线问题", ("两曲线同切线",), 4.1, 2.6, line_fill="#687083", stroke_width=0.65, rx=2.8),
        Box("distance", "node green", 106, 84, 48, 18, "#e7f1ed", "#397161", "夹线与距离", ("不等式 / 最值 / 几何量",), 4.1, 2.45, line_fill="#687083", stroke_width=0.65, rx=2.8),
        Box("count", "node violet", 158, 84, 40, 18, "#eeeaf6", "#65528f", "切线条数", ("区域计数法",), 4.1, 2.6, line_fill="#687083", stroke_width=0.65, rx=2.8),
    ]

    leaves = [
        Box("basic-a", "leaf", 12, 116, 42, 17, "#fffdf9", "#c9c3b8", "在点切线", ("已知切点", "斜率=f'(x0)")),
        Box("basic-b", "leaf", 12, 139, 42, 17, "#fffdf9", "#c9c3b8", "过点切线", ("设未知切点", "解 x0 个数")),
        Box("basic-note", "tag", 12, 162, 42, 20, "#fffdf9", "#d7d0c3", "第1讲", ("区分在点和过点", "切线方程定参数"), 3.0, 2.15, stroke_width=0.38, rx=1.7),
        Box("common-a", "leaf", 58, 116, 44, 17, "#fffdf9", "#c9c3b8", "凹凸相同", ("外公切线", "交点数类比")),
        Box("common-b", "leaf", 58, 139, 44, 17, "#fffdf9", "#c9c3b8", "凹凸相反", ("内公切线", "上下函数")),
        Box("common-c", "leaf", 58, 162, 44, 18, "#fffdf9", "#c9c3b8", "公共点公切线", ("函数值相等", "导数值相等")),
        Box("common-note", "tag", 58, 186, 44, 20, "#fffdf9", "#d7d0c3", "第2-4讲", ("分别设切点", "斜率和截距相等"), 3.0, 2.15, stroke_width=0.38, rx=1.7),
        Box("distance-a", "leaf", 106, 116, 48, 17, "#fffdf9", "#c9c3b8", "曲线夹切线", ("恒成立转边界", "边界多为切线")),
        Box("distance-b", "leaf", 106, 139, 48, 17, "#fffdf9", "#c9c3b8", "距离问题", ("平行切线", "距离最小")),
        Box("distance-c", "leaf", 106, 162, 48, 18, "#fffdf9", "#c9c3b8", "二元函数最值", ("消元 参变分离", "构造函数")),
        Box("distance-note", "tag", 106, 186, 48, 20, "#fffdf9", "#d7d0c3", "第5-7讲", ("临界直线", "切线即边界"), 3.0, 2.15, stroke_width=0.38, rx=1.7),
        Box("count-a", "leaf", 158, 116, 40, 17, "#fffdf9", "#c9c3b8", "区域法", ("先分区", "再计数")),
        Box("count-b", "leaf", 158, 139, 40, 17, "#fffdf9", "#c9c3b8", "外三", ("外部区域", "三条切线")),
        Box("count-c", "leaf", 158, 162, 40, 17, "#fffdf9", "#c9c3b8", "内一", ("区域内", "一条切线")),
        Box("count-d", "leaf", 158, 185, 40, 17, "#fffdf9", "#c9c3b8", "上二", ("切线或曲线上", "两条切线")),
        Box("count-note", "tag", 158, 208, 40, 18, "#fffdf9", "#d7d0c3", "第8讲", ("拐点切线", "区域判断"), 3.0, 2.15, stroke_width=0.38, rx=1.7),
    ]
    by_key = {b.key: b for b in [root, core, *branches, *leaves]}

    method = Box(
        "method",
        "tag",
        12,
        232,
        104,
        42,
        "#fffdf9",
        "#d7d0c3",
        "通用解题链",
        (
            "1. 设切点: 未知点写成 x0/x1/x2",
            "2. 写切线: 点斜式 + 导数几何意义",
            "3. 建方程: 斜率 截距 过点 相切",
            "4. 数形转化: 零点 交点 单调 极值 区域",
        ),
        title_size=3.35,
        line_size=2.25,
        stroke_width=0.38,
        rx=1.7,
    )

    lines: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297" role="img" aria-labelledby="title desc">',
        '  <title id="title">导数与切线知识概念图</title>',
        '  <desc id="desc">以 Novak 概念图方式呈现导数与切线讲义中概念、题型、方法之间的树形关联。</desc>',
        '  <defs>',
        '    <marker id="arrow" viewBox="0 0 8 8" refX="6.5" refY="4" markerWidth="3.2" markerHeight="3.2" orient="auto-start-reverse">',
        '      <path d="M 0 0 L 8 4 L 0 8 z" fill="#b8c0ce" fill-opacity="0.62" />',
        '    </marker>',
        '    <filter id="softShadow" x="-8%" y="-10%" width="116%" height="125%">',
        '      <feDropShadow dx="0" dy="0.8" stdDeviation="0.8" flood-color="#18233a" flood-opacity="0.12" />',
        '    </filter>',
        '  </defs>',
        '  <rect class="bg" x="0" y="0" width="210" height="297" fill="#faf9f5" stroke="none" />',
        '  <g opacity="0.42">',
        '    <path class="hair" d="M18 24H192M18 64H192M18 104H192M18 144H192M18 184H192M18 224H192M18 264H192" stroke="#e9e5dc" stroke-width=".28" fill="none" />',
        '    <path class="hair" d="M30 18V279M70 18V279M110 18V279M150 18V279M190 18V279" stroke="#e9e5dc" stroke-width=".28" fill="none" />',
        '  </g>',
    ]

    branch_children = {
        "basic": ["basic-a", "basic-b", "basic-note"],
        "common": ["common-a", "common-b", "common-c", "common-note"],
        "distance": ["distance-a", "distance-b", "distance-c", "distance-note"],
        "count": ["count-a", "count-b", "count-c", "count-d", "count-note"],
    }

    # Draw all connector lines before cards/text. Opaque card fills then hide
    # any connector segment that passes below a card, so no line can obscure text.
    lines.append(edge(root, core, strong=True))
    for branch in branches:
        lines.append(edge(core, branch))
    for branch in branches:
        for child_key in branch_children[branch.key]:
            lines.append(edge(branch, by_key[child_key]))

    # Cross-links: light dashed method relationships, also under all cards/text.
    lines.append(edge(by_key["common-c"], by_key["count-note"], dashed=True))
    lines.append(edge(by_key["distance-c"], by_key["count-note"], dashed=True))
    lines.append(edge(core, method))

    lines.extend(box_group(root, shadow=True))
    lines.extend(box_group(core, shadow=True))
    for branch in branches:
        lines.extend(box_group(branch, shadow=True))

    for leaf in leaves:
        lines.extend(box_group(leaf))

    lines.extend(box_group(method))

    # Edge labels and method text are deliberately drawn after all lines.
    lines.extend([
        label(31, 75, "由切点设参"),
        label(80, 75, "比较两切线"),
        label(130, 75, "转不等式"),
        label(176, 75, "计数分区"),
    ])
    lines.extend([
        label(123, 211, "方程解数"),
        label(146, 220, "图像分区"),
    ])

    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"bytes={OUT.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
