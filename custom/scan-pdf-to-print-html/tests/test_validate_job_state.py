from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_job_state.py"


def write_common_job_files(
    job_dir: Path,
    *,
    job_payload: dict[str, object],
    include_transcript_defaults: bool = True,
) -> None:
    merged_job_payload = dict(job_payload)
    if include_transcript_defaults:
        merged_job_payload = {
            "canonical_transcript_path": "source-transcript.md",
            "raw_transcript_path": "doc2x/page-transcript.raw.md",
            "transcript_audit_status": "approved",
            "transcript_structure_lint_status": "passed",
            **merged_job_payload,
        }
    (job_dir / "doc2x").mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(merged_job_payload, ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "source-transcript.md").write_text("# Source Transcript\n", encoding="utf-8")
    (job_dir / "doc2x" / "page-transcript.raw.md").write_text("# Source Transcript Raw\n", encoding="utf-8")
    (job_dir / "layout-brief.md").write_text("# Layout Brief\n", encoding="utf-8")
    (job_dir / "handoff-notes.md").write_text("# Handoff Notes\n", encoding="utf-8")
    (job_dir / "doc2x" / "preupload.json").write_text("{}\n", encoding="utf-8")
    (job_dir / "doc2x" / "parse-status.json").write_text('{"data": {"status": "success"}}\n', encoding="utf-8")
    (job_dir / "doc2x" / "parse-result.json").write_text('{"pages": []}\n', encoding="utf-8")


def run_validator(job_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(job_dir), *args],
        capture_output=True,
        text=True,
    )


def build_subagent_manifest(
    *,
    parts_dir: Path,
    pages: list[dict[str, object]],
    final_html_path: str = "handout.html",
    assembly: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "version": 1,
        "parts_dir": str(parts_dir),
        "final_html_path": final_html_path,
        "pages": pages,
        "assembly": assembly or {"status": "pending"},
    }


def success_meta_payload(
    *, page_number: int, source_fingerprint: str = "fp-page-0001"
) -> dict[str, object]:
    return {
        "page_number": page_number,
        "status": "success",
        "source_fingerprint": source_fingerprint,
        "warnings": [],
    }


def test_require_html_fails_for_incomplete_subagent_manifest_job(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>partial</body></html>\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(parts_dir / "page-0001.fragment.html"),
                        "meta_path": str(parts_dir / "page-0001.meta.json"),
                    },
                    {
                        "page_number": 2,
                        "status": "pending",
                        "fragment_path": str(parts_dir / "page-0002.fragment.html"),
                        "meta_path": str(parts_dir / "page-0002.meta.json"),
                    },
                ],
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (parts_dir / "page-0001.fragment.html").write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    (parts_dir / "page-0001.meta.json").write_text(
        json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "page 2" in result.stdout.lower()
    assert "success" in result.stdout.lower()


def test_require_html_accepts_complete_subagent_manifest_job(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>ok</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "validated scan job" in result.stdout.lower()


def test_require_html_accepts_complete_subagent_manifest_with_relative_paths(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>relative</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": "handout-parts/page-0001.fragment.html",
                        "meta_path": "handout-parts/page-0001.meta.json",
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "validated scan job" in result.stdout.lower()


def test_require_html_fails_when_manifest_paths_escape_handout_parts(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    external_dir = tmp_path / "external-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    external_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = external_dir / "page-0001.fragment.html"
    meta_path = external_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>escaped</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "handout-parts" in result.stdout.lower()
    assert "page 1" in result.stdout.lower()


def test_require_html_fails_when_manifest_and_meta_status_drift(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>drift</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "page_number": 1,
                "status": "failed",
                "source_fingerprint": "fp-page-0001",
                "warnings": [],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "meta" in result.stdout.lower()
    assert "page 1" in result.stdout.lower()


def test_require_html_fails_for_empty_manifest_object(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>empty-manifest</body></html>\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text("{}\n", encoding="utf-8")

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "html-build-manifest" in result.stdout.lower()


def test_require_html_fails_for_empty_meta_object(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>empty-meta</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text("{}\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "meta" in result.stdout.lower()
    assert "page 1" in result.stdout.lower()


def test_require_html_fails_when_manifest_and_meta_page_numbers_mismatch(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>page-mismatch</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(
        json.dumps(success_meta_payload(page_number=999), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "page_number" in result.stdout.lower() or "page number" in result.stdout.lower()
    assert "999" in result.stdout


def test_require_html_fails_when_manifest_and_meta_fingerprints_mismatch(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>fingerprint-mismatch</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(
        json.dumps(success_meta_payload(page_number=1, source_fingerprint="fp-stale-meta"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-current-manifest",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "fingerprint" in result.stdout.lower()
    assert "page 1" in result.stdout.lower()


def test_require_html_fails_for_empty_successful_fragment(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>assembled</body></html>\n", encoding="utf-8")
    fragment_path.write_text("   \n", encoding="utf-8")
    meta_path.write_text(json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "fragment" in result.stdout.lower()
    assert "page 1" in result.stdout.lower()


def test_require_html_fails_for_raw_markdown_fragment(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>assembled</body></html>\n", encoding="utf-8")
    fragment_path.write_text("# Raw Markdown Title\n\n- bullet one\n", encoding="utf-8")
    meta_path.write_text(json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "success", "output_html": str(job_dir / "handout.html")},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "fragment" in result.stdout.lower()
    assert "html" in result.stdout.lower()


def test_require_html_fails_when_assembly_is_pending_even_if_stale_html_exists(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    (job_dir / "handout.html").write_text("<html><body>stale-old-html</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                assembly={"status": "pending"},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "assembly" in result.stdout.lower()
    assert "pending" in result.stdout.lower()


def test_require_html_accepts_custom_output_path_after_successful_assembly(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    parts_dir = job_dir / "handout-parts"
    custom_html = tmp_path / "custom-output.html"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fragment_path = parts_dir / "page-0001.fragment.html"
    meta_path = parts_dir / "page-0001.meta.json"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "html_builder": "subagent-orchestrated"},
    )
    custom_html.write_text("<html><body>custom-output</body></html>\n", encoding="utf-8")
    fragment_path.write_text("<section><p>Page 1</p></section>\n", encoding="utf-8")
    meta_path.write_text(json.dumps(success_meta_payload(page_number=1), ensure_ascii=False) + "\n", encoding="utf-8")
    (job_dir / "html-build-manifest.json").write_text(
        json.dumps(
            build_subagent_manifest(
                parts_dir=parts_dir,
                pages=[
                    {
                        "page_number": 1,
                        "status": "success",
                        "source_fingerprint": "fp-page-0001",
                        "fragment_path": str(fragment_path),
                        "meta_path": str(meta_path),
                    }
                ],
                final_html_path="handout.html",
                assembly={"status": "success", "output_html": str(custom_html)},
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "validated scan job" in result.stdout.lower()


def test_require_html_keeps_legacy_jobs_compatible(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "render_pages": False},
    )
    (job_dir / "handout.html").write_text("<html><body>legacy</body></html>\n", encoding="utf-8")

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "validated scan job" in result.stdout.lower()


def test_require_html_fails_when_doc2x_transcript_audit_is_pending(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "render_pages": False, "transcript_audit_status": "pending"},
    )
    (job_dir / "handout.html").write_text("<html><body>pending-audit</body></html>\n", encoding="utf-8")

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "audit" in result.stdout.lower()


def test_require_html_fails_when_doc2x_raw_transcript_copy_is_missing(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "render_pages": False},
    )
    (job_dir / "doc2x" / "page-transcript.raw.md").unlink()
    (job_dir / "handout.html").write_text("<html><body>missing-raw-copy</body></html>\n", encoding="utf-8")

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "raw_transcript" in result.stdout.lower() or "raw transcript" in result.stdout.lower()


def test_require_html_fails_when_transcript_structure_lint_is_pending(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"

    write_common_job_files(
        job_dir,
        job_payload={
            "ocr_backend": "doc2x",
            "render_pages": False,
            "transcript_structure_lint_status": "pending",
        },
    )
    (job_dir / "handout.html").write_text("<html><body>pending-lint</body></html>\n", encoding="utf-8")

    result = run_validator(job_dir, "--require-html")

    assert result.returncode == 1
    assert "structure" in result.stdout.lower()


def test_render_pages_job_passes_without_pages_clean_directory(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    pages_dir = job_dir / "pages"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "render_pages": True},
    )
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "page-0001.png").write_bytes(b"png")
    (pages_dir / "manifest.json").write_text('{"pages": [{"page_number": 1}]}\n', encoding="utf-8")

    result = run_validator(job_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "validated scan job" in result.stdout.lower()


def test_pre_crop_body_job_requires_body_page_manifest(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    pages_dir = job_dir / "pages"

    write_common_job_files(
        job_dir,
        job_payload={"ocr_backend": "doc2x", "render_pages": False, "pre_crop_body": True},
    )
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "page-0001.png").write_bytes(b"png")
    (pages_dir / "manifest.json").write_text('{"pages": [{"page_number": 1}]}\n', encoding="utf-8")

    result = run_validator(job_dir)

    assert result.returncode == 1
    assert "pages-body" in result.stdout.lower()
    assert "manifest" in result.stdout.lower()


def test_empty_job_json_does_not_pass_silently(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    pages_dir = job_dir / "pages"

    write_common_job_files(job_dir, job_payload={}, include_transcript_defaults=False)
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "page-0001.png").write_bytes(b"png")
    (pages_dir / "manifest.json").write_text('{"pages": [{"page_number": 1}]}\n', encoding="utf-8")

    result = run_validator(job_dir)

    assert result.returncode == 1
    assert "job.json" in result.stdout.lower()
