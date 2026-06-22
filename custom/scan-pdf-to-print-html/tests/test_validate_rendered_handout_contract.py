from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_rendered_handout_contract.py"
)

IMAGE_DATA = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='90'%3E"
    "%3Crect width='120' height='90' fill='white'/%3E"
    "%3Cpath d='M10 70 C35 10, 55 10, 70 70 S100 130, 110 20' "
    "stroke='black' fill='none' stroke-width='4'/%3E"
    "%3C/svg%3E"
)


def _playwright_ready() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
        return True
    except Exception:
        return False


def _write_handout(path: Path, css: str) -> None:
    path.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.transcript-flow .phycat-blockquote {{
  border-left: 3px solid #1b365d;
  background: #f1efe8;
  padding: 8px 12px;
}}
.transcript-flow .lead-tag-example {{
  display: inline-block;
  background: #DE7356;
  color: white;
}}
{css}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-fit-state="ready">
    <section class="sheet-body">
      <div class="transcript-flow">
        <blockquote class="phycat-blockquote">
          <p class="lead-para"><span class="lead-tag-example">例 5</span> 函数图像选择题。</p>
          <table>
            <thead><tr><th>A</th><th>B</th></tr></thead>
            <tbody>
              <tr>
                <td><img src="{IMAGE_DATA}" alt="A"></td>
                <td><img src="{IMAGE_DATA}" alt="B"></td>
              </tr>
            </tbody>
          </table>
        </blockquote>
      </div>
    </section>
  </article>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def _write_cover_handout(path: Path, cover_margin: str) -> None:
    path.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
body {{
  margin: 0;
  padding: 24px 0;
}}
.sheet {{
  width: 794px;
  height: 1123px;
  margin: 0 auto 12mm;
  background: white;
}}
.concept-map-sheet {{
  margin: {cover_margin};
}}
@media print {{
  .concept-map-sheet {{ margin: 0; }}
}}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet concept-map-sheet" data-fit-state="ready">
    <svg width="794" height="1123" viewBox="0 0 794 1123">
      <rect width="794" height="1123" fill="white"/>
      <text x="397" y="560" text-anchor="middle">cover</text>
    </svg>
  </article>
  <article class="sheet" data-fit-state="ready">
    <section class="sheet-body">
      <h1>正文</h1>
      <p>普通内容页。</p>
    </section>
  </article>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_accepts_neutral_choice_table(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_handout(
        html,
        """
.transcript-flow .phycat-blockquote table,
.transcript-flow .phycat-blockquote th,
.transcript-flow .phycat-blockquote td {
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 400;
}
.transcript-flow .phycat-blockquote img {
  width: 100px;
  height: 80px;
}
""",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--wait-ms",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "question option tables are neutral" in result.stdout
    assert "question option images are readable" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_rejects_left_aligned_cover_sheet(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_cover_handout(html, "0")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--wait-ms",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "[FAIL] special cover sheets align with regular sheets in screen preview" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_skips_cover_alignment_when_no_cover_sheet(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_handout(
        html,
        """
.transcript-flow .phycat-blockquote table,
.transcript-flow .phycat-blockquote th,
.transcript-flow .phycat-blockquote td {
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 400;
}
.transcript-flow .phycat-blockquote img {
  width: 100px;
  height: 80px;
}
""",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--wait-ms",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "special cover sheets align with regular sheets in screen preview" not in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_rejects_flattened_blockquote_left_rule(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_handout(
        html,
        """
.transcript-flow .phycat-blockquote {
  border: 1px solid #e8e6dc;
  background: #e8e6dc;
}
.transcript-flow .phycat-blockquote table,
.transcript-flow .phycat-blockquote th,
.transcript-flow .phycat-blockquote td {
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 400;
}
.transcript-flow .phycat-blockquote img {
  width: 100px;
  height: 80px;
}
""",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--wait-ms",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "[FAIL] blockquote left rule visible" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_rejects_ruled_choice_table_and_tiny_images(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_handout(
        html,
        """
.transcript-flow .phycat-blockquote table {
  border: 1px solid #999;
  background: #fffaf0;
}
.transcript-flow .phycat-blockquote th {
  border: 1px solid #999;
  background: #efe6d5;
  font-size: 12px;
  font-weight: 700;
}
.transcript-flow .phycat-blockquote td {
  border: 1px solid #999;
  background: #fffaf0;
  font-size: 12px;
  font-weight: 400;
}
.transcript-flow .phycat-blockquote img {
  width: 40px;
  height: 30px;
}
""",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--wait-ms",
            "0",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "[FAIL] question option tables are neutral" in result.stdout
    assert "[FAIL] question option th/td styles match" in result.stdout
    assert "[FAIL] question option images are readable" in result.stdout
