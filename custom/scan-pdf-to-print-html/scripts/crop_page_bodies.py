#!/usr/bin/env python3
"""Crop rendered PDF page images down to their main body region."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


DEFAULT_THRESHOLD = 245
DEFAULT_ROW_FILL_RATIO = 0.03
DEFAULT_COL_FILL_RATIO = 0.03
DEFAULT_PADDING_RATIO = 0.015


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Path to pages/manifest.json")
    parser.add_argument("--out-dir", required=True, help="Directory for cropped body page images")
    parser.add_argument("--out-pdf", help="Optional output PDF built from cropped body images")
    return parser


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def content_rows(mask: list[list[bool]]) -> list[int]:
    return [sum(1 for cell in row if cell) for row in mask]


def content_cols(mask: list[list[bool]]) -> list[int]:
    if not mask:
        return []
    width = len(mask[0])
    return [sum(1 for row in mask if row[index]) for index in range(width)]


def find_runs(counts: list[int], minimum_count: int) -> list[tuple[int, int, int]]:
    runs: list[tuple[int, int, int]] = []
    start: int | None = None
    total = 0
    for index, count in enumerate(counts):
        if count >= minimum_count:
            if start is None:
                start = index
                total = 0
            total += count
            continue
        if start is not None:
            runs.append((start, index, total))
            start = None
            total = 0
    if start is not None:
        runs.append((start, len(counts), total))
    return runs


def choose_primary_run(runs: list[tuple[int, int, int]]) -> tuple[int, int] | None:
    if not runs:
        return None
    start, end, _total = max(runs, key=lambda item: (item[1] - item[0], item[2]))
    return start, end


def build_content_mask(image: Image.Image, threshold: int) -> list[list[bool]]:
    grayscale = image.convert("L")
    width, height = grayscale.size
    pixels = grayscale.load()
    return [
        [pixels[x, y] < threshold for x in range(width)]
        for y in range(height)
    ]


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def detect_body_bbox(
    image: Image.Image,
    *,
    threshold: int = DEFAULT_THRESHOLD,
    row_fill_ratio: float = DEFAULT_ROW_FILL_RATIO,
    col_fill_ratio: float = DEFAULT_COL_FILL_RATIO,
    padding_ratio: float = DEFAULT_PADDING_RATIO,
) -> tuple[int, int, int, int]:
    width, height = image.size
    mask = build_content_mask(image, threshold)

    row_min = max(1, int(width * row_fill_ratio))
    row_runs = find_runs(content_rows(mask), row_min)
    row_run = choose_primary_run(row_runs)
    if row_run is None:
        return 0, 0, width, height
    top, bottom = row_run

    body_mask = mask[top:bottom]
    col_min = max(1, int((bottom - top) * col_fill_ratio))
    col_runs = find_runs(content_cols(body_mask), col_min)
    col_run = choose_primary_run(col_runs)
    if col_run is None:
        return 0, top, width, bottom
    left, right = col_run

    pad_x = int(width * padding_ratio)
    pad_y = int(height * padding_ratio)
    cropped_left = clamp(left - pad_x, 0, width)
    cropped_top = clamp(top - pad_y, 0, height)
    cropped_right = clamp(right + pad_x, cropped_left + 1, width)
    cropped_bottom = clamp(bottom + pad_y, cropped_top + 1, height)
    return cropped_left, cropped_top, cropped_right, cropped_bottom


def crop_page_image(image: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int]]:
    bbox = detect_body_bbox(image)
    return image.crop(bbox), bbox


def load_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid manifest object: {path}")
    return payload


def relative_or_absolute(path: Path) -> str:
    return str(path.resolve())


def build_body_pdf(images: list[Image.Image], out_pdf: Path, dpi: int) -> None:
    if not images:
        raise SystemExit("No cropped images available to write body-only PDF.")
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    rgb_images = [image.convert("RGB") for image in images]
    first, *rest = rgb_images
    first.save(out_pdf, "PDF", resolution=dpi, save_all=True, append_images=rest)


def process_manifest(manifest_path: Path, out_dir: Path, out_pdf: Path | None) -> Path:
    manifest = load_manifest(manifest_path)
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise SystemExit(f"Invalid pages manifest: {manifest_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    cropped_pages: list[dict[str, object]] = []
    pdf_images: list[Image.Image] = []
    dpi = int(manifest.get("dpi") or 220)

    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise SystemExit(f"Invalid page entry at index {index}: expected object")
        page_number = int(page.get("page_number") or index)
        image_path = Path(str(page.get("image_path", ""))).expanduser().resolve()
        if not image_path.exists():
            raise SystemExit(f"Rendered page image not found: {image_path}")

        with Image.open(image_path) as source_image:
            cropped_image, bbox = crop_page_image(source_image)
            body_name = f"{image_path.stem}.body.png"
            body_path = out_dir / body_name
            cropped_image.save(body_path)
            pdf_images.append(cropped_image.copy())

        left, top, right, bottom = bbox
        cropped_pages.append(
            {
                "page_number": page_number,
                "source_image_path": relative_or_absolute(image_path),
                "body_image_path": relative_or_absolute(body_path),
                "body_bbox": {
                    "left": left,
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                },
                "width": right - left,
                "height": bottom - top,
                "dpi": int(page.get("dpi") or dpi),
            }
        )

    if out_pdf is not None:
        build_body_pdf(pdf_images, out_pdf, dpi)

    output_manifest = {
        "source_manifest": relative_or_absolute(manifest_path),
        "source_pdf": manifest.get("source_pdf"),
        "cropped_page_count": len(cropped_pages),
        "dpi": dpi,
        "body_pdf_path": relative_or_absolute(out_pdf) if out_pdf is not None else None,
        "pages": cropped_pages,
    }
    output_manifest_path = out_dir / "manifest.json"
    write_json(output_manifest_path, output_manifest)
    return output_manifest_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_pdf = Path(args.out_pdf).expanduser().resolve() if args.out_pdf else None

    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    output_manifest_path = process_manifest(manifest_path, out_dir, out_pdf)
    print(str(output_manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
