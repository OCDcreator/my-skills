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


def _write_orphan_heading_handout(
    path: Path, *, heading_tag: str = "h3", terminal_attrs: str = ""
) -> None:
    """Reproduces the orphan-heading defect the user reported.

    Sheet 2 ends with a LONE heading followed by a large blank; the next sheet
    begins with a blockquote that did not fit. Before the fix, the
    next-sheet-blockquote exemption silently excused this blank. The
    orphan-heading guard must FAIL it and point at the stranded heading.

    heading_tag is parameterized so the regression is locked at every level
    the builder emits — h3 and h4. The real project (2026-06-19-ch02-conic)
    exposed an h4 orphan ("【方法 2】定义法"), so h4 is the primary regression
    case; h3 stays covered too.
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
}}
.sheet-body {{
  height: 1000px;
}}
.flow-block {{
  height: 120px;
}}
.flow-block.half {{
  height: 500px;
}}
.flow-block.fill {{
  height: 900px;
}}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2" {terminal_attrs}>
    <section class="sheet-body">
      <div class="flow-block half">正文段落，占满页面上半部分。</div>
      <div class="flow-block"><{heading_tag}>这是一个小节标题</{heading_tag}></div>
    </section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body">
      <blockquote class="phycat-blockquote"><div class="flow-block fill">例题引用块，放不下才到这一页。</div></blockquote>
    </section>
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


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_fails_orphan_heading_even_with_blockquote_next(tmp_path: Path) -> None:
    """Core regression: a stranded trailing heading must FAIL even though the
    next sheet starts with a blockquote (which previously exempted the blank).

    Parameterized across heading levels the builder emits. The real project
    exposed an h4 orphan, so h4 is the primary case; h3 is covered too.
    """
    for heading_tag in ("h3", "h4"):
        html = tmp_path / f"handout_{heading_tag}.html"
        _write_orphan_heading_handout(html, heading_tag=heading_tag)

        result = _run_validator(html)

        assert result.returncode == 1, f"[{heading_tag}] {result.stdout + result.stderr}"
        assert "Sheet 2" in result.stdout, f"[{heading_tag}] {result.stdout}"
        assert "orphan heading" in result.stdout, f"[{heading_tag}] {result.stdout}"


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_exempts_blockquote_boundary_without_orphan(tmp_path: Path) -> None:
    """A legit blockquote boundary — the preceding sheet's last element is a
    paragraph, not a stranded heading — must still PASS. The orphan guard must
    not over-fire and break the original blockquote exemption."""
    html = tmp_path / "handout.html"
    html.write_text(
        """<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet { width: 794px; min-height: 1123px; }
.sheet-body { height: 1000px; }
.flow-block { height: 120px; }
.flow-block.half { height: 500px; }
.flow-block.fill { height: 900px; }
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2">
    <section class="sheet-body"><div class="flow-block half">正文段落，以普通段落结尾。</div></section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body">
      <blockquote class="phycat-blockquote"><div class="flow-block fill">例题引用块。</div></blockquote>
    </section>
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

    result = _run_validator(html)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "next sheet starts with blockquote" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_keeps_orphan_heading_exempt_for_real_chapter_break(tmp_path: Path) -> None:
    """A trailing heading is the intended end of a section when the next sheet
    starts a chapter-shaped h2. That is NOT an orphan — it must stay exempt."""
    html = tmp_path / "handout.html"
    html.write_text(
        """<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet { width: 794px; min-height: 1123px; }
.sheet-body { height: 1000px; }
.flow-block { height: 120px; }
.flow-block.half { height: 500px; }
.flow-block.fill { height: 900px; }
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2">
    <section class="sheet-body">
      <div class="flow-block half">本章正文。</div>
      <div class="flow-block"><h3>本章小结</h3></div>
    </section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body"><div class="flow-block fill"><h2>第二章 新内容</h2></div></section>
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

    result = _run_validator(html)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "chapter h2" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_exempts_legitimate_blank_when_next_sheet_starts_with_heading(tmp_path: Path) -> None:
    """Weak-model safety valve: a trailing blank is LEGITIMATE when the next
    sheet starts with a heading, because the heading belongs at the start of
    its own section. Pulling it up would strand it above a blank (re-creating
    the orphan defect). This must PASS so a weaker model is not tempted to
    "tighten spacing" to chase a blank that is actually correct.

    This is the exact shape the real project exposed: sheet N has a moderate
    trailing blank, and sheet N+1 begins with a heading whose content follows.
    """
    html = tmp_path / "handout.html"
    html.write_text(
        """<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet { width: 794px; min-height: 1123px; }
.sheet-body { height: 1000px; }
.flow-block { height: 120px; }
.flow-block.half { height: 500px; }
.flow-block.fill { height: 900px; }
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2">
    <section class="sheet-body"><div class="flow-block half">正文段落，留下合理的尾部空白。</div></section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body">
      <div class="flow-block"><h3>小节标题</h3></div>
      <div class="flow-block fill">小节正文内容。</div>
    </section>
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

    result = _run_validator(html)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "section start" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_still_fails_real_orphan_when_next_sheet_starts_with_heading(tmp_path: Path) -> None:
    """The heading-boundary exemption on the NEXT sheet must NOT hide a real
    orphan heading stranded on THIS sheet. This guards the exemption against
    being too broad: a sheet that itself ends with a heading above a large
    blank still FAILs, even if the sheet after it also starts with a heading.
    """
    html = tmp_path / "handout.html"
    html.write_text(
        """<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet { width: 794px; min-height: 1123px; }
.sheet-body { height: 1000px; }
.flow-block { height: 120px; }
.flow-block.half { height: 500px; }
.flow-block.fill { height: 900px; }
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2">
    <section class="sheet-body">
      <div class="flow-block half">正文段落。</div>
      <div class="flow-block"><h3>本页末尾的孤标题</h3></div>
    </section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body">
      <div class="flow-block"><h3>下一页的标题</h3></div>
      <div class="flow-block fill">下一页正文。</div>
    </section>
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

    result = _run_validator(html)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Sheet 2" in result.stdout
    assert "orphan heading" in result.stdout
