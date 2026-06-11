#!/usr/bin/env python3
"""Validate the minimal working contract for a scan job."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from build_faithful_handout_html import validate_fragment_html


REQUIRED_FILES = ("job.json", "source-transcript.md", "layout-brief.md", "handoff-notes.md")
REQUIRED_DOC2X_FILES = (
    "doc2x/preupload.json",
    "doc2x/parse-status.json",
    "doc2x/parse-result.json",
)
SUBAGENT_HTML_BUILDER = "subagent-orchestrated"
HTML_TAG_PATTERN = re.compile(r"</?[a-zA-Z][\w:-]*(?:\s[^<>]*)?>")


def load_json_file(
    path: Path, failures: list[str], *, missing_label: str, invalid_label: str
) -> dict[str, object] | None:
    if not path.exists():
        failures.append(missing_label)
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"{invalid_label}: {exc}")
        return None

    if isinstance(payload, dict):
        return payload

    failures.append(f"{invalid_label}: expected a JSON object")
    return None


def path_is_within(parent_dir: Path, candidate_path: Path) -> bool:
    try:
        candidate_path.relative_to(parent_dir)
    except ValueError:
        return False
    return True


def resolve_job_path(job_dir: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = job_dir / candidate
    return candidate.resolve()


def validate_rendered_fragment(page_number: object, fragment_path: Path, failures: list[str]) -> None:
    fragment_html = fragment_path.read_text(encoding="utf-8")
    try:
        cleaned_fragment = validate_fragment_html(str(page_number), fragment_html)
    except ValueError as exc:
        failures.append(str(exc))
        return

    if not cleaned_fragment:
        failures.append(f"Fragment for page {page_number} is empty")
        return

    if not HTML_TAG_PATTERN.search(cleaned_fragment):
        failures.append(f"Fragment for page {page_number} does not look like rendered body HTML")


def validate_subagent_html_contract(job_dir: Path, failures: list[str]) -> Path | None:
    manifest_path = job_dir / "html-build-manifest.json"
    manifest = load_json_file(
        manifest_path,
        failures,
        missing_label="Missing html-build-manifest.json",
        invalid_label="Invalid html-build-manifest.json",
    )
    if manifest is None:
        return None

    parts_dir = (job_dir / "handout-parts").resolve()
    if not parts_dir.is_dir():
        failures.append("Missing directory: handout-parts")

    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        failures.append("Invalid html-build-manifest.json: pages must be a non-empty list")
        return None

    for index, page_payload in enumerate(pages, start=1):
        if not isinstance(page_payload, dict):
            failures.append(f"Invalid html-build-manifest.json: page entry {index} must be an object")
            continue

        page_number = page_payload.get("page_number", index)
        page_status = str(page_payload.get("status", "")).strip().lower()
        if page_status != "success":
            failures.append(f"Manifest page {page_number} is not successful: {page_status or 'missing'}")
            continue

        manifest_source_fingerprint = str(page_payload.get("source_fingerprint", "")).strip()
        if not manifest_source_fingerprint:
            failures.append(f"Manifest page {page_number} is missing source_fingerprint")

        for key, label in (("fragment_path", "fragment"), ("meta_path", "meta")):
            raw_path = str(page_payload.get(key, "")).strip()
            if not raw_path:
                failures.append(f"Manifest page {page_number} is missing {key}")
                continue
            resolved_path = resolve_job_path(job_dir, raw_path)
            if not path_is_within(parts_dir, resolved_path):
                failures.append(
                    f"Manifest page {page_number} {key} must resolve inside handout-parts: {resolved_path}"
                )
                continue
            if not resolved_path.exists():
                failures.append(f"Missing {label} for page {page_number}: {raw_path}")
                continue

            if key == "fragment_path":
                validate_rendered_fragment(page_number, resolved_path, failures)

            if key == "meta_path" and resolved_path.exists():
                meta_payload = load_json_file(
                    resolved_path,
                    failures,
                    missing_label=f"Missing meta for page {page_number}: {raw_path}",
                    invalid_label=f"Invalid meta for page {page_number}",
                )
                if meta_payload is None:
                    continue

                meta_status = str(meta_payload.get("status", "")).strip().lower()
                if meta_status != "success":
                    failures.append(f"Meta page {page_number} is not successful: {meta_status or 'missing'}")
                meta_page_number = str(meta_payload.get("page_number", "")).strip()
                manifest_page_number = str(page_number).strip()
                if meta_page_number != manifest_page_number:
                    failures.append(
                        f"Meta page_number {meta_page_number or 'missing'} does not match manifest page_number "
                        f"{manifest_page_number}"
                    )
                meta_source_fingerprint = str(meta_payload.get("source_fingerprint", "")).strip()
                if not meta_source_fingerprint:
                    failures.append(f"Meta page {page_number} is missing source_fingerprint")
                elif meta_source_fingerprint != manifest_source_fingerprint:
                    failures.append(
                        f"Meta page {page_number} source_fingerprint does not match manifest source_fingerprint: "
                        f"{meta_source_fingerprint} != {manifest_source_fingerprint}"
                    )

    assembly_payload = manifest.get("assembly")
    if not isinstance(assembly_payload, dict):
        failures.append("Invalid html-build-manifest.json: assembly must be an object")
        return None

    assembly_status = str(assembly_payload.get("status", "")).strip().lower()
    if assembly_status != "success":
        failures.append(f"Assembly is not successful: {assembly_status or 'missing'}")
        return None

    output_html_value = str(
        assembly_payload.get("output_html") or manifest.get("final_html_path") or ""
    ).strip()
    if not output_html_value:
        failures.append("Invalid html-build-manifest.json: missing assembly output_html or final_html_path")
        return None

    return resolve_job_path(job_dir, output_html_value)


def validate_body_crop_contract(job_dir: Path, failures: list[str]) -> None:
    pages_body_dir = job_dir / "pages-body"
    if not pages_body_dir.is_dir():
        failures.append("Missing directory: pages-body")

    manifest = load_json_file(
        pages_body_dir / "manifest.json",
        failures,
        missing_label="Missing pages-body/manifest.json",
        invalid_label="Invalid pages-body/manifest.json",
    )
    if manifest is None:
        return

    if not (job_dir / "doc2x" / "body-only.pdf").exists():
        failures.append("Missing Doc2X pre-crop artifact: doc2x/body-only.pdf")

    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        failures.append("Invalid pages-body/manifest.json: pages must be a non-empty list")
        return

    for index, page_payload in enumerate(pages, start=1):
        if not isinstance(page_payload, dict):
            failures.append(f"Invalid pages-body/manifest.json: page entry {index} must be an object")
            continue
        body_image_path = str(page_payload.get("body_image_path", "")).strip()
        if not body_image_path:
            failures.append(f"Invalid pages-body/manifest.json: page entry {index} missing body_image_path")
            continue
        resolved_image = resolve_job_path(job_dir, body_image_path)
        if not resolved_image.exists():
            failures.append(f"Missing body page image: {body_image_path}")


def validate_doc2x_transcript_contract(
    job_dir: Path,
    job_payload: dict[str, object],
    failures: list[str],
    *,
    require_audit_approval: bool,
) -> None:
    raw_transcript_path = str(job_payload.get("raw_transcript_path", "")).strip()
    canonical_transcript_path = str(job_payload.get("canonical_transcript_path", "")).strip()

    if not raw_transcript_path:
        failures.append("Missing raw_transcript_path in job.json")
    else:
        resolved_raw = resolve_job_path(job_dir, raw_transcript_path)
        if not resolved_raw.exists():
            failures.append(f"Missing raw transcript copy: {raw_transcript_path}")

    if not canonical_transcript_path:
        failures.append("Missing canonical_transcript_path in job.json")
    else:
        resolved_canonical = resolve_job_path(job_dir, canonical_transcript_path)
        if not resolved_canonical.exists():
            failures.append(f"Missing canonical transcript: {canonical_transcript_path}")

    audit_status = str(job_payload.get("transcript_audit_status", "")).strip().lower()
    if require_audit_approval and audit_status != "approved":
        failures.append(f"Transcript audit is not approved: {audit_status or 'missing'}")

    lint_status = str(job_payload.get("transcript_structure_lint_status", "")).strip().lower()
    if require_audit_approval and lint_status not in {"passed", "passed-with-warnings"}:
        failures.append(f"Transcript structure lint is not ready: {lint_status or 'missing'}")


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
    loaded_job_payload = load_json_file(
        job_json_path,
        failures,
        missing_label="Missing file: job.json",
        invalid_label="Invalid job.json",
    )
    job_payload = loaded_job_payload if loaded_job_payload is not None else {}
    if loaded_job_payload == {}:
        failures.append("Invalid job.json: expected a non-empty JSON object")

    ocr_backend = str(job_payload.get("ocr_backend", "")).strip().lower()
    render_pages = bool(job_payload.get("render_pages"))
    pre_crop_body = bool(job_payload.get("pre_crop_body"))
    html_builder = str(job_payload.get("html_builder", "")).strip().lower()

    if ocr_backend == "doc2x":
        for relative_path in REQUIRED_DOC2X_FILES:
            if not (job_dir / relative_path).exists():
                failures.append(f"Missing Doc2X artifact: {relative_path}")
        if job_payload.get("export_format") and not (job_dir / "doc2x/export-result.json").exists():
            failures.append("Missing Doc2X artifact: doc2x/export-result.json")
        validate_doc2x_transcript_contract(
            job_dir,
            job_payload,
            failures,
            require_audit_approval=args.require_html,
        )
    else:
        render_pages = True

    if pre_crop_body:
        render_pages = True
        validate_body_crop_contract(job_dir, failures)

    if render_pages:
        if not (job_dir / "pages").is_dir():
            failures.append("Missing directory: pages")
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

    if args.require_html:
        if html_builder == SUBAGENT_HTML_BUILDER:
            resolved_html_path = validate_subagent_html_contract(job_dir, failures)
            if resolved_html_path is not None and not resolved_html_path.exists():
                failures.append(f"Missing assembled HTML: {resolved_html_path}")
        elif not (job_dir / "handout.html").exists():
            failures.append("Missing handout.html")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"OK: validated scan job at {job_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
