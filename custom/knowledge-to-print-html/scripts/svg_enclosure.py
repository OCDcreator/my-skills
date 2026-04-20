from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SVG_FRAME_MIN_WIDTH = 140.0

SVG_FRAME_MIN_HEIGHT = 80.0

SVG_FRAME_BACKGROUND_AREA_RATIO = 0.75

SVG_FRAME_OVERFLOW_TOLERANCE = 4.0

SVG_FRAME_VERTICAL_SLACK = 120.0

SVG_TEXT_BOX_MAX_WIDTH = 420.0

SVG_TEXT_BOX_MAX_HEIGHT = 220.0

SVG_STRUCTURED_FRAME_MAX_WIDTH = 600.0

SVG_STRUCTURED_FRAME_MAX_HEIGHT = 400.0

SVG_TEXT_BOX_MIN_SIDE_PADDING = 12.0

SVG_TEXT_BOX_MIN_TOP_PADDING = 12.0

SVG_TEXT_BOX_MIN_BOTTOM_PADDING = 10.0

SVG_TEXT_BOX_MAX_HORIZONTAL_IMBALANCE = 14.0

SVG_TEXT_BOX_MAX_VERTICAL_IMBALANCE = 16.0

def parse_svg_number(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else default

def parse_svg_numbers(value: str | None) -> list[float]:
    if not value:
        return []
    return [float(item) for item in re.findall(r"-?\d+(?:\.\d+)?", value)]

def parse_translate_transform(transform: str | None) -> tuple[float, float]:
    if not transform:
        return (0.0, 0.0)

    translate_x = 0.0
    translate_y = 0.0
    for func_name, args in re.findall(r"([A-Za-z]+)\(([^)]*)\)", transform):
        if func_name != "translate":
            continue
        numbers = parse_svg_numbers(args)
        if numbers:
            translate_x += numbers[0]
            translate_y += numbers[1] if len(numbers) > 1 else 0.0
    return (translate_x, translate_y)

def parse_svg_viewbox(root: ET.Element) -> tuple[float, float]:
    view_box = root.attrib.get("viewBox")
    numbers = parse_svg_numbers(view_box)
    if len(numbers) == 4 and numbers[2] > 0 and numbers[3] > 0:
        return (numbers[2], numbers[3])

    width = parse_svg_number(root.attrib.get("width"), default=0.0)
    height = parse_svg_number(root.attrib.get("height"), default=0.0)
    return (width, height)

def parse_svg_class_font_sizes(root: ET.Element) -> dict[str, float]:
    class_font_sizes: dict[str, float] = {}

    for style_node in root.iter():
        if style_node.tag.split("}")[-1] != "style":
            continue
        style_text = style_node.text or ""
        for selector_block, body in re.findall(r"([^{}]+)\{([^}]*)\}", style_text):
            font_match = re.search(r"font-size\s*:\s*([0-9.]+)px", body)
            if not font_match:
                font_match = re.search(r"font\s*:[^;]*?([0-9.]+)px", body)
            if not font_match:
                continue
            font_size = float(font_match.group(1))
            for class_name in re.findall(r"\.([A-Za-z0-9_-]+)", selector_block):
                class_font_sizes[class_name] = font_size

    return class_font_sizes

def resolve_svg_font_size(
    element: ET.Element,
    class_font_sizes: dict[str, float],
    *,
    fallback: float = 16.0,
) -> float:
    if "font-size" in element.attrib:
        return parse_svg_number(element.attrib.get("font-size"), default=fallback)

    style_attr = element.attrib.get("style", "")
    style_match = re.search(r"font-size\s*:\s*([0-9.]+)px", style_attr)
    if style_match:
        return float(style_match.group(1))

    font_match = re.search(r"font\s*:\s*[^;]*?([0-9.]+)px", style_attr)
    if font_match:
        return float(font_match.group(1))

    class_names = element.attrib.get("class", "").split()
    for class_name in class_names:
        if class_name in class_font_sizes:
            return class_font_sizes[class_name]

    return fallback

def estimate_svg_text_width(text: str, font_size: float) -> float:
    units = 0.0
    for character in text:
        if character.isspace():
            units += 0.35
        elif ord(character) > 127:
            units += 1.0
        elif character.isupper():
            units += 0.68
        else:
            units += 0.56
    return max(font_size * 0.8, units * font_size)

def compute_svg_element_bounds(
    element: ET.Element,
    *,
    offset: tuple[float, float],
    class_font_sizes: dict[str, float],
) -> dict[str, Any] | None:
    tag = element.tag.split("}")[-1]
    offset_x, offset_y = offset

    if tag == "rect":
        width = parse_svg_number(element.attrib.get("width"), default=0.0)
        height = parse_svg_number(element.attrib.get("height"), default=0.0)
        if width <= 0 or height <= 0:
            return None
        left = parse_svg_number(element.attrib.get("x"), default=0.0) + offset_x
        top = parse_svg_number(element.attrib.get("y"), default=0.0) + offset_y
        return {
            "tag": "rect",
            "left": left,
            "top": top,
            "right": left + width,
            "bottom": top + height,
            "width": width,
            "height": height,
            "text": None,
            "fontSize": None,
        }

    if tag != "text":
        return None

    text_content = re.sub(r"\s+", " ", "".join(element.itertext())).strip()
    if not text_content:
        return None

    font_size = resolve_svg_font_size(element, class_font_sizes)
    x_values = parse_svg_numbers(element.attrib.get("x"))
    y_values = parse_svg_numbers(element.attrib.get("y"))
    x_position = (x_values[0] if x_values else 0.0) + offset_x
    y_position = (y_values[0] if y_values else 0.0) + offset_y
    width = estimate_svg_text_width(text_content, font_size)
    height = font_size * 1.2
    anchor = element.attrib.get("text-anchor", "start")

    if anchor == "middle":
        left = x_position - (width / 2)
    elif anchor == "end":
        left = x_position - width
    else:
        left = x_position

    top = y_position - (font_size * 0.85)
    return {
        "tag": "text",
        "left": left,
        "top": top,
        "right": left + width,
        "bottom": top + height,
        "width": width,
        "height": height,
        "text": text_content,
        "fontSize": font_size,
    }

def collect_svg_drawables(
    node: ET.Element,
    *,
    parent_key: tuple[int, ...],
    offset: tuple[float, float],
    class_font_sizes: dict[str, float],
    elements: list[dict[str, Any]],
    order_counter: list[int],
) -> None:
    translate_x, translate_y = parse_translate_transform(node.attrib.get("transform"))
    current_offset = (offset[0] + translate_x, offset[1] + translate_y)

    for child_index, child in enumerate(list(node)):
        bounds = compute_svg_element_bounds(
            child,
            offset=current_offset,
            class_font_sizes=class_font_sizes,
        )
        order = order_counter[0]
        order_counter[0] += 1
        if bounds:
            class_names = child.attrib.get("class", "").split()
            elements.append(
                {
                    "tag": bounds["tag"],
                    "left": bounds["left"],
                    "top": bounds["top"],
                    "right": bounds["right"],
                    "bottom": bounds["bottom"],
                    "width": bounds["width"],
                    "height": bounds["height"],
                    "text": bounds["text"],
                    "fontSize": bounds["fontSize"],
                    "parentKey": parent_key,
                    "order": order,
                    "classes": class_names,
                }
            )

        collect_svg_drawables(
            child,
            parent_key=parent_key + (child_index,),
            offset=current_offset,
            class_font_sizes=class_font_sizes,
            elements=elements,
            order_counter=order_counter,
        )

def horizontal_overlap_ratio(
    left_a: float,
    right_a: float,
    left_b: float,
    right_b: float,
) -> float:
    overlap = max(0.0, min(right_a, right_b) - max(left_a, left_b))
    smallest_width = max(1.0, min(right_a - left_a, right_b - left_b))
    return overlap / smallest_width

def inspect_svg_visual_enclosure(svg_path: Path) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    except (ET.ParseError, OSError, UnicodeDecodeError):
        return []

    svg_width, svg_height = parse_svg_viewbox(root)
    svg_area = max(svg_width * svg_height, 1.0)
    class_font_sizes = parse_svg_class_font_sizes(root)
    elements: list[dict[str, Any]] = []
    collect_svg_drawables(
        root,
        parent_key=(),
        offset=(0.0, 0.0),
        class_font_sizes=class_font_sizes,
        elements=elements,
        order_counter=[0],
    )

    issues: list[dict[str, Any]] = []
    candidate_frames = [
        element
        for element in elements
        if element["tag"] == "rect"
        and element["width"] >= SVG_FRAME_MIN_WIDTH
        and element["height"] >= SVG_FRAME_MIN_HEIGHT
        and (element["width"] * element["height"]) < (svg_area * SVG_FRAME_BACKGROUND_AREA_RATIO)
    ]

    for frame in candidate_frames:
        overflowing_items: list[dict[str, Any]] = []
        padding_issue: dict[str, Any] | None = None
        is_small_text_box = (
            frame["width"] <= SVG_TEXT_BOX_MAX_WIDTH
            and frame["height"] <= SVG_TEXT_BOX_MAX_HEIGHT
        )
        is_structured_content_frame = (
            frame["width"] <= SVG_STRUCTURED_FRAME_MAX_WIDTH
            and frame["height"] <= SVG_STRUCTURED_FRAME_MAX_HEIGHT
        )
        vertical_limit = frame["bottom"] + min(
            SVG_FRAME_VERTICAL_SLACK,
            max(36.0, frame["height"] * 0.45),
        )
        for element in elements:
            if element["parentKey"] != frame["parentKey"]:
                continue
            if element["order"] <= frame["order"]:
                continue
            if element["tag"] not in {"rect", "text"}:
                continue

            center_x = (element["left"] + element["right"]) / 2
            center_y = (element["top"] + element["bottom"]) / 2
            if element["tag"] == "text":
                overlaps_horizontally = (
                    (frame["left"] - 12.0) <= element["left"] <= (frame["right"] - 12.0)
                    or (frame["left"] + 8.0) <= center_x <= (frame["right"] - 8.0)
                )
            else:
                overlaps_horizontally = (
                    horizontal_overlap_ratio(
                        frame["left"],
                        frame["right"],
                        element["left"],
                        element["right"],
                    ) >= 0.6
                    or (frame["left"] - 6.0) <= center_x <= (frame["right"] + 6.0)
                )
            if not overlaps_horizontally:
                continue
            if center_y < (frame["top"] - 12.0) or center_y > vertical_limit:
                continue

            overflow_left = max(0.0, frame["left"] - element["left"])
            overflow_right = max(0.0, element["right"] - frame["right"])
            overflow_top = max(0.0, frame["top"] - element["top"])
            overflow_bottom = max(0.0, element["bottom"] - frame["bottom"])
            max_overflow = max(
                overflow_left,
                overflow_right,
                overflow_top,
                overflow_bottom,
            )
            if max_overflow <= SVG_FRAME_OVERFLOW_TOLERANCE:
                continue
            if element["tag"] == "text":
                font_size = element.get("fontSize") or 16.0
                if max_overflow <= font_size * 0.35:
                    continue

            overflowing_items.append(
                {
                    "tag": element["tag"],
                    "text": element.get("text"),
                    "left": round(element["left"], 2),
                    "top": round(element["top"], 2),
                    "right": round(element["right"], 2),
                    "bottom": round(element["bottom"], 2),
                    "overflowLeft": round(overflow_left, 2),
                    "overflowRight": round(overflow_right, 2),
                    "overflowTop": round(overflow_top, 2),
                    "overflowBottom": round(overflow_bottom, 2),
                }
            )

        if is_small_text_box or is_structured_content_frame:
            content_text_items = []
            content_rect_items = []
            for element in elements:
                if element["parentKey"] != frame["parentKey"]:
                    continue
                if element["order"] <= frame["order"] or element["tag"] not in {"rect", "text"}:
                    continue
                center_x = (element["left"] + element["right"]) / 2
                center_y = (element["top"] + element["bottom"]) / 2
                if (
                    (frame["left"] + 4.0) <= center_x <= (frame["right"] - 4.0)
                    and (frame["top"] + 2.0) <= center_y <= (frame["bottom"] + 8.0)
                ):
                    if element["tag"] == "text":
                        content_text_items.append(element)
                    elif (
                        0.0 < element["width"] < frame["width"]
                        and 0.0 < element["height"] < frame["height"]
                    ):
                        content_rect_items.append(element)

            content_items = content_text_items
            if is_structured_content_frame and content_rect_items:
                content_items = [*content_text_items, *content_rect_items]

            if content_text_items and content_items:
                content_left = min(item["left"] for item in content_items)
                content_right = max(item["right"] for item in content_items)
                content_top = min(item["top"] for item in content_items)
                content_bottom = max(item["bottom"] for item in content_items)
                padding = {
                    "left": round(frame["left"] - content_left if content_left < frame["left"] else content_left - frame["left"], 2),
                    "right": round(frame["right"] - content_right, 2),
                    "top": round(content_top - frame["top"], 2),
                    "bottom": round(frame["bottom"] - content_bottom, 2),
                }
                compact_multiline_box = is_small_text_box and frame["width"] <= 260.0 and len(content_text_items) >= 4
                structured_content_frame = is_structured_content_frame and bool(content_rect_items)
                horizontal_imbalance = abs(padding["left"] - padding["right"])
                vertical_imbalance = abs(padding["top"] - padding["bottom"])
                fails_padding = (
                    padding["left"] < SVG_TEXT_BOX_MIN_SIDE_PADDING
                    or padding["right"] < SVG_TEXT_BOX_MIN_SIDE_PADDING
                    or padding["top"] < SVG_TEXT_BOX_MIN_TOP_PADDING
                    or padding["bottom"] < SVG_TEXT_BOX_MIN_BOTTOM_PADDING
                    or (
                        compact_multiline_box
                        and horizontal_imbalance > SVG_TEXT_BOX_MAX_HORIZONTAL_IMBALANCE
                    )
                    or (
                        (compact_multiline_box or structured_content_frame)
                        and vertical_imbalance > SVG_TEXT_BOX_MAX_VERTICAL_IMBALANCE
                    )
                )
                if fails_padding:
                    padding_issue = {
                        "contentBounds": {
                            "left": round(content_left, 2),
                            "right": round(content_right, 2),
                            "top": round(content_top, 2),
                            "bottom": round(content_bottom, 2),
                        },
                        "padding": padding,
                        "horizontalImbalance": round(horizontal_imbalance, 2),
                        "verticalImbalance": round(vertical_imbalance, 2),
                        "compactMultilineBox": compact_multiline_box,
                        "structuredContentFrame": structured_content_frame,
                    }

        rect_overflows = [item for item in overflowing_items if item["tag"] == "rect"]
        text_overflows = [item for item in overflowing_items if item["tag"] == "text"]
        if not rect_overflows and not text_overflows:
            if padding_issue is None:
                continue
        if not is_small_text_box and padding_issue is None and not rect_overflows and len(text_overflows) < 2:
            continue

        issues.append(
            {
                "svgPath": str(svg_path),
                "kind": (
                    "small_text_box_overflow"
                    if is_small_text_box and text_overflows
                    else "small_text_box_padding_failure"
                    if is_small_text_box and padding_issue is not None
                    else "svg_inner_padding_failure"
                    if padding_issue is not None
                    else "group_enclosure_failure"
                ),
                "frame": {
                    "left": round(frame["left"], 2),
                    "top": round(frame["top"], 2),
                    "right": round(frame["right"], 2),
                    "bottom": round(frame["bottom"], 2),
                    "width": round(frame["width"], 2),
                    "height": round(frame["height"], 2),
                },
                "overflowItems": overflowing_items,
                "paddingIssue": padding_issue,
            }
        )

    return issues

def resolve_local_image_path(html_path: Path, image_src: str | None) -> Path | None:
    if not image_src:
        return None
    if image_src.startswith(("http://", "https://", "data:")):
        return None

    normalized_src = image_src.split("?", 1)[0].split("#", 1)[0]
    return (html_path.parent / normalized_src).resolve()

def attach_svg_visual_enclosure_issues(
    *,
    html_path: Path,
    analysis: dict[str, Any],
) -> None:
    sheet_index = {
        str(sheet.get("page")): sheet
        for sheet in analysis["sheets"]
    }
    for sheet in analysis["sheets"]:
        sheet["svgVisualEnclosure"] = {"count": 0, "items": []}

    all_issues: list[dict[str, Any]] = []
    for image in analysis["images"]:
        image_path = resolve_local_image_path(html_path, image.get("src"))
        if not image_path or image_path.suffix.lower() != ".svg" or not image_path.exists():
            continue

        svg_issues = inspect_svg_visual_enclosure(image_path)
        for issue in svg_issues:
            item = {
                "src": image.get("src"),
                "alt": image.get("alt"),
                "page": image.get("page"),
                "svgPath": issue["svgPath"],
                "frame": issue["frame"],
                "overflowItems": issue["overflowItems"],
            }
            all_issues.append(item)
            page_key = str(image.get("page"))
            if page_key in sheet_index:
                sheet_index[page_key]["svgVisualEnclosure"]["items"].append(item)

    for sheet in analysis["sheets"]:
        sheet["svgVisualEnclosure"]["count"] = len(sheet["svgVisualEnclosure"]["items"])

    analysis["svgVisualEnclosureIssues"] = {
        "count": len(all_issues),
        "items": all_issues,
    }
