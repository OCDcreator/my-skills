from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_handout_via_subagents.py"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_script(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def write_source_transcript(job_dir: Path, page_texts: list[str]) -> None:
    parts = ["# Source Transcript", ""]
    for index, page_text in enumerate(page_texts, start=1):
        parts.extend(
            [
                f"## Page {index}",
                "",
                page_text,
                "",
            ]
        )
    (job_dir / "source-transcript.md").write_text("\n".join(parts), encoding="utf-8")


def init_job(tmp_path: Path) -> Path:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    write_source_transcript(
        job_dir,
        [
            "第一页内容",
            "第二页内容",
            "第三页内容",
            "第四页内容",
        ],
    )
    write_json(
        job_dir / "job.json",
        {
            "job_dir": str(job_dir),
            "source_pdf": "scan.pdf",
            "ocr_backend": "doc2x",
        },
    )
    return job_dir


def test_prepare_generates_manifest_for_selected_pages_and_marks_builder(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)

    result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "2,4")

    assert result.returncode == 0, result.stderr

    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))

    assert manifest["selected_pages"] == [2, 4]
    assert manifest["pending_pages"] == [2, 4]
    assert manifest["page_count"] == 2
    assert manifest["parts_dir"] == "handout-parts"
    assert manifest["final_html_path"] == "handout.html"
    assert [page["page_number"] for page in manifest["pages"]] == [2, 4]
    assert manifest["pages"][0]["fragment_path"].endswith("handout-parts/page-0002.fragment.html")
    assert manifest["pages"][0]["meta_path"].endswith("handout-parts/page-0002.meta.json")
    assert manifest["pages"][0]["source_fingerprint"]
    assert manifest["pages"][0]["status"] == "pending"
    assert job_payload["html_builder"] == "subagent-orchestrated"


def test_prepare_rejects_invalid_page_subset_ranges(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)

    result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "3-2")

    assert result.returncode != 0
    assert "Invalid page selection" in result.stderr


def test_prepare_does_not_write_manifest_if_job_json_is_missing(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    (job_dir / "job.json").unlink()

    result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "2,4")

    assert result.returncode != 0
    assert "missing job.json" in result.stderr.lower()
    assert not (job_dir / "html-build-manifest.json").exists()


def test_prepare_resume_only_keeps_pages_without_success_status(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    initial_prepare = run_script("prepare", "--job-dir", str(job_dir), "--pages", "1-3")
    assert initial_prepare.returncode == 0, initial_prepare.stderr
    initial_manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))
    fingerprints = {
        page["page_number"]: page["source_fingerprint"]
        for page in initial_manifest["pages"]
    }
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir(exist_ok=True)
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": fingerprints[1]},
    )
    write_json(handout_parts / "page-0002.meta.json", {"page_number": 2, "status": "failed"})
    write_json(handout_parts / "page-0003.meta.json", {"page_number": 3, "status": "pending"})

    result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "1-3", "--resume")

    assert result.returncode == 0, result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))

    assert manifest["page_count"] == 3
    assert manifest["parts_dir"] == "handout-parts"
    assert manifest["final_html_path"] == "handout.html"
    assert manifest["selected_pages"] == [1, 2, 3]
    assert manifest["pending_pages"] == [2, 3]
    assert manifest["pages"][0]["status"] == "success"
    assert manifest["pages"][1]["status"] == "failed"
    assert manifest["pages"][2]["status"] == "pending"


def test_prepare_resume_does_not_reuse_success_meta_after_transcript_change(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    initial_prepare = run_script("prepare", "--job-dir", str(job_dir), "--pages", "1")
    assert initial_prepare.returncode == 0, initial_prepare.stderr
    initial_manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))
    original_fingerprint = initial_manifest["pages"][0]["source_fingerprint"]

    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir(exist_ok=True)
    (handout_parts / "page-0001.fragment.html").write_text("<p>旧片段</p>", encoding="utf-8")
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": original_fingerprint},
    )

    write_source_transcript(
        job_dir,
        [
            "第一页内容（已更新）",
            "第二页内容",
            "第三页内容",
            "第四页内容",
        ],
    )

    result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "1", "--resume")

    assert result.returncode == 0, result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))

    assert manifest["pages"][0]["source_fingerprint"] != original_fingerprint
    assert manifest["pages"][0]["status"] == "pending"
    assert manifest["pending_pages"] == [1]


def test_prepare_without_resume_invalidates_selected_page_artifacts(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    fragment_path = handout_parts / "page-0001.fragment.html"
    meta_path = handout_parts / "page-0001.meta.json"
    error_path = handout_parts / "page-0001.error.txt"
    fragment_path.write_text("<p>stale fragment</p>", encoding="utf-8")
    write_json(meta_path, {"page_number": 1, "status": "success"})
    error_path.write_text("stale error", encoding="utf-8")

    result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "1")

    assert result.returncode == 0, result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))

    assert not fragment_path.exists()
    assert not meta_path.exists()
    assert not error_path.exists()
    assert manifest["pending_pages"] == [1]
    assert manifest["pages"][0]["status"] == "pending"


def test_prepare_treats_malformed_page_meta_as_pending(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    (handout_parts / "page-0002.meta.json").write_text("{bad json", encoding="utf-8")

    result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "2", "--resume")

    assert result.returncode == 0, result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))

    assert manifest["pending_pages"] == [2]
    assert manifest["pages"][0]["status"] == "pending"


def test_status_refreshes_manifest_from_page_meta_files(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    page_one_fingerprint = "fp-page-1"
    page_two_fingerprint = "fp-page-2"
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "selected_pages": [1, 2],
            "pending_pages": [1, 2],
            "pages": [
                {
                    "page_number": 1,
                    "fragment_path": str(handout_parts / "page-0001.fragment.html"),
                    "meta_path": str(handout_parts / "page-0001.meta.json"),
                    "source_fingerprint": page_one_fingerprint,
                    "status": "pending",
                },
                {
                    "page_number": 2,
                    "fragment_path": str(handout_parts / "page-0002.fragment.html"),
                    "meta_path": str(handout_parts / "page-0002.meta.json"),
                    "source_fingerprint": page_two_fingerprint,
                    "status": "pending",
                },
            ],
        },
    )
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": page_one_fingerprint},
    )
    write_json(handout_parts / "page-0002.meta.json", {"page_number": 2, "status": "failed"})

    result = run_script("status", "--job-dir", str(job_dir))

    assert result.returncode == 0, result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))

    assert [page["status"] for page in manifest["pages"]] == ["success", "failed"]
    assert manifest["pending_pages"] == [2]


def test_status_treats_malformed_page_meta_as_pending(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "selected_pages": [2],
            "pending_pages": [],
            "pages": [
                {
                    "page_number": 2,
                    "fragment_path": "handout-parts/page-0002.fragment.html",
                    "meta_path": "handout-parts/page-0002.meta.json",
                    "source_fingerprint": "fp-page-2",
                    "status": "success",
                }
            ],
        },
    )
    (handout_parts / "page-0002.meta.json").write_text("{bad json", encoding="utf-8")

    result = run_script("status", "--job-dir", str(job_dir))

    assert result.returncode == 0, result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))

    assert manifest["pending_pages"] == [2]
    assert manifest["pages"][0]["status"] == "pending"


def test_assemble_builds_final_html_from_fragments_only(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    (job_dir / "source-transcript.md").unlink()
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    default_out = job_dir / "handout.html"
    page_two_fingerprint = "fp-page-2"
    page_four_fingerprint = "fp-page-4"
    (handout_parts / "page-0002.fragment.html").write_text("<h2>第二页片段</h2>", encoding="utf-8")
    (handout_parts / "page-0004.fragment.html").write_text("<p>第四页片段</p>", encoding="utf-8")
    write_json(
        handout_parts / "page-0002.meta.json",
        {"page_number": 2, "status": "success", "source_fingerprint": page_two_fingerprint},
    )
    write_json(
        handout_parts / "page-0004.meta.json",
        {"page_number": 4, "status": "success", "source_fingerprint": page_four_fingerprint},
    )
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "title": "Fragment Only Handout",
            "source_label": "Subagent Fragments",
            "final_html_path": "handout.html",
            "selected_pages": [2, 4],
            "pending_pages": [],
            "pages": [
                {
                    "page_number": 2,
                    "fragment_path": str(handout_parts / "page-0002.fragment.html"),
                    "meta_path": str(handout_parts / "page-0002.meta.json"),
                    "source_fingerprint": page_two_fingerprint,
                    "status": "success",
                },
                {
                    "page_number": 4,
                    "fragment_path": str(handout_parts / "page-0004.fragment.html"),
                    "meta_path": str(handout_parts / "page-0004.meta.json"),
                    "source_fingerprint": page_four_fingerprint,
                    "status": "success",
                },
            ],
        },
    )

    result = run_script("assemble", "--job-dir", str(job_dir))

    assert result.returncode == 0, result.stderr
    html = (job_dir / "handout.html").read_text(encoding="utf-8")
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))

    assert "Fragment Only Handout" in html
    assert "第二页片段" in html
    assert "第四页片段" in html
    assert manifest["assembly"]["status"] == "success"
    assert manifest["final_html_path"] == str(default_out)


def test_assemble_with_custom_output_updates_manifest_contract(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    custom_out = job_dir / "custom-output.html"
    page_one_fingerprint = "fp-page-1"
    (handout_parts / "page-0001.fragment.html").write_text("<p>第一页片段</p>", encoding="utf-8")
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": page_one_fingerprint},
    )
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "title": "Custom Output Handout",
            "source_label": "Subagent Fragments",
            "final_html_path": "handout.html",
            "selected_pages": [1],
            "pending_pages": [],
            "pages": [
                {
                    "page_number": 1,
                    "fragment_path": "handout-parts/page-0001.fragment.html",
                    "meta_path": "handout-parts/page-0001.meta.json",
                    "source_fingerprint": page_one_fingerprint,
                    "status": "success",
                }
            ],
            "assembly": {"status": "pending"},
        },
    )

    result = run_script("assemble", "--job-dir", str(job_dir), "--out-html", str(custom_out))

    assert result.returncode == 0, result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))

    assert custom_out.exists()
    assert manifest["final_html_path"] == str(custom_out)
    assert manifest["assembly"]["output_html"] == str(custom_out)
    assert job_payload["handout_html"] == str(custom_out)


def test_default_reassemble_resets_manifest_and_job_output_path_after_custom_output(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    custom_out = job_dir / "custom-output.html"
    default_out = job_dir / "handout.html"
    page_one_fingerprint = "fp-page-1"
    (handout_parts / "page-0001.fragment.html").write_text("<p>第一页片段</p>", encoding="utf-8")
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": page_one_fingerprint},
    )
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "title": "Reassemble Path Reset",
            "source_label": "Subagent Fragments",
            "final_html_path": "handout.html",
            "selected_pages": [1],
            "pending_pages": [],
            "pages": [
                {
                    "page_number": 1,
                    "fragment_path": "handout-parts/page-0001.fragment.html",
                    "meta_path": "handout-parts/page-0001.meta.json",
                    "source_fingerprint": page_one_fingerprint,
                    "status": "success",
                }
            ],
            "assembly": {"status": "pending"},
        },
    )

    first_result = run_script("assemble", "--job-dir", str(job_dir), "--out-html", str(custom_out))
    assert first_result.returncode == 0, first_result.stderr

    second_result = run_script("assemble", "--job-dir", str(job_dir))

    assert second_result.returncode == 0, second_result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))

    assert default_out.exists()
    assert manifest["final_html_path"] == str(default_out)
    assert manifest["assembly"]["output_html"] == str(default_out)
    assert job_payload["handout_html"] == str(default_out)


def test_prepare_resets_custom_assembly_contract_for_new_run(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    custom_out = job_dir / "custom-output.html"
    page_one_fingerprint = "fp-page-1"
    (handout_parts / "page-0001.fragment.html").write_text("<p>第一页片段</p>", encoding="utf-8")
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": page_one_fingerprint},
    )
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "title": "Cycle Handout",
            "source_label": "Subagent Fragments",
            "final_html_path": "handout.html",
            "selected_pages": [1],
            "pending_pages": [],
            "pages": [
                {
                    "page_number": 1,
                    "fragment_path": "handout-parts/page-0001.fragment.html",
                    "meta_path": "handout-parts/page-0001.meta.json",
                    "source_fingerprint": page_one_fingerprint,
                    "status": "success",
                }
            ],
            "assembly": {"status": "pending"},
        },
    )

    assemble_result = run_script("assemble", "--job-dir", str(job_dir), "--out-html", str(custom_out))

    assert assemble_result.returncode == 0, assemble_result.stderr

    prepare_result = run_script("prepare", "--job-dir", str(job_dir), "--pages", "1")

    assert prepare_result.returncode == 0, prepare_result.stderr
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))

    assert manifest["final_html_path"] == "handout.html"
    assert manifest["assembly"] == {"status": "pending"}
    assert "output_html" not in manifest["assembly"]
    assert "handout_html" not in job_payload


def test_assemble_does_not_write_outputs_if_job_json_is_missing(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    page_one_fingerprint = "fp-page-1"
    (handout_parts / "page-0001.fragment.html").write_text("<p>第一页片段</p>", encoding="utf-8")
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": page_one_fingerprint},
    )
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "title": "Missing Job Handout",
            "source_label": "Subagent Fragments",
            "selected_pages": [1],
            "pending_pages": [],
            "pages": [
                {
                    "page_number": 1,
                    "fragment_path": "handout-parts/page-0001.fragment.html",
                    "meta_path": "handout-parts/page-0001.meta.json",
                    "source_fingerprint": page_one_fingerprint,
                    "status": "success",
                }
            ],
            "assembly": {"status": "pending"},
        },
    )
    (job_dir / "job.json").unlink()

    result = run_script("assemble", "--job-dir", str(job_dir))

    assert result.returncode != 0
    assert "missing job.json" in result.stderr.lower()
    assert not (job_dir / "handout.html").exists()
    manifest = json.loads((job_dir / "html-build-manifest.json").read_text(encoding="utf-8"))
    assert manifest["assembly"]["status"] == "pending"


def test_assemble_requires_all_pages_to_be_successful(tmp_path: Path) -> None:
    job_dir = init_job(tmp_path)
    handout_parts = job_dir / "handout-parts"
    handout_parts.mkdir()
    page_one_fingerprint = "fp-page-1"
    page_two_fingerprint = "fp-page-2"
    (handout_parts / "page-0001.fragment.html").write_text("<p>第一页片段</p>", encoding="utf-8")
    write_json(
        handout_parts / "page-0001.meta.json",
        {"page_number": 1, "status": "success", "source_fingerprint": page_one_fingerprint},
    )
    write_json(handout_parts / "page-0002.meta.json", {"page_number": 2, "status": "failed"})
    write_json(
        job_dir / "html-build-manifest.json",
        {
            "title": "Blocked Handout",
            "source_label": "Subagent Fragments",
            "selected_pages": [1, 2],
            "pending_pages": [2],
            "pages": [
                {
                    "page_number": 1,
                    "fragment_path": str(handout_parts / "page-0001.fragment.html"),
                    "meta_path": str(handout_parts / "page-0001.meta.json"),
                    "source_fingerprint": page_one_fingerprint,
                    "status": "success",
                },
                {
                    "page_number": 2,
                    "fragment_path": str(handout_parts / "page-0002.fragment.html"),
                    "meta_path": str(handout_parts / "page-0002.meta.json"),
                    "source_fingerprint": page_two_fingerprint,
                    "status": "failed",
                },
            ],
        },
    )

    result = run_script("assemble", "--job-dir", str(job_dir))

    assert result.returncode != 0
    assert "not all pages are successful" in result.stderr.lower()
