from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_MAX_CARD_GRID_COUNT = 2
DEFAULT_MAX_CARD_AREA_RATIO = 0.35
DEFAULT_MIN_CARD_TEXT_SIZE_PX = 11.0
DEFAULT_MIN_BODY_FONT_SIZE_PX = 11.5
DEFAULT_MIN_BODY_LINE_HEIGHT_RATIO = 1.35
DEFAULT_MIN_PARAGRAPH_SPACING_RATIO = 0.45


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a sequential page-review packet for print handouts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/review_print_pages.py --html artifacts/knowledge-handout/topic/handout.html\n"
            "  python scripts/review_print_pages.py --html artifacts/knowledge-handout/topic/handout.html --review-language zh\n"
            "\n"
            "Run this after layout validation so the packet includes the latest screenshots, parity data, and subagent prompt files."
        ),
    )
    parser.add_argument("--html", required=True, help="Path to the handout.html file.")
    parser.add_argument(
        "--prefix",
        help="Artifact prefix. Defaults to the HTML filename stem.",
    )
    parser.add_argument(
        "--out-dir",
        help="Override output directory for screenshots and report.",
    )
    parser.add_argument(
        "--review-dir",
        help="Override review packet directory. Defaults to <out-dir>/page-review.",
    )
    parser.add_argument(
        "--browser-path",
        help="Optional browser executable path to pass through to validate_print_layout.py.",
    )
    parser.add_argument(
        "--review-language",
        choices=("auto", "en", "zh"),
        default="auto",
        help="Language for the generated subagent prompt. Default: auto.",
    )
    parser.add_argument(
        "--max-bottom-gap-ratio",
        type=float,
        default=0.22,
        help="Heuristic fail threshold for bottom whitespace ratio. Default: 0.22.",
    )
    parser.add_argument(
        "--min-content-height-ratio",
        type=float,
        default=0.58,
        help="Heuristic fail threshold for page content height ratio. Default: 0.58.",
    )
    parser.add_argument(
        "--min-figure-width-ratio",
        type=float,
        default=0.50,
        help="Heuristic warning threshold for the largest figure width ratio. Default: 0.50.",
    )
    parser.add_argument(
        "--min-figure-area-ratio",
        type=float,
        default=0.10,
        help="Heuristic warning threshold for the largest figure area ratio. Default: 0.10.",
    )
    parser.add_argument(
        "--max-card-grid-count",
        type=int,
        default=DEFAULT_MAX_CARD_GRID_COUNT,
        help="Fail when too many small card-like blocks create a dashboard grid. Default: 2.",
    )
    parser.add_argument(
        "--max-card-area-ratio",
        type=float,
        default=DEFAULT_MAX_CARD_AREA_RATIO,
        help="Fail when card-like blocks occupy too much of the page. Default: 0.35.",
    )
    parser.add_argument(
        "--min-card-text-size-px",
        type=float,
        default=DEFAULT_MIN_CARD_TEXT_SIZE_PX,
        help="Fail when dense card-like blocks use text smaller than this threshold. Default: 11.0.",
    )
    parser.add_argument(
        "--min-body-font-size-px",
        type=float,
        default=DEFAULT_MIN_BODY_FONT_SIZE_PX,
        help="Fail when body text gets too small for print reading. Default: 11.5.",
    )
    parser.add_argument(
        "--min-body-line-height-ratio",
        type=float,
        default=DEFAULT_MIN_BODY_LINE_HEIGHT_RATIO,
        help="Fail when line height is compressed below this ratio. Default: 1.35.",
    )
    parser.add_argument(
        "--min-paragraph-spacing-ratio",
        type=float,
        default=DEFAULT_MIN_PARAGRAPH_SPACING_RATIO,
        help="Fail when paragraph spacing is compressed below this ratio. Default: 0.45.",
    )
    return parser.parse_args()


def run_validation(args: argparse.Namespace, html_path: Path, prefix: str) -> Path:
    command = [
        sys.executable,
        str(Path(__file__).with_name("validate_print_layout.py")),
        "--html",
        str(html_path),
        "--prefix",
        prefix,
    ]
    if args.out_dir:
        command.extend(["--out-dir", args.out_dir])
    if args.browser_path:
        command.extend(["--browser-path", args.browser_path])

    output_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else html_path.parent / "screens" / "py-latest"
    report_path = output_dir / f"{prefix}-validation-report.json"

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        if report_path.exists():
            return report_path
        raise

    return report_path


def build_flags(
    page: dict[str, Any],
    thresholds: dict[str, float],
    screenshot: dict[str, Any],
    pdf_screenshot: dict[str, Any] | None,
    parity: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    density = page.get("density") or {}
    figures = page.get("figures") or {}
    cards = page.get("cards") or {}
    typography = page.get("typography") or {}
    meta = page.get("meta") or {}
    container_text_overflow = page.get("containerTextOverflow") or {}
    svg_visual_enclosure = page.get("svgVisualEnclosure") or {}
    largest_figure = figures.get("largest")

    if page.get("issueCount", 0) > 0:
        flags.append(
            {
                "severity": "fail",
                "code": "dom_overflow",
                "message": "Detected DOM clipping or overflow inside the sheet.",
            }
        )

    if density.get("bottomGapRatio", 0) > thresholds["max_bottom_gap_ratio"]:
        flags.append(
            {
                "severity": "fail",
                "code": "large_bottom_gap",
                "message": "Large empty area remains at the bottom of the page.",
                "actual": density.get("bottomGapRatio"),
                "threshold": thresholds["max_bottom_gap_ratio"],
            }
        )

    if density.get("contentHeightRatio", 1) < thresholds["min_content_height_ratio"]:
        flags.append(
            {
                "severity": "fail",
                "code": "sparse_page",
                "message": "Visible content occupies too little of the page height.",
                "actual": density.get("contentHeightRatio"),
                "threshold": thresholds["min_content_height_ratio"],
            }
        )

    if largest_figure:
        if largest_figure.get("widthRatio", 1) < thresholds["min_figure_width_ratio"]:
            flags.append(
                {
                    "severity": "warn",
                    "code": "small_figure_width",
                    "message": "Largest figure is narrow relative to the page or column.",
                    "actual": largest_figure.get("widthRatio"),
                    "threshold": thresholds["min_figure_width_ratio"],
                }
            )
        if largest_figure.get("areaRatio", 1) < thresholds["min_figure_area_ratio"]:
            flags.append(
                {
                    "severity": "warn",
                    "code": "small_figure_area",
                    "message": "Largest figure occupies too little visual area for a teaching diagram.",
                    "actual": largest_figure.get("areaRatio"),
                    "threshold": thresholds["min_figure_area_ratio"],
                }
            )

    card_grid_count = cards.get("gridLikeCount", 0)
    if card_grid_count > thresholds["max_card_grid_count"] or (
        cards.get("count", 0) > thresholds["max_card_grid_count"]
        and cards.get("totalAreaRatio", 0) > thresholds["max_card_area_ratio"]
        and (
            cards.get("minSmallestFontSizePx") is not None
            and cards.get("minSmallestFontSizePx") < thresholds["min_card_text_size_px"]
        )
    ):
        flags.append(
            {
                "severity": "fail",
                "code": "card_grid_antipattern",
                "message": "Dense card-like grid makes the page read like a dashboard instead of a handout.",
                "actual": {
                    "count": cards.get("count"),
                    "gridLikeCount": card_grid_count,
                    "totalAreaRatio": cards.get("totalAreaRatio"),
                    "smallTextCount": cards.get("smallTextCount"),
                    "minSmallestFontSizePx": cards.get("minSmallestFontSizePx"),
                },
                "threshold": {
                    "maxCardGridCount": thresholds["max_card_grid_count"],
                    "maxCardAreaRatio": thresholds["max_card_area_ratio"],
                    "minCardTextSizePx": thresholds["min_card_text_size_px"],
                },
            }
        )

    min_body_font_size = typography.get("minBodyFontSizePx")
    min_line_height_ratio = typography.get("minLineHeightRatio")
    min_paragraph_spacing_ratio = typography.get("minParagraphSpacingRatio")
    small_body_text = (
        min_body_font_size is not None
        and min_body_font_size < thresholds["min_body_font_size_px"]
    )
    tight_line_height = (
        min_line_height_ratio is not None
        and min_line_height_ratio < thresholds["min_body_line_height_ratio"]
    )
    tight_paragraph_spacing = (
        min_paragraph_spacing_ratio is not None
        and min_paragraph_spacing_ratio < thresholds["min_paragraph_spacing_ratio"]
    )
    if small_body_text or (tight_line_height and tight_paragraph_spacing):
        flags.append(
            {
                "severity": "fail",
                "code": "compressed_typographic_rhythm",
                "message": "Typography has been compressed too aggressively; reflow content instead of tightening type.",
                "actual": {
                    "minBodyFontSizePx": min_body_font_size,
                    "minLineHeightRatio": min_line_height_ratio,
                    "minParagraphSpacingRatio": min_paragraph_spacing_ratio,
                },
                "threshold": {
                    "minBodyFontSizePx": thresholds["min_body_font_size_px"],
                    "minBodyLineHeightRatio": thresholds["min_body_line_height_ratio"],
                    "minParagraphSpacingRatio": thresholds["min_paragraph_spacing_ratio"],
                },
            }
        )

    if meta.get("candidateCount", 0) > 0:
        flags.append(
            {
                "severity": "fail",
                "code": "meta_leakage_candidate",
                "message": "Learner-facing body appears to contain provenance or process narration.",
                "actual": meta.get("candidates"),
            }
        )

    if container_text_overflow.get("count", 0) > 0:
        flags.append(
            {
                "severity": "fail",
                "code": "inner_container_text_overflow",
                "message": "Text overflows or is clipped inside one or more containers even though the page block may still fit.",
                "actual": container_text_overflow.get("items"),
            }
        )

    if svg_visual_enclosure.get("count", 0) > 0:
        flags.append(
            {
                "severity": "fail",
                "code": "svg_visual_enclosure_failure",
                "message": "An SVG diagram uses a visual frame/card that does not enclose its own pills, labels, or content.",
                "actual": svg_visual_enclosure.get("items"),
            }
        )

    if screenshot.get("visibleSheetCount") != 1:
        flags.append(
            {
                "severity": "fail",
                "code": "page_isolation_failed",
                "message": "The page query did not isolate a single visible sheet.",
            }
        )

    if not pdf_screenshot:
        flags.append(
            {
                "severity": "fail",
                "code": "pdf_page_capture_missing",
                "message": "No rendered PDF page screenshot was available for this page.",
            }
        )
    elif not pdf_screenshot.get("usesA4Aspect", False):
        flags.append(
            {
                "severity": "fail",
                "code": "pdf_page_not_a4",
                "message": "The rendered PDF page screenshot does not preserve an A4-like aspect ratio.",
            }
        )

    if not parity:
        flags.append(
            {
                "severity": "fail",
                "code": "pdf_parity_missing",
                "message": "No HTML-vs-PDF parity metadata was generated for this page.",
            }
        )
    else:
        if parity.get("sameDimensions") is False:
            flags.append(
                {
                    "severity": "warn",
                    "code": "pdf_dimension_drift",
                    "message": "HTML and PDF screenshots were rendered at noticeably different dimensions.",
                }
            )
        if (parity.get("visualDiffScore") or 0) > 0.035:
            flags.append(
                {
                    "severity": "warn",
                    "code": "pdf_visual_drift",
                    "message": "Rendered PDF page appears visually different from the HTML page screenshot.",
                    "actual": parity.get("visualDiffScore"),
                    "threshold": 0.035,
                }
            )

    return flags


def build_subagent_prompt(page_packet: dict[str, Any]) -> str:
    return build_subagent_prompt_with_language(page_packet, review_language="en")


def detect_review_language(html_path: Path, requested_language: str) -> str:
    if requested_language in {"en", "zh"}:
        return requested_language

    text = html_path.read_text(encoding="utf-8", errors="ignore")
    stripped = re.sub(r"<[^>]+>", " ", text)
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", stripped))
    latin_count = len(re.findall(r"[A-Za-z]", stripped))
    return "zh" if cjk_count >= 24 and cjk_count * 2 >= max(latin_count, 1) else "en"


def build_subagent_prompt_with_language(
    page_packet: dict[str, Any],
    review_language: str,
) -> str:
    page_number = page_packet["page"]
    html_screenshot_path = page_packet["htmlScreenshot"]
    pdf_screenshot_path = page_packet["pdfScreenshot"]
    parity = page_packet.get("parity") or {}
    flags = page_packet["heuristicFlags"]
    heuristic_summary = "none" if not flags else ", ".join(
        f"{flag['severity']}:{flag['code']}" for flag in flags
    )

    if review_language == "zh":
        return (
            "REQUIRED: 你是逐页审版子代理，不是负责改稿的主代理。\n"
            "不要编辑文件。不要重写整份讲义。不要审查其他页面。\n"
            f"请审查这份 print-first 教学讲义的第 {page_number} 页。\n"
            f"HTML 截图: {html_screenshot_path}\n"
            f"PDF 截图: {pdf_screenshot_path}\n"
            f"Heuristic flags: {heuristic_summary}\n\n"
            "请对比 HTML 单页截图与 PDF 单页截图。\n"
            f"参考 visual diff score: {parity.get('visualDiffScore')}\n\n"
            "判断该页是否通过 print-review gate。\n"
            "只返回 JSON，键名必须是: page, pass, issues, fixes。\n"
            "每个 issue 必须包含: type, severity, evidence, fix。\n"
            "审查范围:\n"
            "- 如果正文混入任何来源说明、过程说明、topic 标签、打印说明等元信息，判失败；不要只盯具体示例。\n"
            "- 如果图太小、图中文字溢出、或图只起装饰作用，判失败。\n"
            "- 如果页面下半部分出现明显大面积空白且没有明确的整页构图理由，判失败。\n"
            "- 如果页面依赖密集小卡片网格、dashboard 式盒子墙或微缩文字盒子，判失败。\n"
            "- 如果为了塞进页面而明显压缩字号、行距或段距，导致排版节奏失衡，判失败。\n"
            "- 如果层级更像网页 hero 或 dashboard，而不是学习讲义，判失败。\n"
            "- 如果图、callout、表格、代码块被裁切、拆坏或明显拥挤，判失败。\n"
            "- 如果 SVG 图中的外框、卡片或分组边框没有把它声称包含的文字、pill、图标或子框完整包住，判失败。\n"
            "- 如果任何 panel、callout、表格单元格、代码块、标签或网格子项内部的文字在容器内左右/上下溢出、被裁切、或只能靠隐藏 overflow 通过页面边界检查，判失败。\n"
            "- 如果 PDF 相比 HTML 出现布局、间距、缩放、裁切或内容缺失变化，判失败。\n"
            "- 如果标题、示例、caption、正文之间缺少清晰教学层级，判失败。\n"
            "- issue 必须具体、只针对当前页。\n"
            "- 优先建议重排内容、合并或拆分区块、放大教学图、改成表格/worked example、或在相邻页之间重新分配内容。\n"
            "- 不要把缩小字号、压缩行距或段距当作首选修复。\n"
            "- fixes 必须说明当前页要怎么改，且必须在审查第 "
            f"{page_number + 1} 页之前完成。"
        )

    return (
        "REQUIRED: You are a page-review subagent, not the editing agent.\n"
        "Do not edit files. Do not rewrite the handout. Do not review any other page.\n"
        f"Review page {page_number} of a print-first teaching handout.\n"
        f"HTML screenshot: {html_screenshot_path}\n"
        f"PDF screenshot: {pdf_screenshot_path}\n"
        f"Heuristic flags: {heuristic_summary}\n\n"
        "Compare the HTML page screenshot against the PDF page screenshot.\n"
        f"Advisory visual diff score: {parity.get('visualDiffScore')}\n\n"
        "Decide whether this single page passes the print-review gate.\n"
        "Return only JSON with keys: page, pass, issues, fixes.\n"
        "Each issue must include: type, severity, evidence, fix.\n"
        "Review scope:\n"
        "- Fail if body text contains any provenance or process chrome such as print instructions, topic labels, source notes, or workflow narration.\n"
        "- Fail if a diagram is too small to read, text in a diagram overflows, or the diagram works only as decoration.\n"
        "- Fail if the page leaves a large empty lower region without a deliberate full-page composition reason.\n"
        "- Fail if the page depends on dense small-card grids, dashboard-like box walls, or microtext boxes.\n"
        "- Fail if spacing, line height, or body text size appears compressed just to force the page to fit.\n"
        "- Fail if visual hierarchy feels like a web hero or dashboard rather than a study handout.\n"
        "- Fail if figures, callouts, tables, or code blocks are clipped, awkwardly split, or visually cramped.\n"
        "- Fail if an SVG diagram's outer frame, card, or grouped border does not visually enclose the text, pills, icons, or child boxes it claims to contain.\n"
        "- Fail if text inside any panel, callout, table cell, code block, tag, or grid item overflows horizontally or vertically, is clipped inside its own container, or only passes page-boundary checks because overflow is hidden.\n"
        "- Fail if the PDF export changes layout, spacing, scaling, clipping, or missing content compared with the HTML page.\n"
        "- Fail if headings, examples, captions, and body text do not form a clear teaching hierarchy.\n"
        "- Issues must be concrete and page-local.\n"
        "- Prefer fixes that rebalance content, merge or split blocks, or enlarge teaching visuals.\n"
        "- Do not suggest shrinking font size, line height, or paragraph spacing as the primary fix.\n"
        "- Fixes must describe how to change layout/content for this page before page "
        f"{page_number + 1} is reviewed."
    )


def write_subagent_prompt_file(
    review_dir: Path,
    page_number: int,
    prompt: str,
) -> Path:
    prompt_path = review_dir / f"page-{page_number:02d}-subagent-prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def write_review_packets(
    report: dict[str, Any],
    report_path: Path,
    review_dir: Path,
    thresholds: dict[str, float],
    review_language: str,
) -> Path:
    review_dir.mkdir(parents=True, exist_ok=True)

    screenshot_index = {
        item["page"]: item for item in report["screenshots"]["pages"]
    }
    pdf_screenshot_index = {
        item["page"]: item for item in report.get("pdf", {}).get("screenshots", {}).get("pages", [])
    }
    parity_index = {
        item["page"]: item for item in report.get("parity", {}).get("pages", [])
    }

    pages: list[dict[str, Any]] = []
    for page in report["analysis"]["sheets"]:
        page_number = int(page["page"])
        screenshot = screenshot_index[page_number]
        pdf_screenshot = pdf_screenshot_index.get(page_number)
        parity = parity_index.get(page_number)
        flags = build_flags(page, thresholds, screenshot, pdf_screenshot, parity)
        subagent_prompt = build_subagent_prompt_with_language(
            {
                "page": page_number,
                "htmlScreenshot": screenshot["path"],
                "pdfScreenshot": pdf_screenshot["path"] if pdf_screenshot else None,
                "parity": parity,
                "heuristicFlags": flags,
            },
            review_language=review_language,
        )
        subagent_prompt_path = write_subagent_prompt_file(
            review_dir,
            page_number,
            subagent_prompt,
        )
        packet = {
            "page": page_number,
            "screenshot": screenshot["path"],
            "htmlScreenshot": screenshot["path"],
            "pdfScreenshot": pdf_screenshot["path"] if pdf_screenshot else None,
            "metrics": {
                "overflow": page.get("overflow"),
                "issueCount": page.get("issueCount"),
                "density": page.get("density"),
                "figures": page.get("figures"),
                "cards": page.get("cards"),
                "typography": page.get("typography"),
                "meta": page.get("meta"),
                "containerTextOverflow": page.get("containerTextOverflow"),
                "svgVisualEnclosure": page.get("svgVisualEnclosure"),
            },
            "pdfMetrics": pdf_screenshot,
            "parity": parity,
            "heuristicFlags": flags,
            "heuristicPass": not any(flag["severity"] == "fail" for flag in flags),
            "subagentRequired": True,
            "subagentPromptPath": str(subagent_prompt_path),
            "subagentPrompt": subagent_prompt,
        }
        pages.append(packet)
        packet_path = review_dir / f"page-{page_number:02d}-review.json"
        packet_path.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    manifest = {
        "htmlPath": report["htmlPath"],
        "validationReport": str(report_path),
        "reviewMode": "sequential-page-gate",
        "reviewLanguage": review_language,
        "subagentRequired": True,
        "nextPageToReview": pages[0]["page"] if pages else None,
        "mainAgentRule": "The main agent must not self-approve a page. It edits only after a page-review subagent returns structured feedback.",
        "instructions": [
            "STOP before any self-review: spawn/call one fresh page-review subagent for the current page.",
            "Review page 1 first.",
            "Do not review page N+1 until page N is fixed and revalidated.",
            "A page passes only when heuristics pass and the page-review subagent returns pass=true.",
            "If no subagent tool is available, report the review as blocked instead of self-approving.",
            "After any page edit, rerun validate_print_layout.py and regenerate this review packet before continuing.",
        ],
        "thresholds": thresholds,
        "pages": pages,
    }
    manifest_path = review_dir / "page-review-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path


def main() -> int:
    args = parse_args()
    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        raise SystemExit(f"HTML file does not exist: {html_path}")

    prefix = args.prefix or html_path.stem
    report_path = run_validation(args, html_path, prefix)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    output_dir = Path(report["outputDir"])
    review_dir = (
        Path(args.review_dir).expanduser().resolve()
        if args.review_dir
        else output_dir / "page-review"
    )

    thresholds = {
        "max_bottom_gap_ratio": args.max_bottom_gap_ratio,
        "min_content_height_ratio": args.min_content_height_ratio,
        "min_figure_width_ratio": args.min_figure_width_ratio,
        "min_figure_area_ratio": args.min_figure_area_ratio,
        "max_card_grid_count": args.max_card_grid_count,
        "max_card_area_ratio": args.max_card_area_ratio,
        "min_card_text_size_px": args.min_card_text_size_px,
        "min_body_font_size_px": args.min_body_font_size_px,
        "min_body_line_height_ratio": args.min_body_line_height_ratio,
        "min_paragraph_spacing_ratio": args.min_paragraph_spacing_ratio,
    }

    review_language = detect_review_language(html_path, args.review_language)
    manifest_path = write_review_packets(
        report,
        report_path,
        review_dir,
        thresholds,
        review_language=review_language,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    failing_pages = [
        page["page"]
        for page in manifest["pages"]
        if page["heuristicPass"] is False
    ]

    print(f"Validation report: {report_path}")
    print(f"Review manifest: {manifest_path}")
    print(f"Pages queued: {len(manifest['pages'])}")
    print(f"Review language: {manifest['reviewLanguage']}")
    if manifest["pages"]:
        first_page = manifest["pages"][0]
        print(
            "Next required action: spawn one page-review subagent with "
            f"{first_page['subagentPromptPath']}"
        )
    if failing_pages:
        print(f"Heuristic review required: {', '.join(str(page) for page in failing_pages)}")
    else:
        print("Heuristics passed on all pages; continue with subagent visual review in order.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
