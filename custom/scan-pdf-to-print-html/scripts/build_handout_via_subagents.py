#!/usr/bin/env python3
"""Prepare and assemble a local fragment-based handout build manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from build_faithful_handout_html import (
    build_html_document_from_fragments,
    default_title,
    split_pages,
)


MANIFEST_NAME = "html-build-manifest.json"
PARTS_DIR_NAME = "handout-parts"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="phase", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare or refresh the fragment manifest")
    prepare.add_argument("--job-dir", required=True, help="Job directory")
    prepare.add_argument("--pages", help='Optional page subset such as "1-3,7"')
    prepare.add_argument("--resume", action="store_true", help="Keep only pages without success in pending_pages")
    prepare.add_argument("--title", help="Optional output title override")
    prepare.add_argument("--source-label", default="OCR Transcript", help="Header label for the final shell")

    status = subparsers.add_parser("status", help="Refresh manifest statuses from page meta files")
    status.add_argument("--job-dir", required=True, help="Job directory")

    assemble = subparsers.add_parser("assemble", help="Assemble handout.html from successful fragments")
    assemble.add_argument("--job-dir", required=True, help="Job directory")
    assemble.add_argument("--out-html", help="Optional output HTML path override")
    return parser


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_job_payload(job_dir: Path) -> dict[str, object]:
    job_path = job_dir / "job.json"
    if not job_path.exists():
        raise SystemExit(f"Missing job.json: {job_path}")
    payload = read_json(job_path)
    if not isinstance(payload, dict):
        raise SystemExit(f"Invalid job.json payload: {job_path}")
    return payload


def save_job_payload(job_dir: Path, job_payload: dict[str, object]) -> None:
    job_payload["html_builder"] = "subagent-orchestrated"
    write_json(job_dir / "job.json", job_payload)


def manifest_path(job_dir: Path) -> Path:
    return job_dir / MANIFEST_NAME


def parts_dir(job_dir: Path) -> Path:
    return job_dir / PARTS_DIR_NAME


def relative_part_path(page_number: int, suffix: str) -> str:
    return f"{PARTS_DIR_NAME}/page-{page_number:04d}.{suffix}"


def resolve_job_path(job_dir: Path, path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return job_dir / candidate


def compute_source_fingerprint(page_number: int, page_content: str) -> str:
    payload = f"{page_number}\n{page_content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def invalidate_page_artifacts(job_dir: Path, page_number: int) -> None:
    for suffix in ("fragment.html", "meta.json", "error.txt"):
        artifact_path = resolve_job_path(job_dir, relative_part_path(page_number, suffix))
        artifact_path.unlink(missing_ok=True)


def parse_page_selection(selection: str | None, available_pages: list[int]) -> list[int]:
    if not available_pages:
        raise ValueError("No pages available in source transcript")
    if not selection:
        return available_pages[:]

    chosen: list[int] = []
    available = set(available_pages)
    for chunk in selection.split(","):
        piece = chunk.strip()
        if not piece:
            continue
        if "-" in piece:
            start_text, end_text = piece.split("-", 1)
            try:
                start = int(start_text)
                end = int(end_text)
            except ValueError as exc:
                raise ValueError(f"Invalid page selection: {selection}") from exc
            if start > end:
                raise ValueError(f"Invalid page selection: {selection}")
            for page_number in range(start, end + 1):
                if page_number not in available:
                    raise ValueError(f"Invalid page selection: {selection}")
                chosen.append(page_number)
            continue
        try:
            page_number = int(piece)
        except ValueError as exc:
            raise ValueError(f"Invalid page selection: {selection}") from exc
        if page_number not in available:
            raise ValueError(f"Invalid page selection: {selection}")
        chosen.append(page_number)

    unique_pages: list[int] = []
    seen: set[int] = set()
    for page_number in chosen:
        if page_number not in seen:
            unique_pages.append(page_number)
            seen.add(page_number)
    return unique_pages


def read_transcript_pages(job_dir: Path) -> list[tuple[int, str]]:
    transcript_path = job_dir / "source-transcript.md"
    if not transcript_path.exists():
        raise SystemExit(f"Missing source-transcript.md: {transcript_path}")
    pages = split_pages(transcript_path.read_text(encoding="utf-8"))
    parsed_pages: list[tuple[int, str]] = []
    for page_number, content in pages:
        parsed_pages.append((int(page_number), content))
    return parsed_pages


def page_meta_status(meta_path: Path, expected_source_fingerprint: str) -> str:
    if not meta_path.exists():
        return "pending"
    try:
        payload = read_json(meta_path)
    except json.JSONDecodeError:
        return "pending"
    if not isinstance(payload, dict):
        return "pending"
    status = str(payload.get("status", "pending")).strip().lower()
    status = status or "pending"
    if status == "success":
        fingerprint = str(payload.get("source_fingerprint", "")).strip()
        if not fingerprint or fingerprint != expected_source_fingerprint:
            return "pending"
    return status


def refresh_manifest_statuses(job_dir: Path, manifest: dict[str, object]) -> dict[str, object]:
    page_entries = manifest.get("pages")
    if not isinstance(page_entries, list):
        raise SystemExit("Manifest pages list is missing or invalid")

    pending_pages: list[int] = []
    for page_entry in page_entries:
        if not isinstance(page_entry, dict):
            raise SystemExit("Manifest page entry is invalid")
        meta_path_value = page_entry.get("meta_path")
        page_number = int(page_entry["page_number"])
        source_fingerprint = str(page_entry.get("source_fingerprint", "")).strip()
        status = page_meta_status(resolve_job_path(job_dir, str(meta_path_value)), source_fingerprint)
        page_entry["status"] = status
        if status != "success":
            pending_pages.append(page_number)

    manifest["pending_pages"] = pending_pages
    return manifest


def command_prepare(args: argparse.Namespace) -> int:
    job_dir = Path(args.job_dir).expanduser().resolve()
    job_payload = load_job_payload(job_dir)
    job_payload.pop("handout_html", None)
    transcript_pages = read_transcript_pages(job_dir)
    available_pages = [page_number for page_number, _content in transcript_pages]
    try:
        selected_pages = parse_page_selection(args.pages, available_pages)
    except ValueError as exc:
        raise SystemExit(str(exc))

    page_lookup = {page_number: content for page_number, content in transcript_pages}
    selected_page_pairs = [(str(page_number), page_lookup[page_number]) for page_number in selected_pages]
    title = default_title(selected_page_pairs, args.title)

    parts_directory = parts_dir(job_dir)
    parts_directory.mkdir(parents=True, exist_ok=True)

    page_entries: list[dict[str, object]] = []
    pending_pages: list[int] = []
    for page_number in selected_pages:
        page_content = page_lookup[page_number]
        source_fingerprint = compute_source_fingerprint(page_number, page_content)
        fragment_path = relative_part_path(page_number, "fragment.html")
        meta_path = relative_part_path(page_number, "meta.json")
        if args.resume:
            status = page_meta_status(resolve_job_path(job_dir, meta_path), source_fingerprint)
        else:
            invalidate_page_artifacts(job_dir, page_number)
            status = "pending"
        page_entries.append(
            {
                "page_number": page_number,
                "fragment_path": fragment_path,
                "meta_path": meta_path,
                "source_fingerprint": source_fingerprint,
                "status": status,
            }
        )
        if not args.resume or status != "success":
            pending_pages.append(page_number)

    manifest = {
        "title": title,
        "source_label": args.source_label,
        "page_count": len(selected_pages),
        "parts_dir": PARTS_DIR_NAME,
        "final_html_path": "handout.html",
        "selected_pages": selected_pages,
        "pending_pages": pending_pages,
        "pages": page_entries,
        "assembly": {"status": "pending"},
    }
    write_json(manifest_path(job_dir), manifest)

    save_job_payload(job_dir, job_payload)
    print(str(manifest_path(job_dir)))
    return 0


def command_status(args: argparse.Namespace) -> int:
    job_dir = Path(args.job_dir).expanduser().resolve()
    path = manifest_path(job_dir)
    if not path.exists():
        raise SystemExit(f"Missing manifest: {path}")
    manifest = read_json(path)
    if not isinstance(manifest, dict):
        raise SystemExit(f"Invalid manifest: {path}")
    refresh_manifest_statuses(job_dir, manifest)
    write_json(path, manifest)
    print(str(path))
    return 0


def command_assemble(args: argparse.Namespace) -> int:
    job_dir = Path(args.job_dir).expanduser().resolve()
    path = manifest_path(job_dir)
    if not path.exists():
        raise SystemExit(f"Missing manifest: {path}")
    manifest = read_json(path)
    if not isinstance(manifest, dict):
        raise SystemExit(f"Invalid manifest: {path}")
    refresh_manifest_statuses(job_dir, manifest)

    page_entries = manifest.get("pages")
    if not isinstance(page_entries, list):
        raise SystemExit("Manifest pages list is missing or invalid")

    failed_or_pending = [entry for entry in page_entries if isinstance(entry, dict) and entry.get("status") != "success"]
    if failed_or_pending:
        raise SystemExit("Not all pages are successful; refusing to assemble final HTML.")

    fragments: list[tuple[str, str]] = []
    for page_entry in page_entries:
        if not isinstance(page_entry, dict):
            raise SystemExit("Manifest page entry is invalid")
        fragment_path = resolve_job_path(job_dir, str(page_entry["fragment_path"]))
        if not fragment_path.exists():
            raise SystemExit(f"Missing fragment HTML: {fragment_path}")
        fragments.append((str(page_entry["page_number"]), fragment_path.read_text(encoding="utf-8")))

    job_payload = load_job_payload(job_dir)
    title = str(manifest.get("title") or "OCR Handout")
    source_label = str(manifest.get("source_label") or "OCR Transcript")
    out_html = Path(args.out_html).expanduser().resolve() if args.out_html else job_dir / "handout.html"
    html_document = build_html_document_from_fragments(fragments, title=title, source_label=source_label)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html_document, encoding="utf-8")

    manifest["final_html_path"] = str(out_html)
    manifest["assembly"] = {"status": "success", "output_html": str(out_html)}
    write_json(path, manifest)

    job_payload["handout_html"] = str(out_html)
    save_job_payload(job_dir, job_payload)
    print(str(out_html))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.phase == "prepare":
        return command_prepare(args)
    if args.phase == "status":
        return command_status(args)
    if args.phase == "assemble":
        return command_assemble(args)
    raise SystemExit(f"Unsupported phase: {args.phase}")


if __name__ == "__main__":
    raise SystemExit(main())
