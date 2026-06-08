#!/usr/bin/env python3
"""Validate the minimal working contract for a scan job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FILES = ("job.json", "source-transcript.md", "layout-brief.md", "handoff-notes.md")
REQUIRED_PAGE_DIRS = ("pages", "pages-clean")
REQUIRED_DOC2X_FILES = (
    "doc2x/preupload.json",
    "doc2x/parse-status.json",
    "doc2x/parse-result.json",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir", help="Job directory to validate")
    parser.add_argument("--require-html", action="store_true", help="Require handout.html to exist")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    job_dir = Path(args.job_dir).expanduser().resolve()
    failures: list[str] = []

    if not job_dir.exists():
        raise SystemExit(f"Job directory not found: {job_dir}")

    for file_name in REQUIRED_FILES:
        if not (job_dir / file_name).exists():
            failures.append(f"Missing file: {file_name}")

    job_json_path = job_dir / "job.json"
    job_payload: dict[str, object] = {}
    if job_json_path.exists():
        try:
            job_payload = json.loads(job_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"Invalid job.json: {exc}")

    ocr_backend = str(job_payload.get("ocr_backend", "")).strip().lower()
    render_pages = bool(job_payload.get("render_pages"))

    if ocr_backend == "doc2x":
        for relative_path in REQUIRED_DOC2X_FILES:
            if not (job_dir / relative_path).exists():
                failures.append(f"Missing Doc2X artifact: {relative_path}")
        if job_payload.get("export_format") and not (job_dir / "doc2x/export-result.json").exists():
            failures.append("Missing Doc2X artifact: doc2x/export-result.json")
    else:
        render_pages = True

    if render_pages:
        for dir_name in REQUIRED_PAGE_DIRS:
            if not (job_dir / dir_name).is_dir():
                failures.append(f"Missing directory: {dir_name}")
        page_images = sorted((job_dir / "pages").glob("page-*.png"))
        if not page_images:
            failures.append("No rendered page images found in pages/")
        manifest_path = job_dir / "pages" / "manifest.json"
        if manifest_path.exists():
            try:
                json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(f"Invalid JSON manifest: {exc}")
        else:
            failures.append("Missing pages/manifest.json")

    if args.require_html and not (job_dir / "handout.html").exists():
        failures.append("Missing handout.html")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"OK: validated scan job at {job_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
