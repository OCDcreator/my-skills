from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .page_capture import A4_ASPECT_RATIO, build_a4_clip, read_png_dimensions, with_query_params
    from .runtime_bootstrap import launch_browser, load_playwright, resolve_browser_path
except ImportError:  # pragma: no cover - supports direct script execution from scripts/
    from page_capture import A4_ASPECT_RATIO, build_a4_clip, read_png_dimensions, with_query_params
    from runtime_bootstrap import launch_browser, load_playwright, resolve_browser_path


SKILL_DIR = Path(__file__).resolve().parents[1]
PRESETS_DIR = SKILL_DIR / "templates" / "presets"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render first-page preview PNGs for all print preset templates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/render_preset_previews.py\n"
            "  python scripts/render_preset_previews.py --preset editorial-atlas --no-auto-install\n"
        ),
    )
    parser.add_argument(
        "--preset",
        action="append",
        help="Preset folder name to render. Repeat to render multiple. Defaults to all presets.",
    )
    parser.add_argument(
        "--presets-dir",
        default=str(PRESETS_DIR),
        help="Preset root directory. Defaults to templates/presets.",
    )
    parser.add_argument(
        "--output-name",
        default="preview.png",
        help="Preview filename to write inside each preset folder. Default: preview.png.",
    )
    parser.add_argument(
        "--device-scale-factor",
        type=float,
        default=1.0,
        help="Screenshot device scale factor. Default: 1.0 for compact repo-friendly previews.",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1200,
        help="Browser viewport width in CSS pixels. Default: 1200.",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1700,
        help="Browser viewport height in CSS pixels. Default: 1700.",
    )
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=250,
        help="Milliseconds to wait before capture. Default: 250.",
    )
    parser.add_argument(
        "--browser-path",
        default=None,
        help="Optional explicit Chromium/Chrome/Edge executable path.",
    )
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="Disable automatic Playwright/browser provisioning.",
    )
    return parser.parse_args()


def iter_preset_dirs(presets_dir: Path, selected_names: list[str] | None) -> list[Path]:
    if selected_names:
        preset_dirs = [presets_dir / name for name in selected_names]
    else:
        preset_dirs = [
            path
            for path in presets_dir.iterdir()
            if path.is_dir() and path.name != "_shared"
        ]
    missing = [path.name for path in preset_dirs if not (path / "handout.html").exists()]
    if missing:
        raise RuntimeError(f"Preset handout.html missing for: {', '.join(missing)}")
    return sorted(preset_dirs, key=lambda path: path.name)


def render_preview(
    context: Any,
    *,
    preset_dir: Path,
    output_name: str,
    settle_ms: int,
) -> dict[str, Any]:
    html_path = preset_dir / "handout.html"
    output_path = preset_dir / output_name
    page = context.new_page()
    try:
        page.goto(with_query_params(html_path.resolve().as_uri(), print=1, preview=1), wait_until="load")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(settle_ms)

        target_locator = page.locator(".sheet").first
        if target_locator.count() == 0:
            raise RuntimeError(f"No `.sheet` page found in {html_path}")
        target_locator.scroll_into_view_if_needed()
        bounding_box = target_locator.bounding_box()
        if not bounding_box:
            raise RuntimeError(f"Unable to measure first sheet for {html_path}")

        page.screenshot(
            path=str(output_path),
            clip=build_a4_clip(bounding_box),
        )
    finally:
        page.close()

    screenshot_width_px, screenshot_height_px = read_png_dimensions(output_path)
    aspect_ratio = screenshot_width_px / screenshot_height_px
    return {
        "preset": preset_dir.name,
        "path": str(output_path),
        "widthPx": screenshot_width_px,
        "heightPx": screenshot_height_px,
        "usesA4Aspect": abs(aspect_ratio - A4_ASPECT_RATIO) <= 0.02,
    }


def main() -> int:
    args = parse_args()
    presets_dir = Path(args.presets_dir).expanduser().resolve()
    preset_dirs = iter_preset_dirs(presets_dir, args.preset)
    auto_install = not args.no_auto_install
    sync_playwright = load_playwright(auto_install)
    browser_path = resolve_browser_path(args.browser_path)
    results: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser, _resolved_browser_path = launch_browser(
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
        try:
            for preset_dir in preset_dirs:
                result = render_preview(
                    context,
                    preset_dir=preset_dir,
                    output_name=args.output_name,
                    settle_ms=args.settle_ms,
                )
                results.append(result)
                status = "A4" if result["usesA4Aspect"] else "not-A4"
                print(
                    f"{result['preset']}: {result['path']} "
                    f"({result['widthPx']}x{result['heightPx']}, {status})"
                )
        finally:
            context.close()
            browser.close()

    if not all(result["usesA4Aspect"] for result in results):
        print(json.dumps(results, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
