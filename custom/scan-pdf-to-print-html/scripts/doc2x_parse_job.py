#!/usr/bin/env python3
"""Run a Doc2X-backed OCR job and materialize local job artifacts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests


DEFAULT_BASE_URL = "https://v2.doc2x.noedgeai.com"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, help="Input PDF path")
    parser.add_argument("--out-dir", required=True, help="Job output directory")
    parser.add_argument("--api-key", help="Doc2X API key. Defaults to DOC2X_API_KEY")
    parser.add_argument("--base-url", default=os.environ.get("DOC2X_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default="v3-2026", choices=("v2", "v3-2026"))
    parser.add_argument("--to", default="md", choices=("md", "tex", "docx"))
    parser.add_argument("--formula-mode", default="normal", choices=("normal", "dollar"))
    parser.add_argument("--formula-level", type=int, default=0, choices=(0, 1, 2))
    parser.add_argument("--merge-cross-page-forms", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=3.0)
    parser.add_argument("--timeout-seconds", type=float, default=1800.0)
    parser.add_argument("--filename", help="Optional export filename stem without extension")
    parser.add_argument("--skip-export", action="store_true", help="Keep page-level parse results only")
    parser.add_argument("--render-pages", action="store_true", help="Also render source pages locally for review")
    parser.add_argument("--render-dpi", type=int, default=260)
    return parser


def ensure_api_key(explicit_key: str | None) -> str:
    key = explicit_key or os.environ.get("DOC2X_API_KEY", "").strip()
    if key:
        return key
    raise SystemExit("Doc2X API key missing. Set DOC2X_API_KEY or pass --api-key.")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def request_json(method: str, url: str, *, headers: dict[str, str], **kwargs) -> dict[str, object]:
    response = requests.request(method, url, headers=headers, timeout=120, **kwargs)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "success":
        raise RuntimeError(f"Doc2X API error from {url}: {json.dumps(data, ensure_ascii=False)}")
    payload = data.get("data")
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected Doc2X payload from {url}: {json.dumps(data, ensure_ascii=False)}")
    return {"raw": data, "data": payload}


def preupload(pdf_path: Path, base_url: str, api_key: str, model: str) -> dict[str, object]:
    body = {"model": model} if model else {}
    result = request_json(
        "POST",
        f"{base_url}/api/v2/parse/preupload",
        headers=auth_headers(api_key),
        json=body,
    )
    data = result["data"]
    if "uid" not in data or "url" not in data:
        raise RuntimeError(f"Doc2X preupload response missing uid/url: {json.dumps(result['raw'], ensure_ascii=False)}")
    return result


def upload_file(pdf_path: Path, upload_url: str) -> None:
    with pdf_path.open("rb") as handle:
        response = requests.put(upload_url, data=handle, timeout=600)
    if response.status_code != 200:
        raise RuntimeError(f"Doc2X upload failed: {response.status_code} {response.text}")


def poll_parse_status(uid: str, base_url: str, api_key: str, poll_seconds: float, timeout_seconds: float) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = request_json(
            "GET",
            f"{base_url}/api/v2/parse/status",
            headers=auth_headers(api_key),
            params={"uid": uid},
        )
        data = result["data"]
        status = data.get("status")
        if status == "success":
            return result
        if status == "failed":
            raise RuntimeError(f"Doc2X parse failed: {data.get('detail', 'unknown error')}")
        time.sleep(poll_seconds)
    raise TimeoutError(f"Timed out waiting for Doc2X parse status for uid={uid}")


def trigger_export(
    uid: str,
    base_url: str,
    api_key: str,
    export_to: str,
    formula_mode: str,
    formula_level: int,
    merge_cross_page_forms: bool,
    filename: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "uid": uid,
        "to": export_to,
        "formula_mode": formula_mode,
        "formula_level": formula_level,
        "merge_cross_page_forms": merge_cross_page_forms,
    }
    if filename:
        payload["filename"] = filename
    return request_json(
        "POST",
        f"{base_url}/api/v2/convert/parse",
        headers={**auth_headers(api_key), "Content-Type": "application/json"},
        json=payload,
    )


def poll_export_status(uid: str, base_url: str, api_key: str, poll_seconds: float, timeout_seconds: float) -> dict[str, object]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = request_json(
            "GET",
            f"{base_url}/api/v2/convert/parse/result",
            headers=auth_headers(api_key),
            params={"uid": uid},
        )
        data = result["data"]
        status = data.get("status")
        if status == "success":
            if not data.get("url"):
                raise RuntimeError(f"Doc2X export reported success without a download url: {json.dumps(result['raw'], ensure_ascii=False)}")
            return result
        if status == "failed":
            raise RuntimeError(f"Doc2X export failed: {data.get('detail', 'unknown error')}")
        time.sleep(poll_seconds)
    raise TimeoutError(f"Timed out waiting for Doc2X export status for uid={uid}")


def infer_download_name(download_url: str) -> str:
    parsed = urlparse(download_url)
    name = Path(parsed.path).name
    return name or "doc2x-download.bin"


def download_export(download_url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = infer_download_name(download_url)
    out_path = out_dir / file_name
    with requests.get(download_url.replace("\\u0026", "&"), stream=True, timeout=600) as response:
        response.raise_for_status()
        with out_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return out_path


def extract_zip_if_needed(download_path: Path, export_dir: Path) -> Path | None:
    if download_path.suffix.lower() != ".zip":
        return None
    extracted_dir = export_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(download_path) as archive:
        archive.extractall(extracted_dir)
    return extracted_dir


def build_page_transcript(parse_result: dict[str, object]) -> str:
    pages = parse_result.get("pages")
    if not isinstance(pages, list):
        return "# Source Transcript\n\n"
    parts = ["# Source Transcript", ""]
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_idx = page.get("page_idx")
        page_number = int(page_idx) + 1 if isinstance(page_idx, int) else len(parts)
        page_md = str(page.get("md", "")).rstrip()
        score = page.get("score")
        parts.append(f"## Page {page_number}")
        if score is not None:
            parts.append(f"<!-- doc2x score: {score} -->")
        parts.append("")
        parts.append(page_md or "[EMPTY PAGE OCR]")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def find_first_markdown(root: Path) -> Path | None:
    candidates = sorted(root.rglob("*.md"))
    return candidates[0] if candidates else None


def preserve_export_markdown(markdown_path: Path, export_dir: Path) -> Path | None:
    if not markdown_path.exists():
        return None
    export_dir.mkdir(parents=True, exist_ok=True)
    preserved_path = export_dir / "export.md"
    shutil.copyfile(markdown_path, preserved_path)
    return preserved_path


def maybe_render_pages(job_dir: Path, pdf_path: Path, dpi: int) -> None:
    command = [
        sys.executable,
        str(Path(__file__).with_name("render_pdf_pages.py")),
        "--pdf",
        str(pdf_path),
        "--out-dir",
        str(job_dir / "pages"),
        "--dpi",
        str(dpi),
    ]
    subprocess.run(command, check=True)
    (job_dir / "pages-clean").mkdir(parents=True, exist_ok=True)


def initialize_job_files(job_dir: Path, payload: dict[str, object]) -> None:
    write_json(job_dir / "job.json", payload)
    write_text(
        job_dir / "layout-brief.md",
        "# Layout Brief\n\n- Paper size: A4\n- Goal: print-first faithful reproduction\n- Allowed changes: layout, typography, spacing, figure placement\n- Forbidden changes: rewriting or summarizing content\n- OCR backend: Doc2X API\n",
    )
    write_text(
        job_dir / "handoff-notes.md",
        "# Handoff Notes\n\n- Review Doc2X formula and table output against the source before making manual fixes.\n- Keep unresolved OCR issues here.\n- If source figures need exact visual fidelity, note whether they were reused, cleaned, or redrawn.\n",
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    api_key = ensure_api_key(args.api_key)
    pdf_path = Path(args.pdf).expanduser().resolve()
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    job_dir = Path(args.out_dir).expanduser().resolve()
    doc2x_dir = job_dir / "doc2x"
    export_dir = doc2x_dir / "export"
    job_dir.mkdir(parents=True, exist_ok=True)
    doc2x_dir.mkdir(parents=True, exist_ok=True)

    initialize_job_files(
        job_dir,
        {
            "source_pdf": str(pdf_path),
            "job_dir": str(job_dir),
            "ocr_backend": "doc2x",
            "model": args.model,
            "export_format": None if args.skip_export else args.to,
            "formula_mode": args.formula_mode,
            "formula_level": args.formula_level,
            "merge_cross_page_forms": bool(args.merge_cross_page_forms),
            "render_pages": bool(args.render_pages),
        },
    )

    base_url = args.base_url.rstrip("/")
    preupload_result = preupload(pdf_path, base_url, api_key, args.model)
    write_json(doc2x_dir / "preupload.json", preupload_result["raw"])
    upload_file(pdf_path, str(preupload_result["data"]["url"]))

    parse_status = poll_parse_status(
        str(preupload_result["data"]["uid"]),
        base_url,
        api_key,
        args.poll_seconds,
        args.timeout_seconds,
    )
    write_json(doc2x_dir / "parse-status.json", parse_status["raw"])
    parse_result = parse_status["data"].get("result")
    if not isinstance(parse_result, dict):
        raise RuntimeError(f"Doc2X parse result missing or malformed: {json.dumps(parse_status['raw'], ensure_ascii=False)}")
    write_json(doc2x_dir / "parse-result.json", parse_result)
    write_text(job_dir / "source-transcript.md", build_page_transcript(parse_result))

    if not args.skip_export:
        export_request = trigger_export(
            str(preupload_result["data"]["uid"]),
            base_url,
            api_key,
            args.to,
            args.formula_mode,
            args.formula_level,
            bool(args.merge_cross_page_forms),
            args.filename,
        )
        write_json(doc2x_dir / "export-request.json", export_request["raw"])
        export_result = poll_export_status(
            str(preupload_result["data"]["uid"]),
            base_url,
            api_key,
            args.poll_seconds,
            args.timeout_seconds,
        )
        write_json(doc2x_dir / "export-result.json", export_result["raw"])
        download_path = download_export(str(export_result["data"]["url"]), export_dir)
        extracted_dir = extract_zip_if_needed(download_path, export_dir)
        if extracted_dir:
            markdown_path = find_first_markdown(extracted_dir)
            if markdown_path:
                preserve_export_markdown(markdown_path, export_dir)

    if args.render_pages:
        maybe_render_pages(job_dir, pdf_path, args.render_dpi)

    print(str(job_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
