from __future__ import annotations

import argparse
import base64
import glob
import importlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
A4_ASPECT_RATIO = A4_WIDTH_MM / A4_HEIGHT_MM
DEFAULT_PARITY_DIFF_THRESHOLD = 0.035


IMAGE_EVAL_JS = r"""
elements => elements.map((image) => ({
  src: image.getAttribute("src"),
  complete: image.complete,
  naturalWidth: image.naturalWidth,
  naturalHeight: image.naturalHeight,
}))
"""

SHEET_EVAL_JS = r"""
elements => {
  const watchedSelectors = [
    "figure",
    ".callout",
    ".case-study",
    ".note-box",
    ".mistakes",
    ".print-note",
    "pre",
    "table",
    ".card",
    ".mini",
    ".ref-item",
    ".summary-points > div",
    ".hero-panel",
    ".tags",
    ".table-like",
  ].join(",");

    return elements.map((sheet) => {
      const rect = sheet.getBoundingClientRect();
      const expectedA4Height = rect.width / (210 / 297);
      const issues = [];
    const directChildren = Array.from(sheet.children).filter((node) => {
      return !node.classList.contains("page-no") && !node.hidden;
    });

    let contentTop = rect.bottom;
    let contentBottom = rect.top;
    let contentLeft = rect.right;
    let contentRight = rect.left;

    for (const node of sheet.querySelectorAll(watchedSelectors)) {
      const box = node.getBoundingClientRect();
      const rightOverflow = Math.round((box.right - rect.right) * 100) / 100;
      const bottomOverflow = Math.round((box.bottom - rect.bottom) * 100) / 100;

      if (rightOverflow > 1) {
        issues.push({
          kind: "right-overflow",
          selector: node.className || node.tagName.toLowerCase(),
          amount: rightOverflow,
        });
      }

      if (bottomOverflow > 1) {
        issues.push({
          kind: "bottom-overflow",
          selector: node.className || node.tagName.toLowerCase(),
          amount: bottomOverflow,
        });
      }
    }

    for (const node of directChildren) {
      const box = node.getBoundingClientRect();
      contentTop = Math.min(contentTop, box.top);
      contentBottom = Math.max(contentBottom, box.bottom);
      contentLeft = Math.min(contentLeft, box.left);
      contentRight = Math.max(contentRight, box.right);
    }

    const hasVisibleContent = directChildren.length > 0;
    const contentBounds = hasVisibleContent ? {
      top: Math.round((contentTop - rect.top) * 100) / 100,
      bottom: Math.round((contentBottom - rect.top) * 100) / 100,
      left: Math.round((contentLeft - rect.left) * 100) / 100,
      right: Math.round((contentRight - rect.left) * 100) / 100,
      width: Math.round((contentRight - contentLeft) * 100) / 100,
      height: Math.round((contentBottom - contentTop) * 100) / 100,
    } : null;

    const figures = Array.from(sheet.querySelectorAll("figure, .figure, img")).map((node) => {
      const box = node.getBoundingClientRect();
      return {
        selector: node.className || node.tagName.toLowerCase(),
        width: Math.round(box.width * 100) / 100,
        height: Math.round(box.height * 100) / 100,
        widthRatio: Math.round((box.width / rect.width) * 1000) / 1000,
        heightRatio: Math.round((box.height / rect.height) * 1000) / 1000,
        areaRatio: Math.round(((box.width * box.height) / (rect.width * rect.height)) * 1000) / 1000,
      };
    });

    const largestFigure = figures.reduce((largest, current) => {
      if (!largest || current.areaRatio > largest.areaRatio) return current;
      return largest;
    }, null);

      return {
      page: sheet.dataset.page || null,
      client: {
        width: sheet.clientWidth,
        height: sheet.clientHeight,
      },
      scroll: {
        width: sheet.scrollWidth,
        height: sheet.scrollHeight,
      },
      overflow: {
        x: Math.max(0, sheet.scrollWidth - sheet.clientWidth),
        y: Math.max(0, sheet.scrollHeight - sheet.clientHeight),
      },
      rect: {
        width: Math.round(rect.width * 100) / 100,
        height: Math.round(rect.height * 100) / 100,
      },
      expectedA4Height: Math.round(expectedA4Height * 100) / 100,
      usesA4Aspect: Math.abs(rect.height - expectedA4Height) <= 2,
      contentBounds,
      density: hasVisibleContent ? {
        contentHeightRatio: Math.round(((contentBottom - contentTop) / rect.height) * 1000) / 1000,
        contentWidthRatio: Math.round(((contentRight - contentLeft) / rect.width) * 1000) / 1000,
        bottomGap: Math.round((rect.bottom - contentBottom) * 100) / 100,
        bottomGapRatio: Math.round(((rect.bottom - contentBottom) / rect.height) * 1000) / 1000,
        topGap: Math.round((contentTop - rect.top) * 100) / 100,
        topGapRatio: Math.round(((contentTop - rect.top) / rect.height) * 1000) / 1000,
      } : null,
      figures: {
        count: figures.length,
        largest: largestFigure,
        items: figures,
      },
      issueCount: issues.length,
      issues,
    };
  });
}
"""

STYLE_RULES_EVAL_JS = r"""
() => {
  const styleText = Array.from(document.querySelectorAll("style"))
    .map((style) => style.textContent || "")
    .join("\n");

  return {
    a4Page: /@page\s*\{[^}]*size\s*:\s*A4/i.test(styleText),
    breakAvoid: /break-inside\s*:\s*avoid/i.test(styleText),
    printMedia: /@media\s+print/i.test(styleText),
    printColorAdjust: /print-color-adjust\s*:\s*exact/i.test(styleText),
  };
}
"""

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

IMAGE_DIFF_EVAL_JS = r"""
async payload => {
  const { leftDataUrl, rightDataUrl, sampleSize } = payload;
  const loadImage = src => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Failed to decode comparison image."));
    image.src = src;
  });

  const [leftImage, rightImage] = await Promise.all([
    loadImage(leftDataUrl),
    loadImage(rightDataUrl),
  ]);

  const canvas = document.createElement("canvas");
  canvas.width = sampleSize;
  canvas.height = sampleSize;
  const context = canvas.getContext("2d", { willReadFrequently: true });

  const sampleImage = image => {
    context.clearRect(0, 0, sampleSize, sampleSize);
    context.drawImage(image, 0, 0, sampleSize, sampleSize);
    return context.getImageData(0, 0, sampleSize, sampleSize).data;
  };

  const leftPixels = sampleImage(leftImage);
  const rightPixels = sampleImage(rightImage);
  let totalDifference = 0;

  for (let index = 0; index < leftPixels.length; index += 4) {
    const leftGray = (
      leftPixels[index] * 0.299 +
      leftPixels[index + 1] * 0.587 +
      leftPixels[index + 2] * 0.114
    ) / 255;
    const rightGray = (
      rightPixels[index] * 0.299 +
      rightPixels[index + 1] * 0.587 +
      rightPixels[index + 2] * 0.114
    ) / 255;
    totalDifference += Math.abs(leftGray - rightGray);
  }

  return Math.round((totalDifference / (sampleSize * sampleSize)) * 10000) / 10000;
}
"""


def run_bootstrap_command(command: list[str]) -> None:
    subprocess.run(command, check=True)


def ensure_python_package(
    import_name: str,
    *,
    pip_name: str,
    auto_install: bool,
) -> Any:
    try:
        return importlib.import_module(import_name)
    except ImportError as exc:
        if not auto_install:
            raise RuntimeError(
                f"Missing Python dependency `{pip_name}`. "
                f"Install it with: {' '.join([sys.executable, '-m', 'pip', 'install', pip_name])}"
            ) from exc

    run_bootstrap_command([sys.executable, "-m", "pip", "install", pip_name])

    try:
        return importlib.import_module(import_name)
    except ImportError as exc:
        raise RuntimeError(
            f"Automatic installation finished, but `{pip_name}` still could not be imported."
        ) from exc


def try_install_system_browser() -> str | None:
    commands: list[list[str]] = []
    if os.name == "nt" and shutil.which("winget"):
        commands.extend(
            [
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "Microsoft.Edge",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "Google.Chrome",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
            ]
        )
    elif sys.platform == "darwin" and shutil.which("brew"):
        commands.extend(
            [
                ["brew", "install", "--cask", "microsoft-edge"],
                ["brew", "install", "--cask", "google-chrome"],
            ]
        )
    elif shutil.which("apt-get"):
        commands.extend(
            [
                ["apt-get", "install", "-y", "chromium-browser"],
                ["apt-get", "install", "-y", "chromium"],
            ]
        )

    for command in commands:
        try:
            run_bootstrap_command(command)
        except Exception:
            continue

        browser_path = resolve_browser_path(None)
        if browser_path:
            return browser_path

    return None


def resolve_qpdf_path() -> str | None:
    candidates = [
        shutil.which("qpdf"),
        r"C:\Program Files\qpdf\bin\qpdf.exe",
        r"C:\Program Files (x86)\qpdf\bin\qpdf.exe",
        "/opt/homebrew/bin/qpdf",
        "/usr/local/bin/qpdf",
        "/usr/bin/qpdf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    glob_patterns = [
        r"C:\Program Files\qpdf*\bin\qpdf.exe",
        r"C:\Program Files (x86)\qpdf*\bin\qpdf.exe",
        str(Path.home() / "AppData/Local/Microsoft/WinGet/Packages/QPDF.QPDF_*" / "*" / "qpdf.exe"),
    ]
    for pattern in glob_patterns:
        matches = sorted(glob.glob(pattern))
        for match in matches:
            if Path(match).exists():
                return str(Path(match))
    return None


def try_install_qpdf() -> str | None:
    commands: list[list[str]] = []
    if os.name == "nt" and shutil.which("winget"):
        commands.append(
            [
                "winget",
                "install",
                "-e",
                "--id",
                "QPDF.QPDF",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        )
    elif sys.platform == "darwin" and shutil.which("brew"):
        commands.append(["brew", "install", "qpdf"])
    elif shutil.which("apt-get"):
        commands.append(["apt-get", "install", "-y", "qpdf"])

    for command in commands:
        try:
            run_bootstrap_command(command)
        except Exception:
            continue

        qpdf_path = resolve_qpdf_path()
        if qpdf_path:
            return qpdf_path

    return None


def inspect_pdf_fast_view_features(path: Path) -> dict[str, bool]:
    data = path.read_bytes()
    head = data[:2048]
    return {
        "linearized": b"/Linearized" in head,
        "objectStreams": b"/ObjStm" in data,
        "xrefStream": b"/XRef" in data,
    }


def optimize_pdf_for_fast_view(
    raw_pdf_path: Path,
    final_pdf_path: Path,
    *,
    auto_install: bool,
) -> dict[str, Any]:
    qpdf_path = resolve_qpdf_path()
    if not qpdf_path and auto_install:
        qpdf_path = try_install_qpdf()

    raw_bytes = raw_pdf_path.stat().st_size
    if not qpdf_path:
        if raw_pdf_path != final_pdf_path:
            shutil.copyfile(raw_pdf_path, final_pdf_path)
        features = inspect_pdf_fast_view_features(final_pdf_path)
        return {
            "tool": None,
            "linearized": features["linearized"],
            "objectStreams": features["objectStreams"],
            "xrefStream": features["xrefStream"],
            "rawBytes": raw_bytes,
            "optimizedBytes": final_pdf_path.stat().st_size,
            "optimized": False,
            "reason": "qpdf was not available and could not be installed automatically.",
        }

    command = [
        qpdf_path,
        "--linearize",
        "--object-streams=generate",
        str(raw_pdf_path),
        str(final_pdf_path),
    ]
    run_bootstrap_command(command)
    features = inspect_pdf_fast_view_features(final_pdf_path)
    return {
        "tool": "qpdf",
        "toolPath": qpdf_path,
        "linearized": features["linearized"],
        "objectStreams": features["objectStreams"],
        "xrefStream": features["xrefStream"],
        "rawBytes": raw_bytes,
        "optimizedBytes": final_pdf_path.stat().st_size,
        "optimized": features["linearized"],
        "reason": None if features["linearized"] else "qpdf ran but the output is not linearized.",
    }


def build_fast_view_pdf(
    html_page_artifacts: list[dict[str, Any]],
    output_dir: Path,
    prefix: str,
    *,
    auto_install: bool,
) -> dict[str, Any]:
    fitz = load_pymupdf(auto_install)
    raw_pdf_path = output_dir / f"{prefix}-fastview-raw.pdf"
    final_pdf_path = output_dir / f"{prefix}-fastview.pdf"
    document = fitz.open()

    try:
        for artifact in html_page_artifacts:
            image_path = Path(artifact["path"])
            page = document.new_page(width=594.96, height=841.92)
            page.insert_image(page.rect, filename=str(image_path), keep_proportion=False)
        document.save(raw_pdf_path, garbage=4, deflate=True, clean=True)
    finally:
        document.close()

    optimization = optimize_pdf_for_fast_view(
        raw_pdf_path,
        final_pdf_path,
        auto_install=auto_install,
    )
    try:
        raw_pdf_path.unlink()
    except OSError:
        pass

    page_count, media_boxes = inspect_pdf_document(
        final_pdf_path,
        auto_install=auto_install,
    )
    return {
        "path": str(final_pdf_path),
        "bytes": final_pdf_path.stat().st_size,
        "pageCount": page_count,
        "mediaBoxes": media_boxes,
        "source": "html-page-screenshots",
        "optimization": optimization,
    }


def ensure_playwright_runtime(auto_install: bool) -> None:
    if not auto_install:
        return
    run_bootstrap_command([sys.executable, "-m", "playwright", "install", "chromium"])


def load_playwright(auto_install: bool) -> Any:
    module = ensure_python_package(
        "playwright.sync_api",
        pip_name="playwright",
        auto_install=auto_install,
    )
    return module.sync_playwright


def load_pymupdf(auto_install: bool) -> Any:
    return ensure_python_package(
        "fitz",
        pip_name="pymupdf",
        auto_install=auto_install,
    )

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a local print-first handout.html and export screenshots, PDF, and a JSON report."
    )
    parser.add_argument("--html", required=True, help="Path to the local handout.html file.")
    parser.add_argument(
        "--out-dir",
        help="Directory for screenshots, PDF, and report. Defaults to <html-dir>/screens/py-latest.",
    )
    parser.add_argument(
        "--browser-path",
        help="Optional Chrome/Chromium executable path. Falls back to common system paths or Playwright's bundled browser.",
    )
    parser.add_argument(
        "--prefix",
        help="Artifact filename prefix. Defaults to the HTML filename stem.",
    )
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=300,
        help="Extra wait after page load before capture. Default: 300.",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1400,
        help="Viewport width for screen captures. Default: 1400.",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1800,
        help="Viewport height for screen captures. Default: 1800.",
    )
    parser.add_argument(
        "--device-scale-factor",
        type=float,
        default=1.5,
        help="Device scale factor for captures. Default: 1.5.",
    )
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="Disable automatic dependency installation and browser provisioning.",
    )
    parser.add_argument(
        "--parity-sample-size",
        type=int,
        default=64,
        help="Downsample size for lightweight HTML-vs-PDF visual diff scoring. Default: 64.",
    )
    return parser.parse_args()


def resolve_browser_path(explicit_path: str | None) -> str | None:
    candidates = [
        explicit_path,
        os.environ.get("PLAYWRIGHT_CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))

    return None


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


def analyze_document(page: Any) -> dict[str, Any]:
    sheet_count = page.locator(".sheet").count()
    if sheet_count == 0:
        raise RuntimeError("No `.sheet` pages found. This validator expects print pages to use the `.sheet` convention.")

    return {
        "title": page.title(),
        "sheetCount": sheet_count,
        "images": page.locator("img").evaluate_all(IMAGE_EVAL_JS),
        "sheets": page.locator(".sheet").evaluate_all(SHEET_EVAL_JS),
        "rules": page.evaluate(STYLE_RULES_EVAL_JS),
    }


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


def render_pdf_page_artifacts(
    pdf_path: Path,
    output_dir: Path,
    prefix: str,
    html_page_artifacts: list[dict[str, Any]],
    *,
    auto_install: bool,
) -> list[dict[str, Any]]:
    fitz = load_pymupdf(auto_install)
    document = fitz.open(str(pdf_path))
    artifacts: list[dict[str, Any]] = []

    try:
        for page_number, pdf_page in enumerate(document, start=1):
            html_artifact = next(
                (artifact for artifact in html_page_artifacts if artifact["page"] == page_number),
                None,
            )
            target_width = (
                int(html_artifact["screenshotWidthPx"])
                if html_artifact
                else int(round(pdf_page.rect.width * 2))
            )
            zoom = target_width / float(pdf_page.rect.width)
            pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            screenshot_path = output_dir / f"{prefix}-pdf-page-{page_number}.png"
            pixmap.save(str(screenshot_path))
            screenshot_width_px, screenshot_height_px = read_png_dimensions(screenshot_path)
            screenshot_aspect_ratio = screenshot_width_px / screenshot_height_px

            artifacts.append(
                {
                    "page": page_number,
                    "path": str(screenshot_path),
                    "widthPt": round(float(pdf_page.rect.width), 2),
                    "heightPt": round(float(pdf_page.rect.height), 2),
                    "screenshotWidthPx": screenshot_width_px,
                    "screenshotHeightPx": screenshot_height_px,
                    "screenshotAspectRatio": round(screenshot_aspect_ratio, 4),
                    "usesA4Aspect": abs(screenshot_aspect_ratio - A4_ASPECT_RATIO) <= 0.02,
                }
            )
    finally:
        document.close()

    return artifacts


def inspect_pdf_document(
    pdf_path: Path,
    *,
    auto_install: bool,
) -> tuple[int, list[dict[str, float]]]:
    fitz = load_pymupdf(auto_install)
    document = fitz.open(str(pdf_path))
    try:
        media_boxes = [
            {
                "widthPt": round(float(page.rect.width), 2),
                "heightPt": round(float(page.rect.height), 2),
            }
            for page in document
        ]
        return document.page_count, media_boxes
    finally:
        document.close()


def build_pdf_html_parity(
    context: Any,
    html_page_artifacts: list[dict[str, Any]],
    pdf_page_artifacts: list[dict[str, Any]],
    *,
    sample_size: int,
) -> list[dict[str, Any]]:
    comparison_page = context.new_page()
    comparison_page.set_content("<!doctype html><html><body></body></html>")
    parity_pages: list[dict[str, Any]] = []

    try:
        pdf_index = {artifact["page"]: artifact for artifact in pdf_page_artifacts}
        for html_artifact in html_page_artifacts:
            page_number = html_artifact["page"]
            pdf_artifact = pdf_index.get(page_number)
            if not pdf_artifact:
                parity_pages.append(
                    {
                        "page": page_number,
                        "htmlScreenshot": html_artifact["path"],
                        "pdfScreenshot": None,
                        "visualDiffScore": None,
                        "matchSuggested": False,
                    }
                )
                continue

            visual_diff_score = comparison_page.evaluate(
                IMAGE_DIFF_EVAL_JS,
                {
                    "leftDataUrl": path_to_data_url(Path(html_artifact["path"])),
                    "rightDataUrl": path_to_data_url(Path(pdf_artifact["path"])),
                    "sampleSize": sample_size,
                },
            )
            same_dimensions = (
                abs(html_artifact["screenshotWidthPx"] - pdf_artifact["screenshotWidthPx"]) <= 4
                and abs(html_artifact["screenshotHeightPx"] - pdf_artifact["screenshotHeightPx"]) <= 4
            )
            match_suggested = (
                visual_diff_score <= DEFAULT_PARITY_DIFF_THRESHOLD
                and same_dimensions
                and pdf_artifact["usesA4Aspect"]
            )

            parity_pages.append(
                {
                    "page": page_number,
                    "htmlScreenshot": html_artifact["path"],
                    "pdfScreenshot": pdf_artifact["path"],
                    "htmlScreenshotWidthPx": html_artifact["screenshotWidthPx"],
                    "htmlScreenshotHeightPx": html_artifact["screenshotHeightPx"],
                    "pdfScreenshotWidthPx": pdf_artifact["screenshotWidthPx"],
                    "pdfScreenshotHeightPx": pdf_artifact["screenshotHeightPx"],
                    "sameDimensions": same_dimensions,
                    "visualDiffScore": visual_diff_score,
                    "matchSuggested": match_suggested,
                }
            )
    finally:
        comparison_page.close()

    return parity_pages


def build_checks(summary: dict[str, Any]) -> tuple[dict[str, bool | None], dict[str, bool]]:
    analysis = summary["analysis"]
    pdf_screenshots = summary["pdf"]["screenshots"]["pages"]
    parity_pages = summary["parity"]["pages"]
    required_checks = {
        "noConsoleProblems": len(summary["consoleMessages"]) == 0,
        "allImagesLoaded": all(
            image["complete"]
            and image["naturalWidth"] > 0
            and image["naturalHeight"] > 0
            for image in analysis["images"]
        ),
        "noSheetOverflow": all(
            sheet["overflow"]["x"] <= 1 and sheet["overflow"]["y"] <= 1
            for sheet in analysis["sheets"]
        ),
        "noDetectedClipping": all(
            sheet["issueCount"] == 0 for sheet in analysis["sheets"]
        ),
        "hasA4PageRule": analysis["rules"]["a4Page"],
        "hasPrintMediaRule": analysis["rules"]["printMedia"],
        "hasBreakAvoidRule": analysis["rules"]["breakAvoid"],
        "hasPrintColorAdjust": analysis["rules"]["printColorAdjust"],
        "sheetsUseA4Aspect": all(
            sheet.get("usesA4Aspect") for sheet in analysis["sheets"]
        ),
        "pdfOptimizedForFastView": summary["pdf"].get("optimization", {}).get("linearized") is True,
        "pdfPageCountMatches": summary["pdf"]["pageCount"] == analysis["sheetCount"],
        "pdfScreenshotCountMatchesHtml": len(pdf_screenshots) == len(summary["screenshots"]["pages"]),
        "pageScreenshotsUseA4Aspect": all(
            artifact["usesA4Aspect"] for artifact in summary["screenshots"]["pages"]
        ),
        "pdfScreenshotsUseA4Aspect": all(
            artifact["usesA4Aspect"] for artifact in pdf_screenshots
        ),
        "fastViewPdfPageCountMatchesHtml": summary["fastViewPdf"]["pageCount"] == analysis["sheetCount"],
        "fastViewPdfOptimizedForFastView": summary["fastViewPdf"].get("optimization", {}).get("linearized") is True,
    }
    optional_checks = {
        "pageQueryIsolatesSheets": all(
            artifact["visibleSheetCount"] == 1 for artifact in summary["screenshots"]["pages"]
        ),
        "pagesAvoidLargeBottomGaps": all(
            (sheet.get("density") or {}).get("bottomGapRatio", 0) <= 0.22
            for sheet in analysis["sheets"]
        ),
        "pdfVisualParityLooksClose": all(
            page.get("matchSuggested") is True for page in parity_pages
        ) if parity_pages else True,
    }
    return required_checks, optional_checks


def launch_browser(playwright: Any, *, browser_path: str | None, auto_install: bool) -> tuple[Any, str | None]:
    launch_kwargs: dict[str, Any] = {"headless": True}
    if browser_path:
        launch_kwargs["executable_path"] = browser_path

    try:
        return playwright.chromium.launch(**launch_kwargs), browser_path
    except Exception as first_error:
        if not auto_install:
            raise

    ensure_playwright_runtime(auto_install=True)
    try:
        return playwright.chromium.launch(**launch_kwargs), browser_path
    except Exception as second_error:
        fallback_browser_path = resolve_browser_path(None) or try_install_system_browser()
        if fallback_browser_path:
            return (
                playwright.chromium.launch(
                    headless=True,
                    executable_path=fallback_browser_path,
                ),
                fallback_browser_path,
            )
        raise RuntimeError(
            "Unable to launch Chromium even after automatic Playwright/browser provisioning."
        ) from second_error


def main() -> int:
    args = parse_args()
    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file does not exist: {html_path}")

    output_dir = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir
        else default_output_dir(html_path)
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix or html_path.stem
    base_url = html_path.as_uri()
    browser_path = resolve_browser_path(args.browser_path)
    auto_install = not args.no_auto_install
    console_messages: list[dict[str, str]] = []
    sync_playwright = load_playwright(auto_install)

    with sync_playwright() as playwright:
        browser, browser_path = launch_browser(
            playwright,
            browser_path=browser_path,
            auto_install=auto_install,
        )
        context = browser.new_context(
            viewport={
                "width": args.viewport_width,
                "height": args.viewport_height,
            },
            device_scale_factor=args.device_scale_factor,
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_messages.append(
                {"type": message.type, "text": message.text}
            )
            if message.type in {"warning", "error"}
            else None,
        )
        page.on(
            "pageerror",
            lambda error: console_messages.append(
                {"type": "pageerror", "text": str(error)}
            ),
        )

        page.goto(with_query_params(base_url, print=1), wait_until="load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(args.settle_ms)

        analysis = analyze_document(page)

        stacked_path = output_dir / f"{prefix}-screen-stacked.png"
        page.screenshot(path=str(stacked_path), full_page=True)

        page_artifacts = capture_page_artifacts(
            context=context,
            base_url=base_url,
            sheet_count=analysis["sheetCount"],
            output_dir=output_dir,
            prefix=prefix,
            settle_ms=args.settle_ms,
        )
        fast_view_pdf = build_fast_view_pdf(
            page_artifacts,
            output_dir,
            prefix,
            auto_install=auto_install,
        )

        page.emulate_media(media="print")
        pdf_path = output_dir / f"{prefix}.pdf"
        raw_pdf_path = output_dir / f"{prefix}-raw.pdf"
        page.pdf(
            path=str(raw_pdf_path),
            print_background=True,
            prefer_css_page_size=True,
        )
        pdf_optimization = optimize_pdf_for_fast_view(
            raw_pdf_path,
            pdf_path,
            auto_install=auto_install,
        )
        try:
            raw_pdf_path.unlink()
        except OSError:
            pass
        pdf_page_artifacts = render_pdf_page_artifacts(
            pdf_path,
            output_dir,
            prefix,
            page_artifacts,
            auto_install=auto_install,
        )
        parity_pages = build_pdf_html_parity(
            context,
            page_artifacts,
            pdf_page_artifacts,
            sample_size=args.parity_sample_size,
        )
        pdf_page_count, media_boxes = inspect_pdf_document(
            pdf_path,
            auto_install=auto_install,
        )

        browser.close()

    summary: dict[str, Any] = {
        "htmlPath": str(html_path),
        "outputDir": str(output_dir),
        "browser": {
            "resolvedPath": browser_path,
            "usesBundledBrowser": browser_path is None,
            "autoInstallEnabled": auto_install,
        },
        "analysis": analysis,
        "consoleMessages": console_messages,
        "screenshots": {
            "stacked": str(stacked_path),
            "pages": page_artifacts,
        },
        "pdf": {
            "path": str(pdf_path),
            "bytes": pdf_path.stat().st_size,
            "pageCount": pdf_page_count,
            "mediaBoxes": media_boxes,
            "optimization": pdf_optimization,
            "screenshots": {
                "pages": pdf_page_artifacts,
            },
        },
        "fastViewPdf": fast_view_pdf,
        "parity": {
            "sampleSize": args.parity_sample_size,
            "diffThreshold": DEFAULT_PARITY_DIFF_THRESHOLD,
            "pages": parity_pages,
        },
    }

    checks, optional_checks = build_checks(summary)
    summary["checks"] = checks
    summary["optionalChecks"] = optional_checks
    summary["pass"] = all(value is True or value is None for value in checks.values())

    report_path = output_dir / f"{prefix}-validation-report.json"
    report_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    failed_checks = [name for name, passed in checks.items() if passed is not True]
    print(f"Report: {report_path}")
    print(f"Pass: {summary['pass']}")
    print(f"Pages: {analysis['sheetCount']}")
    print(f"PDF: {pdf_path}")
    print(f"Fast-view PDF: {fast_view_pdf['path']}")
    if optional_checks:
        print(f"Optional checks: {json.dumps(optional_checks, ensure_ascii=False)}")
    if failed_checks:
        print(f"Failed checks: {', '.join(failed_checks)}")

    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
