from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "validate_sheet_bottom_margin.py"
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


def _write_handout(path: Path, *, terminal_attrs: str = "") -> None:
    path.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet {{
  width: 794px;
  min-height: 1123px;
}}
.sheet-body {{
  height: 1000px;
}}
.flow-block {{
  height: 120px;
}}
.flow-block.tall {{
  height: 950px;
}}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2" {terminal_attrs}>
    <section class="sheet-body"><div class="flow-block">short lecture tail</div></section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body"><div class="flow-block tall"><h2>大招 2</h2></div></section>
  </article>
  <article class="sheet" data-page-number="4">
    <section class="sheet-body"><div class="flow-block">final page</div></section>
  </article>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def _run_validator(html: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--max-fraction",
            "0.10",
        ],
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_exempts_forced_lecture_terminal_sheet(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_handout(html, terminal_attrs='data-ends-before-lecture="true"')

    result = _run_validator(html)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "forced lecture break" in result.stdout
    assert "PASS" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_rejects_same_blank_without_lecture_marker(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_handout(html)

    result = _run_validator(html)

    assert result.returncode == 1
    assert "Sheet 2" in result.stdout
    assert "forced lecture break" not in result.stdout
