# Scan Pdf To Print Html Kami Default Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scan-pdf-to-print-html` generate a Kami-based A4 handout by default, center table content horizontally and vertically, and document a pass-first sequential review gate.

**Architecture:** Vendor a small, local Kami CSS kernel into the skill so the generator no longer owns a one-off visual system. Keep OCR-specific page structure in `build_faithful_handout_html.py`, add centered table/media rules there, then update the skill docs to codify a preflight-first review path before sequential fresh-subagent page review.

**Tech Stack:** Python 3, `markdown-it-py`, static CSS assets, MathJax SVG, PowerShell 7, Edge headless export, pytest

---

## File Structure

- Create: `custom/scan-pdf-to-print-html/assets/kami-default-kernel.css`
  - Responsibility: vendored Kami token and base editorial rules used by the generator at runtime
- Create: `custom/scan-pdf-to-print-html/references/review-gate.md`
  - Responsibility: explicit pass-first review workflow for this skill, including preflight, artifact rebuild, and sequential page review
- Modify: `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py`
  - Responsibility: load local Kami kernel, apply OCR-specific print rules, preserve MathJax SVG, center table content, keep image cleanup behavior
- Modify: `custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py`
  - Responsibility: lock Kami default tokens, centered table behavior, MathJax SVG, and image-frame suppression
- Modify: `custom/scan-pdf-to-print-html/SKILL.md`
  - Responsibility: describe the new default Kami kernel and the required preflight-first review gate

## Task 1: Vendor The Kami Default Kernel And Wire It Into The Generator

**Files:**
- Create: `custom/scan-pdf-to-print-html/assets/kami-default-kernel.css`
- Modify: `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py`
- Test: `custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py`

- [ ] **Step 1: Write the failing test for Kami default tokens**

Add this test to `custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py`:

```python
def test_uses_kami_default_paper_tokens(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text("## Page 1\n\nKami token smoke test\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "--bg: #f5f4ed;" in html
    assert "--accent: #1b365d;" in html
    assert "Charter" in html
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
py -3 -m pytest C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\tests\test_build_faithful_handout_html.py::test_uses_kami_default_paper_tokens -v
```

Expected:

- `FAIL`
- the generated HTML does not yet contain `--bg: #f5f4ed;`

- [ ] **Step 3: Add the local Kami kernel asset and load it from the generator**

Create `custom/scan-pdf-to-print-html/assets/kami-default-kernel.css` with the vendored base tokens and page primitives:

```css
:root {
  --bg: #f5f4ed;
  --surface: #faf9f5;
  --surface-warm: #e8e6dc;
  --fg: #141413;
  --fg-2: #3d3d3a;
  --muted: #504e49;
  --meta: #6b6a64;
  --border: #e8e6dc;
  --border-soft: #e5e3d8;
  --accent: #1b365d;
  --accent-on: #faf9f5;
  --accent-light: #2d5a8a;
  --accent-hover: var(--accent);
  --accent-active: #142a48;
  --font-display: Charter, Georgia, Palatino, "Times New Roman", serif;
  --font-body: Charter, Georgia, Palatino, "Times New Roman", serif;
  --font-mono: "JetBrains Mono", "SF Mono", "Fira Code", Consolas, Monaco, "TsangerJinKai02", "Source Han Serif SC", monospace;
  --text-sm: 12px;
  --text-base: 14px;
  --text-lg: 17px;
  --text-xl: 22px;
  --text-2xl: 32px;
  --leading-display: 1.1;
  --leading-tight: 1.25;
  --leading-body: 1.55;
  --tracking-display: -1.2px;
  --tracking-label: 0.4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --elev-ring: 0 0 0 1px var(--border);
  --elev-raised: 0 4px 24px rgba(0, 0, 0, 0.05);
}

* {
  box-sizing: border-box;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

html,
body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--fg);
  font-family: var(--font-body);
}

strong {
  font-weight: 500;
}
```

Then refactor `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py` so the CSS is loaded from that file:

```python
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def read_asset_text(name: str) -> str:
    asset_path = ASSETS_DIR / name
    if not asset_path.exists():
        raise SystemExit(f"CSS asset not found: {asset_path}")
    return asset_path.read_text(encoding="utf-8").strip()


KAMI_KERNEL_CSS = read_asset_text("kami-default-kernel.css")
```

And replace the inline style assembly in `build_html_document(...)`:

```python
            "  <style>",
            KAMI_KERNEL_CSS,
            OCR_PRINT_CSS,
            "  </style>",
```

- [ ] **Step 4: Run the targeted token test and the existing suite**

Run:

```bash
py -3 -m pytest C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\tests\test_build_faithful_handout_html.py::test_uses_kami_default_paper_tokens -v
py -3 -m pytest C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\tests\test_build_faithful_handout_html.py -v
```

Expected:

- first command: `PASS`
- second command: all tests still `PASS`

- [ ] **Step 5: Commit the Kami kernel wiring**

```bash
git -C C:\Users\lt\Desktop\Write\custom-project\my-skills add custom/scan-pdf-to-print-html/assets/kami-default-kernel.css custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py
git -C C:\Users\lt\Desktop\Write\custom-project\my-skills commit -m "feat: vendor Kami default kernel for scan pdf handouts"
```

## Task 2: Center Table Content And Keep Formula / Media Cells Stable

**Files:**
- Modify: `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py`
- Modify: `custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py`

- [ ] **Step 1: Write the failing test for centered table cells**

Add this test to `custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py`:

```python
def test_centers_table_cells_for_text_formula_and_media(tmp_path: Path) -> None:
    source_md = tmp_path / "source-transcript.md"
    out_html = tmp_path / "handout.html"
    source_md.write_text(
        "\n".join(
            [
                "## Page 1",
                "",
                "| 类型 | 内容 |",
                "| --- | --- |",
                r"| 符号语言 | \( a // b \) |",
                "| 图形语言 | ![图 1](./images/example.png) |",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--md",
            str(source_md),
            "--out-html",
            str(out_html),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    html = out_html.read_text(encoding="utf-8")

    assert "text-align: center;" in html
    assert "vertical-align: middle;" in html
    assert 'mjx-container[jax="SVG"]' in html
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
py -3 -m pytest C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\tests\test_build_faithful_handout_html.py::test_centers_table_cells_for_text_formula_and_media -v
```

Expected:

- `FAIL`
- the generated CSS still reflects left/top table alignment

- [ ] **Step 3: Add centered table and media rules**

In `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py`, replace the table rules in the OCR-specific CSS block with:

```python
OCR_PRINT_CSS = """
@page {
  size: A4;
  margin: 0;
}

body {
  background: radial-gradient(circle at top, #f8f6ef 0%, var(--bg) 58%, #ece8dc 100%);
  font-size: var(--text-base);
  line-height: var(--leading-body);
}

.transcript-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 3mm 0 4mm;
  font-size: 11.4px;
  background: var(--surface);
  table-layout: fixed;
}

.transcript-body th,
.transcript-body td {
  padding: 2.8mm 3mm;
  border: 1px solid var(--border);
  text-align: center;
  vertical-align: middle;
}

.transcript-body th {
  color: var(--fg-2);
  background: var(--surface-warm);
}

.transcript-body td img,
.transcript-body td mjx-container[jax="SVG"] {
  display: block;
  margin-inline: auto;
}
"""
```

Keep the existing image-frame removal rules and MathJax SVG bootstrap unchanged.

- [ ] **Step 4: Run the focused tests and the full generator suite**

Run:

```bash
py -3 -m pytest C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\tests\test_build_faithful_handout_html.py::test_centers_table_cells_for_text_formula_and_media -v
py -3 -m pytest C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\tests\test_build_faithful_handout_html.py -v
```

Expected:

- both commands `PASS`
- existing MathJax SVG and image-frame regression tests remain green

- [ ] **Step 5: Commit the centered table rules**

```bash
git -C C:\Users\lt\Desktop\Write\custom-project\my-skills add custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py
git -C C:\Users\lt\Desktop\Write\custom-project\my-skills commit -m "feat: center OCR handout table content by default"
```

## Task 3: Document The Review Gate And Verify A Real OCR Artifact

**Files:**
- Create: `custom/scan-pdf-to-print-html/references/review-gate.md`
- Modify: `custom/scan-pdf-to-print-html/SKILL.md`
- Modify: `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py`

- [ ] **Step 1: Add the review-gate reference document**

Create `custom/scan-pdf-to-print-html/references/review-gate.md`:

```md
# Review Gate

Use this default order before hand-off:

1. Run generator unit tests.
2. Rebuild the real `handout.html`.
3. Run `validate_job_state.py --require-html`.
4. Export a fresh screenshot and PDF from the rebuilt HTML.
5. Check the known failure classes before asking a reviewer:
   - formulas visible
   - tables centered
   - image cells frameless
   - no obvious overflow or clipping
6. If `knowledge-to-print-html` review tooling is available, run its page-review packet generation.
7. Review page 1 with a fresh reviewer subagent.
8. Fix page 1 and revalidate before page 2.
9. Continue sequentially until all pages pass.
```

- [ ] **Step 2: Update the skill contract**

Patch `custom/scan-pdf-to-print-html/SKILL.md` so the default path and validation language become:

```md
This skill now prefers `Doc2X API` as the OCR engine, and uses a local `Kami`-based print kernel as the default page language.

Default path:

`Doc2X OCR -> local job files -> Kami fidelity layout -> review gate -> A4 HTML/PDF`
```

And update the validation section to explicitly reference the local gate:

```md
- Run `scripts/validate_job_state.py` on the job directory.
- Follow `references/review-gate.md` before asking any page reviewer to approve the output.
- Use the downstream print validators from `knowledge-to-print-html` when available.
```

- [ ] **Step 3: Make the OCR stylesheet split obvious in code**

Add a short comment near the CSS composition in `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py`:

```python
# Vendored Kami tokens define the document language.
# OCR_PRINT_CSS keeps scan-specific pagination, table, and media behavior local to this skill.
```

- [ ] **Step 4: Run tests and rebuild the real page-274 Doc2X sample**

Run:

```bash
py -3 -m pytest C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\tests\test_build_faithful_handout_html.py -v
py -3 C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\scripts\build_faithful_handout_html.py --md C:\Users\lt\Documents\Codex\2026-06-08\codex\work\mst-page-274\doc2x-job\source-transcript.md --out-html C:\Users\lt\Documents\Codex\2026-06-08\codex\work\mst-page-274\doc2x-job\handout.html --title "知识盒二 线面平行与面面平行" --source-label "Doc2X OCR"
py -3 C:\Users\lt\Desktop\Write\custom-project\my-skills\custom\scan-pdf-to-print-html\scripts\validate_job_state.py C:\Users\lt\Documents\Codex\2026-06-08\codex\work\mst-page-274\doc2x-job --require-html
& 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --headless --disable-gpu --virtual-time-budget=10000 --window-size=1400,2200 --screenshot=C:\Users\lt\Documents\Codex\2026-06-08\codex\work\mst-page-274\doc2x-job\handout-render.png "file:///C:/Users/lt/Documents/Codex/2026-06-08/codex/work/mst-page-274/doc2x-job/handout.html"
& 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --headless --disable-gpu --virtual-time-budget=10000 --print-to-pdf=C:\Users\lt\Documents\Codex\2026-06-08\codex\work\mst-page-274\doc2x-job\handout.pdf --no-pdf-header-footer "file:///C:/Users/lt/Documents/Codex/2026-06-08/codex/work/mst-page-274/doc2x-job/handout.html"
```

Expected:

- pytest suite `PASS`
- `OK: validated scan job at ...doc2x-job`
- Edge reports bytes written for both PNG and PDF
- the screenshot shows visible formulas and centered table rows

- [ ] **Step 5: Commit the docs and review-gate updates**

```bash
git -C C:\Users\lt\Desktop\Write\custom-project\my-skills add custom/scan-pdf-to-print-html/SKILL.md custom/scan-pdf-to-print-html/references/review-gate.md custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py
git -C C:\Users\lt\Desktop\Write\custom-project\my-skills commit -m "docs: add Kami review gate for scan pdf handouts"
```

## Self-Review

### Spec coverage

- Kami default kernel: Task 1
- centered table content: Task 2
- preserve MathJax SVG and image cleanup: Tasks 1 and 2
- pass-first sequential review gate: Task 3
- real OCR artifact verification: Task 3

### Placeholder scan

- No `TODO`, `TBD`, or “implement later”
- Every file path is explicit
- Every test and verification command is explicit
- Each code-changing step includes concrete code

### Type consistency

- CSS asset path is consistently `assets/kami-default-kernel.css`
- Python constant name is consistently `KAMI_KERNEL_CSS`
- OCR-specific CSS block is consistently `OCR_PRINT_CSS`

