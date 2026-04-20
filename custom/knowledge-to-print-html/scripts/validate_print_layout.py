from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .checks import (
        DEFAULT_PARITY_DIFF_THRESHOLD,
        analyze_document,
        build_checks,
    )
    from .page_capture import (
        capture_page_artifacts,
        default_output_dir,
        with_query_params,
    )
    from .pdf_artifacts import (
        build_fast_view_pdf,
        build_pdf_html_parity,
        inspect_pdf_document,
        optimize_pdf_for_fast_view,
        render_pdf_page_artifacts,
    )
    from .runtime_bootstrap import (
        launch_browser,
        load_playwright,
        resolve_browser_path,
    )
    from .svg_enclosure import inspect_svg_visual_enclosure
except ImportError:  # pragma: no cover - supports direct script execution from scripts/
    from checks import (
        DEFAULT_PARITY_DIFF_THRESHOLD,
        analyze_document,
        build_checks,
    )
    from page_capture import (
        capture_page_artifacts,
        default_output_dir,
        with_query_params,
    )
    from pdf_artifacts import (
        build_fast_view_pdf,
        build_pdf_html_parity,
        inspect_pdf_document,
        optimize_pdf_for_fast_view,
        render_pdf_page_artifacts,
    )
    from runtime_bootstrap import (
        launch_browser,
        load_playwright,
        resolve_browser_path,
    )
    from svg_enclosure import inspect_svg_visual_enclosure


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a local print-first handout.html and export screenshots, PDF, and a JSON report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/validate_print_layout.py --html artifacts/knowledge-handout/topic/handout.html\n"
            "  python scripts/validate_print_layout.py --html artifacts/knowledge-handout/topic/handout.html --device-scale-factor 3.125 --out-dir artifacts/knowledge-handout/topic/screens/high-dpi\n"
            "\n"
            "Use the high-DPI example when you need a raster/image-only PDF at roughly 300 DPI."
        ),
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
        help="Device scale factor for captures. Default: 1.5. Use 3.125 for roughly 300 DPI A4 image-only PDF output.",
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

        analysis = analyze_document(page, html_path)

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
