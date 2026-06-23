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


# Portrait-aspect SVG (90 wide x 120 tall, aspect 0.75 -> portrait band 15-28%).
# Used by the aspect-ratio width-band regression tests (C26). <!-- evolved 2026-06-23 -->
PORTRAIT_IMAGE_DATA = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='90' height='120'%3E"
    "%3Crect width='90' height='120' fill='%23eee'/%3E"
    "%3C/svg%3E"
)
REMOTE_IMAGE_URL = "https://cdn.noedgeai.com/test-figure.jpg?x=10&y=20&w=90&h=120"


def _write_body_image_handout(path: Path, css: str, img_src: str = PORTRAIT_IMAGE_DATA) -> None:
    """Handout with one ordinary body image (NOT inside a choice table).

    Used by the C26 width-band and C28 remote-src regression tests.
    The sheet-body is 794px wide (A4 @ 96dpi), so the width-band fractions
    map roughly to: 15%%=~119px, 28%%=~222px, 63%%=~500px.
    """
    path.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet {{
  width: 794px;
  min-height: 1123px;
  margin: 0 auto;
  background: white;
}}
.sheet-body {{
  padding: 0;
}}
.transcript-flow img {{
  display: block;
  margin: 0 auto;
}}
{css}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-fit-state="ready">
    <section class="sheet-body">
      <div class="transcript-flow">
        <p>正文段落。</p>
        <p><img src="{img_src}" alt="figure"></p>
      </div>
    </section>
  </article>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


def _write_cluster_handout(path: Path, css: str) -> None:
    """Handout with one .ocr-image-cluster containing two images (C27).

    PASS case uses a 2-column grid (side-by-side); FAIL case uses display:block
    so the two images stack vertically.
    """
    path.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet {{
  width: 794px;
  min-height: 1123px;
  margin: 0 auto;
  background: white;
}}
.transcript-flow .ocr-image-cluster img {{
  width: 200px;
  height: 150px;
}}
{css}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-fit-state="ready">
    <section class="sheet-body">
      <div class="transcript-flow">
        <p>下图组展示两个并列图形。</p>
        <span class="ocr-image-cluster ocr-image-cluster--2">
          <img src="{IMAGE_DATA}" alt="a">
          <img src="{IMAGE_DATA}" alt="b">
        </span>
      </div>
    </section>
  </article>
</main>
</body>
</html>
""",
        encoding="utf-8",
    )


# --- C26: aspect-ratio image width band --- <!-- evolved 2026-06-23 -->

@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_accepts_in_band_portrait_image(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    # Portrait band is 15-28% of ~794px ~= 119-222px. 160px ~= 20%, in band.
    _write_body_image_handout(html, ".transcript-flow img { width: 160px; height: auto; }")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--html", str(html), "--wait-ms", "0"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[FAIL] non-exempt images render within aspect-ratio width band" not in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_rejects_oversized_portrait_image(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    # 500px ~= 63% of 794px, far above the portrait band ceiling (28%).
    _write_body_image_handout(html, ".transcript-flow img { width: 500px; height: auto; }")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--html", str(html), "--wait-ms", "0"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "[FAIL] non-exempt images render within aspect-ratio width band" in result.stdout


# --- C27: adjacent-image side-by-side --- <!-- evolved 2026-06-23 -->

@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_accepts_side_by_side_cluster(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_cluster_handout(
        html,
        ".transcript-flow .ocr-image-cluster { "
        "display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; "
        "}",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--html", str(html), "--wait-ms", "0"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[FAIL] clustered/figure images are side-by-side, not stacked" not in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_rejects_stacked_cluster(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    # Force each cluster image onto its own line (display:block on the imgs)
    # so they stack vertically instead of sitting side-by-side.
    _write_cluster_handout(
        html,
        ".transcript-flow .ocr-image-cluster img { display: block; }",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--html", str(html), "--wait-ms", "0"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "[FAIL] clustered/figure images are side-by-side, not stacked" in result.stdout


# --- C28: HTML local-image-only (--disallow-remote-images) --- <!-- evolved 2026-06-23 -->

@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_accepts_local_src_when_remote_disallowed(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_body_image_handout(
        html,
        ".transcript-flow img { width: 160px; height: auto; }",
        img_src=PORTRAIT_IMAGE_DATA,  # data: URI is local
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--wait-ms",
            "0",
            "--disallow-remote-images",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[FAIL] handout.html uses local image paths only (no remote src)" not in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_rendered_contract_rejects_remote_src_when_remote_disallowed(tmp_path: Path) -> None:
    html = tmp_path / "handout.html"
    _write_body_image_handout(
        html,
        ".transcript-flow img { width: 160px; height: auto; }",
        img_src=REMOTE_IMAGE_URL,  # remote CDN URL
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--html",
            str(html),
            "--wait-ms",
            "0",
            "--disallow-remote-images",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "[FAIL] handout.html uses local image paths only (no remote src)" in result.stdout
