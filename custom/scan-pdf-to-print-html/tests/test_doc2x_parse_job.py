from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "doc2x_parse_job.py"
SPEC = importlib.util.spec_from_file_location("doc2x_parse_job", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_preserve_export_markdown_keeps_canonical_transcript_unchanged(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    export_dir = job_dir / "doc2x" / "export"
    extracted_dir = export_dir / "extracted"
    source_transcript = job_dir / "source-transcript.md"
    export_markdown = extracted_dir / "nested" / "result.md"

    canonical_content = "# Source Transcript\n\n## Page 1\n\nCanonical page transcript.\n"
    export_content = "# Export Markdown\n\nMerged export body.\n"

    source_transcript.parent.mkdir(parents=True, exist_ok=True)
    source_transcript.write_text(canonical_content, encoding="utf-8")
    export_markdown.parent.mkdir(parents=True, exist_ok=True)
    export_markdown.write_text(export_content, encoding="utf-8")

    preserved_path = MODULE.preserve_export_markdown(export_markdown, export_dir)

    assert source_transcript.read_text(encoding="utf-8") == canonical_content
    assert preserved_path == export_dir / "export.md"
    assert preserved_path.read_text(encoding="utf-8") == export_content


def test_preserve_export_markdown_localizes_remote_doc2x_crop_urls_when_local_image_exists(
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "job"
    export_dir = job_dir / "doc2x" / "export"
    extracted_dir = export_dir / "extracted"
    export_markdown = extracted_dir / "output.md"
    local_image_name = "019eab50-58b4-72eb-8e82-6d70f600ccfe_0_890_558_214_114_0.jpg"
    remote_url = (
        "https://cdn.noedgeai.com/019eab50-58b4-72eb-8e82-6d70f600ccfe_0.jpg"
        "?x=890&y=558&w=214&h=114&r=0"
    )

    (extracted_dir / "images").mkdir(parents=True, exist_ok=True)
    (extracted_dir / "images" / local_image_name).write_bytes(b"fake-image")
    export_markdown.write_text(
        f'<table><tr><td><img src="{remote_url}"/></td></tr></table>\n',
        encoding="utf-8",
    )

    preserved_path = MODULE.preserve_export_markdown(export_markdown, export_dir)

    assert preserved_path == export_dir / "export.md"
    preserved_text = preserved_path.read_text(encoding="utf-8")
    assert remote_url not in preserved_text
    assert f'<img src="images/{local_image_name}"/>' in preserved_text
    assert (export_dir / "images" / local_image_name).exists()


def test_preserve_export_markdown_copies_existing_local_image_assets_next_to_export_md(
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "job"
    export_dir = job_dir / "doc2x" / "export"
    extracted_dir = export_dir / "extracted"
    export_markdown = extracted_dir / "output.md"
    local_image_name = "diagram-1.jpg"

    (extracted_dir / "images").mkdir(parents=True, exist_ok=True)
    (extracted_dir / "images" / local_image_name).write_bytes(b"diagram")
    export_markdown.write_text(
        f"![diagram](images/{local_image_name})\n",
        encoding="utf-8",
    )

    preserved_path = MODULE.preserve_export_markdown(export_markdown, export_dir)

    assert preserved_path.read_text(encoding="utf-8") == f"![diagram](images/{local_image_name})\n"
    assert (export_dir / "images" / local_image_name).read_bytes() == b"diagram"


def test_prepare_doc2x_input_pdf_builds_body_only_pdf_before_upload(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    commands: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> None:
        commands.append(command)
        script_name = Path(command[1]).name
        if script_name == "render_pdf_pages.py":
            pages_dir = job_dir / "pages"
            pages_dir.mkdir(parents=True, exist_ok=True)
            (pages_dir / "page-001.png").write_bytes(b"fake-page")
            (pages_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "source_pdf": str(pdf_path),
                        "page_count": 1,
                        "rendered_page_count": 1,
                        "dpi": 240,
                        "pages": [
                            {
                                "page_number": 1,
                                "image_path": str(pages_dir / "page-001.png"),
                                "width": 1000,
                                "height": 1400,
                                "dpi": 240,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return

        if script_name == "crop_page_bodies.py":
            body_dir = job_dir / "pages-body"
            body_dir.mkdir(parents=True, exist_ok=True)
            (body_dir / "page-001.body.png").write_bytes(b"fake-body")
            (body_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "source_manifest": str(job_dir / "pages" / "manifest.json"),
                        "cropped_page_count": 1,
                        "pages": [
                            {
                                "page_number": 1,
                                "body_image_path": str(body_dir / "page-001.body.png"),
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (job_dir / "doc2x").mkdir(parents=True, exist_ok=True)
            (job_dir / "doc2x" / "body-only.pdf").write_bytes(b"%PDF-body\n")
            return

        raise AssertionError(f"Unexpected command: {command}")

    upload_pdf = MODULE.prepare_doc2x_input_pdf(
        job_dir=job_dir,
        pdf_path=pdf_path,
        render_dpi=240,
        runner=fake_run,
    )

    assert upload_pdf == job_dir / "doc2x" / "body-only.pdf"
    assert [Path(command[1]).name for command in commands] == [
        "render_pdf_pages.py",
        "crop_page_bodies.py",
    ]
    assert "--out-pdf" in commands[1]


def test_materialize_doc2x_transcripts_writes_raw_copy_and_pending_audit_metadata(
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "job"
    MODULE.initialize_job_files(job_dir, {"ocr_backend": "doc2x"})

    MODULE.materialize_doc2x_transcripts(
        job_dir,
        {
            "pages": [
                {
                    "page_idx": 0,
                    "md": "第一段 OCR 正文",
                }
            ]
        },
    )

    raw_transcript = job_dir / "doc2x" / "page-transcript.raw.md"
    canonical_transcript = job_dir / "source-transcript.md"
    job_payload = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))

    assert raw_transcript.exists()
    assert canonical_transcript.exists()
    assert raw_transcript.read_text(encoding="utf-8") == canonical_transcript.read_text(encoding="utf-8")
    assert "第一段 OCR 正文" in canonical_transcript.read_text(encoding="utf-8")
    assert job_payload["raw_transcript_path"] == "doc2x/page-transcript.raw.md"
    assert job_payload["canonical_transcript_path"] == "source-transcript.md"
    assert job_payload["transcript_audit_status"] == "pending"
    assert job_payload["transcript_structure_lint_status"] == "pending"
