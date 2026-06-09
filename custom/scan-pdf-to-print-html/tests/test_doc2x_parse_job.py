from __future__ import annotations

import importlib.util
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
