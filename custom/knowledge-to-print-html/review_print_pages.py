from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a sequential page-review packet for print handouts."
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

    subprocess.run(command, check=True)

    output_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else html_path.parent / "screens" / "py-latest"
    return output_dir / f"{prefix}-validation-report.json"


def build_flags(
    page: dict[str, Any],
    thresholds: dict[str, float],
    screenshot: dict[str, Any],
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    density = page.get("density") or {}
    figures = page.get("figures") or {}
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

    if screenshot.get("visibleSheetCount") != 1:
        flags.append(
            {
                "severity": "fail",
                "code": "page_isolation_failed",
                "message": "The page query did not isolate a single visible sheet.",
            }
        )

    return flags


def build_subagent_prompt(page_packet: dict[str, Any]) -> str:
    page_number = page_packet["page"]
    screenshot_path = page_packet["screenshot"]
    flags = page_packet["heuristicFlags"]
    heuristic_summary = "none" if not flags else ", ".join(
        f"{flag['severity']}:{flag['code']}" for flag in flags
    )

    return (
        "REQUIRED: You are a page-review subagent, not the editing agent.\n"
        "Do not edit files. Do not rewrite the handout. Do not review any other page.\n"
        f"Review page {page_number} of a print-first teaching handout.\n"
        f"Screenshot: {screenshot_path}\n"
        f"Heuristic flags: {heuristic_summary}\n\n"
        "Decide whether this single page passes the print-review gate.\n"
        "Return only JSON with keys: page, pass, issues, fixes.\n"
        "Each issue must include: type, severity, evidence, fix.\n"
        "Review scope:\n"
        "- Fail if body text contains meta/process chrome such as print instructions, topic labels, provenance notes, or workflow narration.\n"
        "- Fail if a diagram is too small to read, text in a diagram overflows, or the diagram works only as decoration.\n"
        "- Fail if the page leaves a large empty lower region without a deliberate full-page composition reason.\n"
        "- Fail if visual hierarchy feels like a web hero or dashboard rather than a study handout.\n"
        "- Fail if figures, callouts, tables, or code blocks are clipped, awkwardly split, or visually cramped.\n"
        "- Fail if headings, examples, captions, and body text do not form a clear teaching hierarchy.\n"
        "- Issues must be concrete and page-local.\n"
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
) -> Path:
    review_dir.mkdir(parents=True, exist_ok=True)

    screenshot_index = {
        item["page"]: item for item in report["screenshots"]["pages"]
    }

    pages: list[dict[str, Any]] = []
    for page in report["analysis"]["sheets"]:
        page_number = int(page["page"])
        screenshot = screenshot_index[page_number]
        flags = build_flags(page, thresholds, screenshot)
        subagent_prompt = build_subagent_prompt(
            {
                "page": page_number,
                "screenshot": screenshot["path"],
                "heuristicFlags": flags,
            }
        )
        subagent_prompt_path = write_subagent_prompt_file(
            review_dir,
            page_number,
            subagent_prompt,
        )
        packet = {
            "page": page_number,
            "screenshot": screenshot["path"],
            "metrics": {
                "overflow": page.get("overflow"),
                "issueCount": page.get("issueCount"),
                "density": page.get("density"),
                "figures": page.get("figures"),
            },
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
    }

    manifest_path = write_review_packets(report, report_path, review_dir, thresholds)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    failing_pages = [
        page["page"]
        for page in manifest["pages"]
        if page["heuristicPass"] is False
    ]

    print(f"Validation report: {report_path}")
    print(f"Review manifest: {manifest_path}")
    print(f"Pages queued: {len(manifest['pages'])}")
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
