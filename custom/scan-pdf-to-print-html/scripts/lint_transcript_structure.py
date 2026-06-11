#!/usr/bin/env python3
"""Lint transcript heading structure before HTML assembly."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PAGE_MARKER_PATTERN = re.compile(r"^##\s+Page\s+(\d+)\s*$")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
TITLE_LIKE_PATTERN = re.compile(
    r"^(?:"
    r"第[0-9一二三四五六七八九十]+[章节部分]"
    r"|[0-9]+[、.．]"
    r"|[一二三四五六七八九十]+[、.．]"
    r"|（[0-9一二三四五六七八九十]+）"
    r"|例\s*[0-9一二三四五六七八九十]+"
    r"|知识(?:点|盒|清单|模块)[0-9一二三四五六七八九十]*"
    r")"
)
SUSPICIOUS_TITLE_PREFIX_PATTERN = re.compile(
    r"^(?:知识(?:点|盒|清单|模块)|例\s*[0-9一二三四五六七八九十]+|练习|小结|方法|定理|性质|判定|定义)"
)
CHINESE_DIGIT_MAP = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", help="Job directory containing job.json and source-transcript.md")
    parser.add_argument("--md", help="Optional explicit transcript path")
    return parser


def read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_transcript_path(job_dir: Path | None, explicit_md: str | None) -> Path:
    if explicit_md:
        return Path(explicit_md).expanduser().resolve()
    if job_dir is None:
        raise SystemExit("Provide --job-dir or --md.")
    return (job_dir / "source-transcript.md").resolve()


def normalize_job_dir(job_dir: str | None) -> Path | None:
    if not job_dir:
        return None
    return Path(job_dir).expanduser().resolve()


def line_is_structural_noise(stripped: str) -> bool:
    if not stripped:
        return True
    if stripped.startswith((">", "-", "* ", "|", "![", "<!--", "```", "~~~", "`", "<", "[")):
        return True
    if stripped.startswith(("解析：", "解析:", "图 ", "Figure ")):
        return True
    return False


def looks_like_title_paragraph(stripped: str) -> bool:
    if line_is_structural_noise(stripped):
        return False
    if len(stripped) > 36:
        return False
    if stripped.endswith(("。", "！", "？", "；", ";", ":", "：", ".")):
        return False
    if TITLE_LIKE_PATTERN.match(stripped):
        return True
    return bool(SUSPICIOUS_TITLE_PREFIX_PATTERN.match(stripped))


def chinese_ordinal_to_int(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    if value == "十":
        return 10
    if value.startswith("十") and len(value) == 2 and value[1] in CHINESE_DIGIT_MAP:
        return 10 + CHINESE_DIGIT_MAP[value[1]]
    if value.endswith("十") and len(value) == 2 and value[0] in CHINESE_DIGIT_MAP:
        return CHINESE_DIGIT_MAP[value[0]] * 10
    if len(value) == 3 and value[1] == "十" and value[0] in CHINESE_DIGIT_MAP and value[2] in CHINESE_DIGIT_MAP:
        return CHINESE_DIGIT_MAP[value[0]] * 10 + CHINESE_DIGIT_MAP[value[2]]
    if len(value) == 1:
        return CHINESE_DIGIT_MAP.get(value)
    return None


def extract_leading_ordinal(text: str) -> int | None:
    stripped = text.strip()
    for pattern in (
        re.compile(r"^(?P<num>\d+)[、.．]"),
        re.compile(r"^(?P<num>[一二三四五六七八九十]+)[、.．]"),
        re.compile(r"^（(?P<num>\d+|[一二三四五六七八九十]+)）"),
        re.compile(r"^第(?P<num>\d+|[一二三四五六七八九十]+)[章节部分]"),
        re.compile(r"^例\s*(?P<num>\d+|[一二三四五六七八九十]+)"),
        re.compile(r"^知识(?:点|盒|清单|模块)(?P<num>\d+|[一二三四五六七八九十]+)"),
    ):
        match = pattern.match(stripped)
        if not match:
            continue
        return chinese_ordinal_to_int(match.group("num"))
    return None


def lint_transcript(markdown_text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    lines = markdown_text.splitlines()
    in_code_fence = False
    current_page = "?"
    previous_content_heading_level: int | None = None
    saw_first_content_heading = False
    checked_first_numbered_heading = False

    for index, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue

        page_match = PAGE_MARKER_PATTERN.match(stripped)
        if page_match:
            current_page = page_match.group(1)
            previous_content_heading_level = None
            saw_first_content_heading = False
            checked_first_numbered_heading = False
            continue

        heading_match = HEADING_PATTERN.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            if level == 1 and heading_text == "Source Transcript":
                continue

            if not saw_first_content_heading:
                saw_first_content_heading = True
                if level > 3:
                    errors.append(
                        f"Page {current_page}: first content heading should start at ###, found H{level}: {heading_text}"
                    )

            if previous_content_heading_level is not None and level > previous_content_heading_level + 1:
                errors.append(
                    f"Page {current_page}: heading level jumps from H{previous_content_heading_level} to H{level}: {heading_text}"
                )

            previous_content_heading_level = level
            if not checked_first_numbered_heading:
                checked_first_numbered_heading = True
                ordinal = extract_leading_ordinal(heading_text)
                if ordinal is not None and ordinal != 1:
                    warnings.append(
                        f"Page {current_page}: first numbered heading starts at {ordinal}, verify no earlier heading was lost: {heading_text}"
                    )
            continue

        prev_blank = index == 0 or not lines[index - 1].strip()
        next_blank = index == len(lines) - 1 or not lines[index + 1].strip()
        if prev_blank and next_blank and looks_like_title_paragraph(stripped):
            warnings.append(
                f"Page {current_page}: title-like paragraph may need heading markup: {stripped}"
            )

    return errors, warnings


def update_job_status(job_dir: Path | None, status: str) -> None:
    if job_dir is None:
        return
    job_path = job_dir / "job.json"
    if not job_path.exists():
        return
    payload = read_json(job_path)
    payload["transcript_structure_lint_status"] = status
    write_json(job_path, payload)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_dir = normalize_job_dir(args.job_dir)
    md_path = resolve_transcript_path(job_dir, args.md)
    if not md_path.exists():
        raise SystemExit(f"Transcript not found: {md_path}")

    errors, warnings = lint_transcript(md_path.read_text(encoding="utf-8"))

    if errors:
        update_job_status(job_dir, "failed")
        for message in errors:
            print(f"FAIL: {message}")
        for message in warnings:
            print(f"WARN: {message}")
        return 1

    status = "passed-with-warnings" if warnings else "passed"
    update_job_status(job_dir, status)
    for message in warnings:
        print(f"WARN: {message}")
    print(f"OK: transcript structure {status} for {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
