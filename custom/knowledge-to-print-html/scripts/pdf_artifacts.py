from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

try:
    from .checks import DEFAULT_PARITY_DIFF_THRESHOLD
    from .page_capture import A4_ASPECT_RATIO, path_to_data_url, read_png_dimensions
    from .runtime_bootstrap import (
        load_pymupdf,
        resolve_qpdf_path,
        run_bootstrap_command,
        try_install_qpdf,
    )
except ImportError:  # pragma: no cover - supports direct script execution from scripts/
    from checks import DEFAULT_PARITY_DIFF_THRESHOLD
    from page_capture import A4_ASPECT_RATIO, path_to_data_url, read_png_dimensions
    from runtime_bootstrap import (
        load_pymupdf,
        resolve_qpdf_path,
        run_bootstrap_command,
        try_install_qpdf,
    )

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
