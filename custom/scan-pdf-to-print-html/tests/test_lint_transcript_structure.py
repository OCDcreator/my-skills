from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "lint_transcript_structure.py"


def run_lint(job_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--job-dir", str(job_dir)],
        capture_output=True,
        text=True,
    )


def write_job(job_dir: Path, transcript: str) -> None:
    (job_dir / "job.json").write_text(
        json.dumps(
            {
                "ocr_backend": "doc2x",
                "canonical_transcript_path": "source-transcript.md",
                "transcript_structure_lint_status": "pending",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (job_dir / "source-transcript.md").write_text(transcript, encoding="utf-8")


def test_lint_transcript_structure_marks_clean_transcript_as_passed(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir(parents=True, exist_ok=True)
    write_job(
        job_dir,
        "\n".join(
            [
                "# Source Transcript",
                "",
                "## Page 1",
                "",
                "### 一、线面平行",
                "",
                "正文内容。",
                "",
                "#### （一）判定定理",
                "",
                "继续正文。",
                "",
            ]
        ),
    )

    result = run_lint(job_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK:" in result.stdout
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    assert job_payload["transcript_structure_lint_status"] == "passed"


def test_lint_transcript_structure_fails_on_heading_level_jump(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir(parents=True, exist_ok=True)
    write_job(
        job_dir,
        "\n".join(
            [
                "# Source Transcript",
                "",
                "## Page 1",
                "",
                "##### 一、层级太深",
                "",
                "正文内容。",
                "",
            ]
        ),
    )

    result = run_lint(job_dir)

    assert result.returncode == 1
    assert "first content heading" in result.stdout.lower()
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    assert job_payload["transcript_structure_lint_status"] == "failed"


def test_lint_transcript_structure_records_warnings_for_title_like_paragraph_and_nonfirst_ordinal(
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir(parents=True, exist_ok=True)
    write_job(
        job_dir,
        "\n".join(
            [
                "# Source Transcript",
                "",
                "## Page 1",
                "",
                "知识盒二 线面平行与面面平行",
                "",
                "### 二、线面平行性质定理",
                "",
                "正文内容。",
                "",
            ]
        ),
    )

    result = run_lint(job_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARN:" in result.stdout
    assert "title-like paragraph" in result.stdout.lower()
    assert "starts at 2" in result.stdout.lower()
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
    assert job_payload["transcript_structure_lint_status"] == "passed-with-warnings"
