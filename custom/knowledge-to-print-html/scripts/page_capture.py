from __future__ import annotations

import base64
import struct
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

A4_WIDTH_MM = 210

A4_HEIGHT_MM = 297

A4_ASPECT_RATIO = A4_WIDTH_MM / A4_HEIGHT_MM

RECT_EVAL_JS = r"""
sheet => {
  const rect = sheet.getBoundingClientRect();
  return {
    width: Math.round(rect.width * 100) / 100,
    height: Math.round(rect.height * 100) / 100,
    hidden: sheet.hidden,
  };
}
"""

VISIBLE_SHEET_COUNT_EVAL_JS = r"""
elements => elements.filter((sheet) => !sheet.hidden).length
"""

ISOLATE_PAGE_EVAL_JS = r"""
pageNumber => {
  const sheets = Array.from(document.querySelectorAll(".sheet"));
  if (sheets.length === 0) return { visibleSheetCount: 0, targetFound: false };

  const pageKey = String(pageNumber);
  const sheetByDataPage = sheets.find((sheet) => sheet.dataset.page === pageKey);
  const targetSheet = sheetByDataPage || sheets[pageNumber - 1] || sheets[0];

  for (const sheet of sheets) {
    const shouldShow = sheet === targetSheet;
    sheet.hidden = !shouldShow;
    sheet.toggleAttribute("aria-hidden", !shouldShow);
    sheet.dataset.printReviewVisible = shouldShow ? "true" : "false";
  }

  return {
    visibleSheetCount: sheets.filter((sheet) => !sheet.hidden).length,
    targetFound: Boolean(targetSheet),
    targetPage: targetSheet.dataset.page || String(sheets.indexOf(targetSheet) + 1),
  };
}
"""

def with_query_params(url: str, **params: Any) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    for key, value in params.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)

    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )

def default_output_dir(html_path: Path) -> Path:
    return html_path.parent / "screens" / "py-latest"

def isolate_page_for_capture(page: Any, page_number: int) -> dict[str, Any]:
    isolation = page.evaluate(ISOLATE_PAGE_EVAL_JS, page_number)
    if isolation["visibleSheetCount"] != 1:
        raise RuntimeError(
            f"Unable to isolate page {page_number}; "
            f"visible sheets: {isolation['visibleSheetCount']}."
        )
    return isolation

def page_sheet_locator(page: Any, page_number: int) -> Any:
    data_page_locator = page.locator(f'.sheet[data-page="{page_number}"]')
    if data_page_locator.count() > 0:
        return data_page_locator.first
    return page.locator(".sheet").nth(page_number - 1)

def read_png_dimensions(path: Path) -> tuple[int, int]:
    png_bytes = path.read_bytes()
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Expected PNG screenshot artifact: {path}")
    return struct.unpack(">II", png_bytes[16:24])

def path_to_data_url(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"

def build_a4_clip(box: dict[str, float]) -> dict[str, float]:
    width = float(box["width"])
    return {
        "x": float(box["x"]),
        "y": float(box["y"]),
        "width": width,
        "height": width / A4_ASPECT_RATIO,
    }

def capture_page_artifacts(
    context: Any,
    base_url: str,
    sheet_count: int,
    output_dir: Path,
    prefix: str,
    settle_ms: int,
) -> list[dict[str, Any]]:
    page_artifacts: list[dict[str, Any]] = []

    for page_number in range(1, sheet_count + 1):
        page = context.new_page()
        try:
            page.goto(
                with_query_params(base_url, print=1, page=page_number),
                wait_until="load",
            )
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(settle_ms)

            isolation = isolate_page_for_capture(page, page_number)
            screenshot_path = output_dir / f"{prefix}-print-page-{page_number}.png"

            target_locator = page_sheet_locator(page, page_number)
            target_locator.scroll_into_view_if_needed()
            bounding_box = target_locator.bounding_box()
            if not bounding_box:
                raise RuntimeError(f"Unable to measure page {page_number} for A4 clipping.")
            page.screenshot(
                path=str(screenshot_path),
                clip=build_a4_clip(bounding_box),
            )

            rect = target_locator.evaluate(RECT_EVAL_JS)
            visible_sheet_count = page.locator(".sheet").evaluate_all(
                VISIBLE_SHEET_COUNT_EVAL_JS
            )
            screenshot_width_px, screenshot_height_px = read_png_dimensions(
                screenshot_path
            )
            screenshot_aspect_ratio = screenshot_width_px / screenshot_height_px
            screenshot_uses_a4_aspect = abs(screenshot_aspect_ratio - A4_ASPECT_RATIO) <= 0.02

            page_artifacts.append(
                {
                    "page": page_number,
                    "path": str(screenshot_path),
                    "width": rect["width"],
                    "height": rect["height"],
                    "hidden": rect["hidden"],
                    "visibleSheetCount": visible_sheet_count,
                    "isolatedTargetPage": isolation["targetPage"],
                    "screenshotWidthPx": screenshot_width_px,
                    "screenshotHeightPx": screenshot_height_px,
                    "screenshotAspectRatio": round(screenshot_aspect_ratio, 4),
                    "usesA4Aspect": screenshot_uses_a4_aspect,
                }
            )
        finally:
            page.close()

    return page_artifacts
