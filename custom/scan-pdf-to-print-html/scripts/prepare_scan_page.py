#!/usr/bin/env python3
"""Create a cleaned helper image from a noisy scan page."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output image path")
    parser.add_argument("--upscale", type=float, default=2.0, help="Upscale factor before cleanup")
    parser.add_argument(
        "--autocontrast-cutoff",
        type=float,
        default=1.0,
        help="Autocontrast cutoff percentage (default: 1.0)",
    )
    parser.add_argument("--sharpen", type=float, default=1.6, help="Sharpness factor (default: 1.6)")
    parser.add_argument(
        "--median-size",
        type=int,
        default=0,
        help="Median filter kernel size. Use 0 to disable.",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        help="Optional grayscale threshold 0-255 for binarization",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input image not found: {input_path}")

    image = Image.open(input_path).convert("L")
    if args.upscale and args.upscale != 1.0:
        width = max(1, int(round(image.width * args.upscale)))
        height = max(1, int(round(image.height * args.upscale)))
        image = image.resize((width, height), Image.Resampling.LANCZOS)

    image = ImageOps.autocontrast(image, cutoff=args.autocontrast_cutoff)

    if args.median_size and args.median_size > 0:
        image = image.filter(ImageFilter.MedianFilter(size=args.median_size))

    if args.sharpen and args.sharpen != 1.0:
        image = ImageEnhance.Sharpness(image).enhance(args.sharpen)

    if args.threshold is not None:
        threshold = max(0, min(255, args.threshold))
        image = image.point(lambda value: 255 if value >= threshold else 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
