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
    <section class="sheet-body"><div class="flow-block tall">content filling the page (no heading, ~5% trailing)</div></section>
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
    <section class="sheet-body">
      <div class="flow-block"><h2>第二章 新内容</h2></div>
      <div class="flow-block fill">新章节正文（让标题不是最后一行）。</div>
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


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_exempts_figure_inside_protected_blockquote(tmp_path: Path) -> None:
    """Regression for the 2026-06-25 false-positive figureDefect on in-quote
    images. Sheet 3's first block is a .phycat-blockquote CONTAINING an image
    whose band-floor height would fit sheet 2's trailing gap. Before the fix,
    analyzeFigureBoundary reported figureDefect (FAIL, "narrow the figure"),
    sending the model into an unbounded shrink/reflow loop — even though
    narrowing an in-quote image CANNOT move the protected blockquote. After the
    fix the boundary falls through to the blockquote exemption (PASS), because
    the blank is the blockquote-integrity cost, not a movable-figure defect.
    """
    svg = (
        "data:image/svg+xml;utf8,"
        "<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>"
        "<rect width='200' height='200' fill='%23ccc'/></svg>"
    )
    html = tmp_path / "handout.html"
    html.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet {{ width: 794px; min-height: 1123px; }}
.sheet-body {{ height: 1000px; }}
.flow-block {{ height: 60px; }}
.flow-block.gap {{ height: 500px; }}
.flow-block.fill {{ height: 880px; }}
.phycat-blockquote {{ border-left: 3px solid #1b365d; padding: 6px 12px; }}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2">
    <section class="sheet-body"><div class="flow-block gap">正文，留下大尾部空白。</div></section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body">
      <blockquote class="phycat-blockquote"><p>例题：如图所示，</p><figure style="margin:0;"><img src="{svg}" style="width:300px;height:auto;display:block;" alt="fig"/></figure></blockquote>
      <div class="flow-block fill">引用块后的正文。</div>
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

    # Must PASS (blockquote exemption), NOT FAIL with a movable-figure hint.
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "narrow the figure" not in result.stdout, (
        "validator still reports a movable-figure defect for an image inside a "
        "protected blockquote — the 2026-06-25 false positive has regressed"
    )


def _write_figure_boundary_handout(path: Path, *, figure_fits_at_floor: bool) -> None:
    """Two variants of a figure-boundary page for the band-floor-anchored gate.

    Sheet 2 has a trailing blank; sheet 3 starts with an <img> figure. Both
    variants use the SAME square image (aspect 1.0, band floor ~19% of body ≈
    151px wide → 151px tall, the absolute narrowest the width band allows).
    The gap on sheet 2 is what differs:

    - figure_fits_at_floor=True: the gap is LARGE (~500px) so the floor-width
      figure (151px tall) fits -> the gate must FAIL with a "narrow it to the
      band floor and let it move up" hint.
    - figure_fits_at_floor=False: the gap is SMALL (~120px, just above the 10%
      threshold) so even the floor-width figure (151px) does NOT fit -> the
      gate must EXEMPT (PASS), because narrowing the figure further would
      leave the width band.
    """
    svg = (
        "data:image/svg+xml;utf8,"
        "<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>"
        "<rect width='200' height='200' fill='%23ccc'/></svg>"
    )
    # Image rendered WIDE (so currentFrac > floor and the "narrow to floor"
    # path is exercised): 400px square on a 794px body ≈ 50% body width.
    img_width = "400px"
    # sheet 2 has ONE content block whose height sets the trailing gap
    # (= body_height 1000px − block_height). LARGE gap (~500px trailing) when
    # the floor-width figure fits; SMALL gap (~120px trailing, just over the
    # 10% threshold) when even the floor-width figure is too tall.
    content_block_height = "500px" if figure_fits_at_floor else "880px"
    path.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet {{ width: 794px; min-height: 1123px; }}
.sheet-body {{ height: 1000px; }}
.flow-block {{ height: 60px; }}
.flow-block.gap {{ height: {content_block_height}; }}
.flow-block.fill {{ height: 880px; }}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2">
    <section class="sheet-body"><div class="flow-block gap">正文，留下尾部空白。</div></section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body">
      <figure style="margin:0;"><img src="{svg}" style="width:{img_width};height:auto;display:block;" alt="fig"/></figure>
      <div class="flow-block fill">图后正文，填充页面避免无关的尾部空白。</div>
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
def test_bottom_margin_fails_figure_that_could_fit_at_band_floor(tmp_path: Path) -> None:
    """A figure whose band-floor width (the narrowest the width band allows)
    would fit in the trailing gap is a movable defect: the gate FAILs and tells
    the model to narrow it to the band floor and move it up."""
    html = tmp_path / "handout.html"
    _write_figure_boundary_handout(html, figure_fits_at_floor=True)

    result = _run_validator(html)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "Sheet 2" in result.stdout
    assert "could fit" in result.stdout
    assert "narrow the figure" in result.stdout


@pytest.mark.skipif(not _playwright_ready(), reason="Playwright chromium is not available")
def test_bottom_margin_exempts_figure_that_cannot_fit_at_band_floor(tmp_path: Path) -> None:
    """A figure whose band-floor width is still too tall for the (small)
    trailing gap is exempt: the blank is the unavoidable cost of the width-band
    floor — narrowing further would leave the band. The gate must PASS and not
    flag it (weak-model safety: stops the model from shrinking past the band)."""
    html = tmp_path / "handout.html"
    _write_figure_boundary_handout(html, figure_fits_at_floor=False)

    result = _run_validator(html)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
    assert "cannot fit" in result.stdout


def _write_kimi_loop_handout(path: Path, img_width: str) -> None:
    """The exact Kimi 2026-06 failure scenario: a MIDDLE page (sheet 2) with a
    large trailing gap, and the next sheet (3) starts with a tall image figure.

    The image is square (aspect 1.0, band floor ~19% of body). ``img_width``
    controls how the image is CURRENTLY rendered — the test runs this twice,
    once wide and once already-narrowed, to prove the band-floor-anchored
    estimate does NOT shrink when the image is narrowed (which is what closed
    the Kimi "shrink -> hint still satisfiable -> shrink again" loop).
    """
    svg = (
        "data:image/svg+xml;utf8,"
        "<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'>"
        "<rect width='200' height='200' fill='%23ccc'/></svg>"
    )
    path.write_text(
        f"""<!doctype html>
<html data-handout-ready="true">
<head>
<meta charset="utf-8">
<style>
.sheet {{ width: 794px; min-height: 1123px; }}
.sheet-body {{ height: 1000px; }}
.flow-block {{ height: 60px; }}
.flow-block.gap {{ height: 120px; }}
.flow-block.fill {{ height: 880px; }}
</style>
</head>
<body>
<main id="handout-print-root">
  <article class="sheet" data-page-number="1">
    <section class="sheet-body"><div class="flow-block">cover</div></section>
  </article>
  <article class="sheet" data-page-number="2">
    <section class="sheet-body"><div class="flow-block gap">正文，留下大尾部空白。</div></section>
  </article>
  <article class="sheet" data-page-number="3">
    <section class="sheet-body">
      <figure style="margin:0;"><img src="{svg}" style="width:{img_width};height:auto;display:block;" alt="fig"/></figure>
      <div class="flow-block fill">图后正文。</div>
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
def test_bottom_margin_band_floor_estimate_is_invariant_under_shrinking(tmp_path: Path) -> None:
    """Regression for the Kimi 2026-06 infinite-shrink loop.

    The old heuristic estimated the figure's minimum height as 0.8x of its
    CURRENT rendered height. When a weak model followed the "narrow the figure"
    hint, the estimate shrank along with the image, so the hint stayed
    satisfiable forever and the model looped, shrinking the image until it was
    unreadable. The band-floor-anchored redesign must produce an estimate that
    is INVARIANT to how the image is currently rendered (it depends only on the
    aspect ratio and the absolute band floor). Run the same figure wide and
    narrow; both must report the same estHeightAtMin.
    """
    import re

    estimates = []
    for i, img_width in enumerate(("400px", "160px")):  # ~50% body, then ~20%
        html = tmp_path / f"handout_{i}.html"
        _write_kimi_loop_handout(html, img_width)
        result = _run_validator(html)
        # Both must FAIL with the figure-could-fit hint (the gap is large).
        assert result.returncode == 1, result.stdout + result.stderr
        m = re.search(r"est (\d+)px", result.stdout)
        assert m, f"could not parse est height from output:\n{result.stdout}"
        estimates.append(int(m.group(1)))

    # The core regression assertion: narrowing the image does NOT lower the
    # estimated minimum height. (They should be exactly equal because the
    # estimate is anchored to the absolute band floor, not the current size.)
    assert estimates[0] == estimates[1], (
        f"band-floor estimate shrank when image was narrowed "
        f"({estimates[0]}px -> {estimates[1]}px); the Kimi infinite-shrink "
        f"loop has regressed: the hint would stay satisfiable as the model "
        f"keeps shrinking the image."
    )
