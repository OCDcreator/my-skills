#!/usr/bin/env python3
"""Initialize a scan transcription job and render page images."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Input PDF path")
    parser.add_argument("--out-dir", required=True, help="Job output directory")
    parser.add_argument("--dpi", type=int, default=220, help="Render DPI (default: 220)")
    parser.add_argument("--pages", help='Optional 1-based page filter such as "1-3,7"')
    return parser


def write_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    job_dir = Path(args.out_dir).expanduser().resolve()
    pages_dir = job_dir / "pages"
    pages_clean_dir = job_dir / "pages-clean"
    diagrams_dir = job_dir / "diagrams"
    tables_dir = job_dir / "tables"

    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    for directory in (job_dir, pages_dir, pages_clean_dir, diagrams_dir, tables_dir):
        directory.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(Path(__file__).with_name("render_pdf_pages.py")),
        "--pdf",
        str(pdf_path),
        "--out-dir",
        str(pages_dir),
        "--dpi",
        str(args.dpi),
    ]
    if args.pages:
        command.extend(["--pages", args.pages])
    subprocess.run(command, check=True)

    job = {
        "source_pdf": str(pdf_path),
        "job_dir": str(job_dir),
        "dpi": args.dpi,
        "page_filter": args.pages or "",
    }
    write_file(job_dir / "job.json", json.dumps(job, ensure_ascii=False, indent=2) + "\n")
    write_file(job_dir / "source-transcript.md", "# Source Transcript\n\n## Page 1\n\n")
    write_file(
        job_dir / "layout-brief.md",
        "# Layout Brief\n\n- Paper size: A4\n- Goal: print-first faithful reproduction\n- Allowed changes: layout, typography, spacing, figure placement\n- Forbidden changes: rewriting or summarizing content\n",
    )
    write_file(
        job_dir / "handoff-notes.md",
        "# Handoff Notes\n\n- Record unreadable fragments here.\n- Record whether each figure was reused, cleaned, or redrawn.\n",
    )
    print(str(job_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
