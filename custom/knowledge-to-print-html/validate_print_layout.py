from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Playwright is required. Install it first, for example: "
        "`python -m pip install playwright`."
    ) from exc


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
            page.screenshot(path=str(screenshot_path), full_page=True)

            target_locator = page_sheet_locator(page, page_number)

            rect = target_locator.evaluate(RECT_EVAL_JS)
            visible_sheet_count = page.locator(".sheet").evaluate_all(
                VISIBLE_SHEET_COUNT_EVAL_JS
            )

            page_artifacts.append(
                {
                    "page": page_number,
                    "path": str(screenshot_path),
                    "width": rect["width"],
                    "height": rect["height"],
                    "hidden": rect["hidden"],
                    "visibleSheetCount": visible_sheet_count,
                    "isolatedTargetPage": isolation["targetPage"],
                }
            )
        finally:
            page.close()

    return page_artifacts


def build_checks(summary: dict[str, Any]) -> tuple[dict[str, bool | None], dict[str, bool]]:
    analysis = summary["analysis"]
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
        "pdfPageCountMatches": summary["pdf"]["pageCount"] == analysis["sheetCount"],
    }
    optional_checks = {
        "pageQueryIsolatesSheets": all(
            artifact["visibleSheetCount"] == 1 for artifact in summary["screenshots"]["pages"]
        ),
        "pagesAvoidLargeBottomGaps": all(
            (sheet.get("density") or {}).get("bottomGapRatio", 0) <= 0.22
            for sheet in analysis["sheets"]
        ),
    }
    return required_checks, optional_checks


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
    console_messages: list[dict[str, str]] = []

    with sync_playwright() as playwright:
        launch_kwargs: dict[str, Any] = {"headless": True}
        if browser_path:
            launch_kwargs["executable_path"] = browser_path

        browser = playwright.chromium.launch(**launch_kwargs)
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

        page.emulate_media(media="print")
        pdf_path = output_dir / f"{prefix}.pdf"
        page.pdf(
            path=str(pdf_path),
            print_background=True,
            prefer_css_page_size=True,
        )
        pdf_text = pdf_path.read_bytes().decode("latin1", errors="ignore")
        page_counts = [
            int(match.group(1)) for match in re.finditer(r"/Count\s+(\d+)", pdf_text)
        ]
        media_boxes = [
            {
                "widthPt": float(match.group(1)),
                "heightPt": float(match.group(2)),
            }
            for match in re.finditer(
                r"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]",
                pdf_text,
            )
        ]
        pdf_page_count = max(page_counts) if page_counts else None

        browser.close()

    summary: dict[str, Any] = {
        "htmlPath": str(html_path),
        "outputDir": str(output_dir),
        "browser": {
            "resolvedPath": browser_path,
            "usesBundledBrowser": browser_path is None,
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
    if optional_checks:
        print(f"Optional checks: {json.dumps(optional_checks, ensure_ascii=False)}")
    if failed_checks:
        print(f"Failed checks: {', '.join(failed_checks)}")

    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
