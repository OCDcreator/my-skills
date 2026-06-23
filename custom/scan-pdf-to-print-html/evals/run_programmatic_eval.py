#!/usr/bin/env python3
"""Lightweight programmatic regression eval for scan-pdf-to-print-html.

Runs build + postprocess on each fixture, then asserts DOM contracts via
Playwright. NO subagents, NO LLM grading — pure Python + browser DOM checks.
Designed to catch code-logic regressions (postprocess regex, pagination,
cover injection) in seconds, so any edit to scripts/ can be verified fast.

This complements (does not replace) skill-creator's full eval flow, which is
for big-version checkups. Use THIS for daily regression after any script edit.

Usage:
    python3 evals/run_programmatic_eval.py            # run all evals
    python3 evals/run_programmatic_eval.py --only 1   # run eval id 1
    python3 evals/run_programmatic_eval.py --keep-tmp # keep tmp job dirs for inspection

Exit code = number of failed assertions (0 = all green).

Eval cases are declared in evals/evals.json (compatible with skill-creator's
schema, so fixtures + expectations can be reused by the full flow later).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError as exc:
    raise SystemExit(
        "Playwright is required. Install with: pip install playwright && playwright install chromium\n"
        f"Details: {exc}"
    ) from exc


SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_ROOT / "scripts"
EVALS_DIR = SKILL_ROOT / "evals"
BUILD = SCRIPTS / "build_faithful_handout_html.py"
POSTPROCESS = SCRIPTS / "postprocess_handout_for_contract.py"
EXAMPLE_GATE = SCRIPTS / "validate_example_blockquote_coverage.py"

# Regex to count example labels in a fixture's source markdown. Matches both
# bare-paragraph labels (行首例题N) AND callout-title labels (e.g. the
# `例题1` inside `> [!question] 例题1`), so the count reflects every example
# regardless of how it was authored. Mirrors the gate's EXAMPLE_LABEL_PATTERN
# but broadened to catch callout titles (which the gate treats as already-
# wrapped, so it doesn't flag them — but for counting blockquotes we need them).
EXAMPLE_LABEL_RE = re.compile(
    r"(?:例题|练习)\s*[0-9一二三四五六七八九十百零两]+",
)


def run_script(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Run a script, return (exit_code, combined_output). Raises on non-zero."""
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{out}")
    return proc.returncode, out


class Assertion:
    """A single verifiable claim with a PASS/FAIL result and evidence."""

    def __init__(self, text: str):
        self.text = text
        self.passed = False
        self.evidence = ""

    def fail(self, evidence: str) -> None:
        self.passed = False
        self.evidence = evidence

    def ok(self, evidence: str = "") -> None:
        self.passed = True
        self.evidence = evidence


def build_and_postprocess(fixture_md: Path, job_dir: Path, cover_src: Path | None) -> Path:
    """Copy fixture into job dir, run build + postprocess, return handout.html path.

    If cover_src is given, copy it as concept-map.svg so inject_cover_metadata
    picks it up (it keys on exactly that filename).
    """
    transcript = job_dir / "source-transcript.md"
    shutil.copyfile(fixture_md, transcript)
    if cover_src is not None:
        shutil.copyfile(cover_src, job_dir / "concept-map.svg")

    html_path = job_dir / "handout.html"
    # Use sys.executable so the same python that imports playwright runs the
    # builder scripts (they also need playwright at render time).
    run_script([sys.executable, str(BUILD), "--md", str(transcript), "--out-html", str(html_path)], job_dir)
    run_script([sys.executable, str(POSTPROCESS), "--html", str(html_path)], job_dir)
    return html_path


def wait_for_handout_ready(page) -> None:
    """Mirror render_html_to_pdf.py's engine-agnostic math wait."""
    page.wait_for_function(
        "document.documentElement.dataset.handoutReady === 'true'",
        timeout=60_000,
    )
    page.wait_for_function(
        "document.fonts && document.fonts.status === 'loaded'",
        timeout=60_000,
    )


# ---------------------------------------------------------------------------
# Per-eval DOM assertion bundles. Each returns a list[Assertion].
# ---------------------------------------------------------------------------


def assert_example_blockquote(job_dir: Path, html_path: Path, fixture_md: Path) -> list[Assertion]:
    """Eval 1: every example label is wrapped in .phycat-blockquote after build.

    Also runs the pre-build gate directly on the fixture to confirm it reports
    bare-paragraph examples (the gate is the source-side defense).
    """
    assertions: list[Assertion] = []

    # Source-side: count example labels in the fixture.
    md_text = fixture_md.read_text(encoding="utf-8")
    label_count = len(EXAMPLE_LABEL_RE.findall(md_text))

    # Pre-build gate: it should report the deliberately-bare example (例题3).
    gate = Assertion("pre-build gate reports bare-paragraph example labels")
    proc = subprocess.run(
        [sys.executable, str(EXAMPLE_GATE), "--md", str(fixture_md)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 and "例题3" in proc.stdout:
        gate.ok(f"gate exit={proc.returncode}, reported 例题3: {proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ''}")
    else:
        gate.fail(f"gate exit={proc.returncode}; expected 例题3 flagged. stdout={proc.stdout.strip()[:200]}")
    assertions.append(gate)

    # Post-build: NO example label may render as a bare paragraph OUTSIDE a
    # .phycat-blockquote. This is the real contract — postprocess's job is to
    # leave zero bare example paragraphs. (Counting blockquote-vs-label is
    # unreliable: one example may reference its own label mid-prose, and
    # mergeExampleRuns can combine adjacent examples. The "no bare <p> outside
    # any blockquote ancestor" check is the faithful contract.)
    bq = Assertion("no example label renders as a bare <p> outside a .phycat-blockquote")
    _ = label_count  # kept for potential future use; the contract is "zero bare", not "count match"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        wait_for_handout_ready(page)
        bq_count = page.evaluate("() => document.querySelectorAll('.phycat-blockquote').length")
        bare_outside = page.evaluate(
            """() => {
                const ps = Array.from(document.querySelectorAll('.transcript-flow p'));
                return ps
                    .filter(p => !p.closest('.phycat-blockquote'))
                    .filter(p => /^\\s*(?:例题|练习)\\s*[0-9一二三四五六七八九十百零]/.test(p.textContent))
                    .map(p => p.textContent.trim().slice(0, 60));
            }"""
        )
        if not bare_outside:
            bq.ok(f"{bq_count} .phycat-blockquote present; 0 bare example <p> outside blockquotes")
        else:
            bq.fail(f"{len(bare_outside)} bare example <p> outside blockquotes: {bare_outside[:3]}")
        browser.close()
    assertions.append(bq)

    # Analysis (解析) must NOT be inside a blockquote.
    analysis = Assertion("解析 paragraphs render OUTSIDE blockquotes")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        wait_for_handout_ready(page)
        leaked = page.evaluate(
            """() => {
                const quotes = Array.from(document.querySelectorAll('.phycat-blockquote'));
                let hits = [];
                for (const q of quotes) {
                    const ps = q.querySelectorAll('p');
                    for (const p of ps) {
                        if (/解析[:：]/.test(p.textContent)) hits.push(p.textContent.trim().slice(0, 50));
                    }
                }
                return hits;
            }"""
        )
        if not leaked:
            analysis.ok("no 解析 paragraph found inside any .phycat-blockquote")
        else:
            analysis.fail(f"解析 leaked into blockquote: {leaked[:3]}")
        browser.close()
    assertions.append(analysis)

    return assertions


def assert_cover_injection(job_dir: Path, html_path: Path, fixture_md: Path) -> list[Assertion]:
    """Eval 2: concept-map.svg is injected as the first A4 cover sheet.

    fixture_md is accepted for signature parity with the other assert_* functions
    (the dispatch passes it uniformly) but unused here — cover assertions depend
    only on the post-build HTML, not the source markdown.
    """
    _ = fixture_md  # signature parity; intentionally unused
    assertions: list[Assertion] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        wait_for_handout_ready(page)

        cover = Assertion("first .sheet is a marked cover (concept-map-sheet + data-sheet-role=cover)")
        first_sheet = page.evaluate(
            """() => {
                const s = document.querySelector('.sheet');
                if (!s) return null;
                return {
                    classes: s.className,
                    role: s.dataset.sheetRole || null,
                    isCover: s.classList.contains('concept-map-sheet'),
                };
            }"""
        )
        if first_sheet and first_sheet.get("isCover") and first_sheet.get("role") == "cover":
            cover.ok(f"first sheet: {first_sheet['classes']}, role={first_sheet['role']}")
        else:
            cover.fail(f"first sheet not a marked cover: {first_sheet}")
        assertions.append(cover)

        img = Assertion("cover sheet contains an <img> pointing at the SVG")
        img_info = page.evaluate(
            """() => {
                const cover = document.querySelector('.sheet.concept-map-sheet');
                if (!cover) return null;
                const i = cover.querySelector('img');
                return i ? { src: i.getAttribute('src'), cls: i.className } : null;
            }"""
        )
        if img_info and "concept-map" in (img_info.get("src") or ""):
            img.ok(f"cover img src={img_info['src']}")
        else:
            img.fail(f"no cover <img> pointing at SVG: {img_info}")
        assertions.append(img)

        browser.close()
    return assertions


def assert_chapter_pagination(job_dir: Path, html_path: Path, fixture_md: Path) -> list[Assertion]:
    """Eval 3: each chapter h2 (except the first) starts a new sheet, and the
    preceding sheet is marked data-ends-before-lecture."""
    assertions: list[Assertion] = []

    # Count chapter headings in the source (第N章/节 shaped h2).
    md_text = fixture_md.read_text(encoding="utf-8")
    chapter_count = len(re.findall(r"^##\s*第[0-9一二三四五六七八九十百零]+[章节]", md_text, re.MULTILINE))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="networkidle")
        wait_for_handout_ready(page)

        # Map: for each sheet, does its first content flow-block start with a chapter h2?
        sheets = page.evaluate(
            """() => {
                const sheets = Array.from(document.querySelectorAll('.sheet'));
                return sheets.map((s, i) => {
                    const body = s.querySelector('.sheet-body');
                    if (!body) return { idx: i, role: s.dataset.sheetRole || null, endsLecture: s.dataset.endsBeforeLecture === 'true', firstH2: null };
                    const firstBlock = body.querySelector(':scope > .flow-block');
                    let firstH2 = null;
                    if (firstBlock) {
                        const h2 = firstBlock.querySelector(':scope > h2');
                        if (h2) firstH2 = h2.textContent.trim();
                    }
                    return { idx: i, role: s.dataset.sheetRole || null, endsLecture: s.dataset.endsBeforeLecture === 'true', firstH2 };
                });
            }"""
        )

        # Assertion A: each chapter h2 (except the first) begins its own sheet.
        starts = Assertion(f"each of {chapter_count} chapter h2(s) except the first begins a new sheet")
        chapter_sheets = [s for s in sheets if s["firstH2"] and re.match(r"第[0-9一二三四五六七八九十百零]+[章节]", s["firstH2"])]
        # The first chapter may share a sheet with prior content; subsequent chapters
        # should each be the FIRST content of their sheet (which chapter_sheets captures).
        if len(chapter_sheets) >= chapter_count:
            starts.ok(f"{len(chapter_sheets)} sheets start with a chapter h2 (>= {chapter_count} chapters)")
        else:
            starts.fail(f"only {len(chapter_sheets)} sheets start with chapter h2, expected >= {chapter_count}; sheets={[(s['idx'], s['firstH2']) for s in sheets if s['firstH2']]}")
        assertions.append(starts)

        # Assertion B: the sheet BEFORE each non-first chapter is marked ends-before-lecture.
        marked = Assertion("sheet before each non-first chapter h2 is marked data-ends-before-lecture")
        unmarked = []
        for s in chapter_sheets:
            prev_idx = s["idx"] - 1
            if prev_idx < 0:
                continue  # first chapter, no predecessor to mark
            prev = sheets[prev_idx] if prev_idx < len(sheets) else None
            if not prev or not prev["endsLecture"]:
                unmarked.append((prev_idx, s["firstH2"]))
        if not unmarked:
            marked.ok(f"all {len(chapter_sheets) - (1 if chapter_sheets else 0)} predecessor sheet(s) marked")
        else:
            marked.fail(f"predecessor sheets NOT marked ends-before-lecture: {unmarked}")
        assertions.append(marked)

        # Assertion C (NEGATIVE — the one pytest caught that this eval originally
        # missed): a NON-chapter-shaped h2 (e.g. "大招总结", "补充说明") must NOT
        # cause its predecessor to be marked ends-before-lecture. If the exemption
        # is too broad (any h2 triggers it), generic exposition h2 escapes the
        # trailing-blank check. This guards against re-widening the exemption.
        non_chapter = Assertion("non-chapter h2 (e.g. 大招总结) does NOT mark its predecessor ends-before-lecture")
        non_chapter_re = re.compile(
            r"^(?:第\s*[0-9一二三四五六七八九十百零]+\s*(?:讲|章|节|部分|篇|单元)|单元\s*[0-9一二三四五六七八九十百零]+|[0-9]+\s*[\.、]\s*[\u4e00-\u9fff]|(?:Module|Lesson|Chapter)\s+\d)"
        )
        falsely_marked = []
        for s in sheets:
            if not s["firstH2"]:
                continue
            if non_chapter_re.match(s["firstH2"]):
                continue  # chapter-shaped — its predecessor SHOULD be marked, covered by Assertion B
            # non-chapter h2: its predecessor must NOT be marked ends-before-lecture
            prev_idx = s["idx"] - 1
            if prev_idx < 0:
                continue
            prev = sheets[prev_idx] if prev_idx < len(sheets) else None
            if prev and prev["endsLecture"]:
                falsely_marked.append((prev_idx, s["firstH2"]))
        if not falsely_marked:
            non_chapter.ok("no non-chapter h2 caused a false ends-before-lecture mark")
        else:
            non_chapter.fail(f"non-chapter h2 falsely marked predecessor: {falsely_marked} (exemption too broad)")
        assertions.append(non_chapter)

        browser.close()
    return assertions


EVAL_DISPATCH = {
    "example-blockquote-coverage": assert_example_blockquote,
    "svg-cover-injection": assert_cover_injection,
    "chapter-h2-pagination": assert_chapter_pagination,
}


def run_eval(eval_spec: dict, keep_tmp: bool) -> list[Assertion]:
    name = eval_spec["name"]
    fixture = EVALS_DIR / eval_spec["fixture"]
    cover_src = EVALS_DIR / eval_spec["cover_fixture"] if eval_spec.get("cover_fixture") else None

    tmp_root = Path(tempfile.mkdtemp(prefix=f"scan-eval-{name}-"))
    try:
        html_path = build_and_postprocess(fixture, tmp_root, cover_src)
        fn = EVAL_DISPATCH[name]
        return fn(tmp_root, html_path, fixture)
    finally:
        if keep_tmp:
            print(f"  [kept tmp] {tmp_root}")
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", type=int, help="run only the eval with this id")
    parser.add_argument("--keep-tmp", action="store_true", help="keep temp job dirs for inspection")
    args = parser.parse_args()

    evals_path = EVALS_DIR / "evals.json"
    spec = json.loads(evals_path.read_text(encoding="utf-8"))
    evals = spec["evals"]
    if args.only is not None:
        evals = [e for e in evals if e["id"] == args.only]
        if not evals:
            print(f"No eval with id={args.only}")
            return 1

    total_failures = 0
    for ev in evals:
        print(f"\n=== Eval {ev['id']}: {ev['name']} ===")
        try:
            assertions = run_eval(ev, args.keep_tmp)
        except Exception as exc:  # noqa: BLE001 — surface build/postprocess failures clearly
            print(f"  ERROR (build/postprocess failed): {exc}")
            total_failures += 1
            continue

        for a in assertions:
            mark = "PASS" if a.passed else "FAIL"
            print(f"  [{mark}] {a.text}")
            if not a.passed:
                print(f"         evidence: {a.evidence}")
            elif a.evidence:
                print(f"         {a.evidence}")
        total_failures += sum(1 for a in assertions if not a.passed)

    print(f"\n{'=' * 50}")
    if total_failures == 0:
        print("ALL EVALS PASS")
    else:
        print(f"{total_failures} assertion(s) FAILED")
    return total_failures


if __name__ == "__main__":
    raise SystemExit(main())
