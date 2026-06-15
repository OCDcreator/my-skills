from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Make the sibling scripts/ directory importable so we can unit-test the
# page-range parser without going through a subprocess. The script imports
# PyMuPDF (fitz) lazily inside main(), so importing the module here does not
# require fitz to be installed.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extract_and_submit import parse_page_range  # noqa: E402

SCRIPT_PATH = SCRIPTS_DIR / "extract_and_submit.py"


# ---------------------------------------------------------------------------
# Unit tests: page-range parser (pure function, no fitz required)
# ---------------------------------------------------------------------------


def test_parse_single_page() -> None:
    assert parse_page_range("7") == [6]


def test_parse_range() -> None:
    assert parse_page_range("6-36") == list(range(5, 36))


def test_parse_mixed() -> None:
    assert parse_page_range("1-3,7,10-12") == [0, 1, 2, 6, 9, 10, 11]


def test_parse_whitespace() -> None:
    assert parse_page_range(" 1 , 2 ") == [0, 1]


def test_parse_empty() -> None:
    with pytest.raises(ValueError):
        parse_page_range("")


def test_parse_invalid() -> None:
    with pytest.raises(ValueError):
        parse_page_range("abc")


# ---------------------------------------------------------------------------
# Integration tests: CLI guards and extraction (need fitz; use a generated PDF)
# ---------------------------------------------------------------------------
pytest.importorskip("fitz")


def _make_pdf(path: Path, page_count: int) -> None:
    import fitz  # type: ignore
    doc = fitz.open()
    for i in range(page_count):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(str(path))
    doc.close()


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_missing_pdf_errors(tmp_path: Path) -> None:
    result = _run_cli(
        "--pdf", str(tmp_path / "missing.pdf"),
        "--pages", "1-3",
        "--output-dir", str(tmp_path / "out"),
    )
    assert result.returncode == 1
    assert "not found" in result.stderr.lower()


def test_ratio_guard_blocks_large_extraction(tmp_path: Path) -> None:
    pdf = tmp_path / "big.pdf"
    _make_pdf(pdf, 15)
    result = _run_cli(
        "--pdf", str(pdf),
        "--pages", "1-12",  # 12/15 = 80%
        "--output-dir", str(tmp_path / "out"),
    )
    assert result.returncode == 1
    assert "--confirm-large" in result.stderr


def test_ratio_guard_passes_with_confirm_large(tmp_path: Path) -> None:
    pdf = tmp_path / "big.pdf"
    _make_pdf(pdf, 15)
    result = _run_cli(
        "--pdf", str(pdf),
        "--pages", "1-12",
        "--output-dir", str(tmp_path / "out"),
        "--confirm-large",
    )
    assert result.returncode == 0
    sub = tmp_path / "out" / "doc2x" / "source-pages.pdf"
    assert sub.exists()


def test_missing_pages_required_for_big_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "big.pdf"
    _make_pdf(pdf, 15)
    result = _run_cli(
        "--pdf", str(pdf),
        "--output-dir", str(tmp_path / "out"),
    )
    assert result.returncode == 1
    assert "--pages is required" in result.stderr


def test_allow_full_pdf_bypasses_ratio_guard(tmp_path: Path) -> None:
    """Regression: --allow-full-pdf on a small PDF is explicit consent to upload
    the whole document, so the ratio guard must NOT fire."""
    pdf = tmp_path / "small.pdf"
    _make_pdf(pdf, 5)
    result = _run_cli(
        "--pdf", str(pdf),
        "--output-dir", str(tmp_path / "out"),
        "--allow-full-pdf",
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "out" / "doc2x" / "extract-manifest.json").read_text("utf-8"))
    assert manifest["extracted_page_count"] == 5
    assert manifest["requested_pages"] == "all"


def test_manifest_fields(tmp_path: Path) -> None:
    pdf = tmp_path / "big.pdf"
    _make_pdf(pdf, 40)
    result = _run_cli(
        "--pdf", str(pdf),
        "--pages", "6-8",
        "--output-dir", str(tmp_path / "out"),
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "out" / "doc2x" / "extract-manifest.json").read_text("utf-8"))
    assert manifest["source_page_count"] == 40
    assert manifest["extracted_page_count"] == 3
    assert manifest["requested_pages"] == "6-8"
    assert manifest["extracted_pdf"] == "doc2x/source-pages.pdf"
    assert "timestamp" in manifest
