---
name: scan-pdf-to-print-html
description: Use when scanned or image-only PDFs need high-fidelity OCR into reusable Markdown/HTML/PDF without rewriting the original content, especially for textbooks, notes, worksheets, formulas, tables, diagrams, question-and-answer pages, or blurry math scans that should go through a Doc2X-backed OCR pipeline before A4 print layout.
---

# Scan Pdf To Print Html

## Overview

Turn a scanned or image-only PDF into a reusable OCR job, a faithful `source-transcript.md`, and a print-ready `handout.html` / PDF while keeping the source content faithful. Improve layout, spacing, and styling, but do not rewrite, summarize, expand, simplify, or teach the content unless the user explicitly asks for adaptation.

This skill uses a local `Kami`-based print kernel as the default page language.

This skill now prefers `Doc2X API` as the OCR engine. Local page rendering and cleanup scripts remain available as fallback or for visual review, and the default path is:

`Doc2X OCR -> local job files -> Kami fidelity layout -> review gate -> A4 HTML/PDF`

This skill is now mature enough to treat the following as hard guardrails, not suggestions:

- `source-transcript.md` is the canonical page-level handoff file
- Doc2X export markdown stays under `doc2x/export/` for reference and must not replace the canonical transcript
- the default page kernel is the bundled local `Kami` asset, not a sibling design repo at runtime
- table cells default to centered content, but inline formulas must remain inline and only display math may be block-centered
- real verification must happen before page-review subagents are asked to approve the output

## Hard Rule: Fidelity First

Never improve the content by default.

- Preserve headings, numbering, question order, answer order, tables, formulas, and figure references.
- Preserve the source language unless the user explicitly asks for translation.
- Preserve omissions and ambiguity. If a character or symbol is unreadable, mark it as `[TO VERIFY: ...]` instead of guessing.
- Preserve meaning over appearance, and preserve appearance over convenience.
- Improve layout only: page composition, typography, whitespace, callouts, figure placement, and print styling are allowed to change.
- Do not convert source material into a summary, notes, study guide, or explanation unless the user explicitly changes the goal.

Read `references/fidelity-rules.md` before drafting the transcript.

## Working Contract

Use the files and folders from `references/working-contract.md`.

The standard output set is:

- `job.json`
- `doc2x/`
- `source-transcript.md`
- `layout-brief.md`
- `handoff-notes.md`
- `handout.html`
- optional `pages/`
- optional `pages-clean/`
- optional `diagrams/`
- optional `tables/`

Initialize a Doc2X-backed job with:

```bash
py -3 scripts/doc2x_parse_job.py --pdf "C:\path\scan.pdf" --out-dir "C:\path\job"
```

## Workflow

### 1. Run Doc2X OCR first

- Use `scripts/doc2x_parse_job.py` as the default entrypoint.
- It handles:
  - `POST /api/v2/parse/preupload`
  - `HTTP PUT` file upload
  - `GET /api/v2/parse/status` polling
  - optional `POST /api/v2/convert/parse`
  - optional `GET /api/v2/convert/parse/result`
  - local download of the export artifact
- Prefer model `v3-2026` unless you have a compatibility reason to stay on `v2`.
- Keep `formula_level=0` by default for fidelity. Only degrade formulas intentionally.
- Keep the page-level parse transcript as the canonical `source-transcript.md`.
- If Doc2X also produces export markdown, keep it under `doc2x/export/export.md` for reference instead of replacing the canonical transcript.

Examples:

```bash
py -3 scripts/doc2x_parse_job.py --pdf "C:\books\chapter1.pdf" --out-dir "C:\jobs\chapter1"
py -3 scripts/doc2x_parse_job.py --pdf "C:\books\chapter1.pdf" --out-dir "C:\jobs\chapter1" --model v3-2026 --to md --formula-mode normal --formula-level 0
py -3 scripts/doc2x_parse_job.py --pdf "C:\books\chapter1.pdf" --out-dir "C:\jobs\chapter1" --model v3-2026 --to md --render-pages --render-dpi 260
```

Read `references/doc2x-api.md` before changing API-related behavior.

### 2. Use local rendering only when it helps review or recovery

- If the Doc2X output needs visual checking against the source, add `--render-pages`.
- If a page is low-contrast, yellowed, noisy, or slightly blurry, generate a cleaned copy in `pages-clean/`.
- Use local rendering when:
  - you need a human-readable page preview
  - you need to crop a source figure for fidelity comparison
  - Doc2X returned a suspicious formula or table and you want to inspect the original pixels
- Do not make local rendering the primary OCR path unless Doc2X is unavailable.

Fallback examples:

```bash
py -3 scripts/prepare_scan_page.py --input "C:\jobs\chapter1\pages\page-001.png" --output "C:\jobs\chapter1\pages-clean\page-001.clean.png"
py -3 scripts/prepare_scan_page.py --input "C:\jobs\chapter1\pages\page-002.png" --output "C:\jobs\chapter1\pages-clean\page-002.clean.png" --upscale 2.2 --sharpen 1.8 --median-size 1
```

### 3. Treat `source-transcript.md` as the source-of-truth handoff file

- `scripts/doc2x_parse_job.py` writes `source-transcript.md` from Doc2X page-level markdown.
- Keep that file faithful and reviewable. It is the canonical bridge between OCR and layout.
- If you later edit `source-transcript.md`, preserve:
  - titles and headings
  - paragraph order
  - lists and numbering
  - question blocks and answers
  - formulas
  - tables
  - figure references and labels
- Keep page boundaries visible unless the user explicitly wants a cross-page merged clean copy.
- When Doc2X already produced a useful export markdown file, keep it under `doc2x/export/` for reference rather than silently replacing the transcript logic.
- Future edits to the workflow must preserve this boundary: page-level parse output is canonical, export markdown is supplemental.

### 4. Review formulas, tables, and figures conservatively

Read `references/figure-policy.md` before touching figures.

#### Formulas

- Prefer Doc2X's structured formula output first.
- Keep `formula_level=0` unless the user explicitly prefers degraded plain text formulas.
- If a formula still looks wrong, compare it against the rendered page before fixing it.

#### Tables

- Prefer Doc2X's table reconstruction first.
- If Doc2X merges a table incorrectly, preserve the issue in `handoff-notes.md` and only apply manual cleanup when you can verify the source page visually.
- Use `merge_cross_page_forms=false` by default for page-faithful jobs. Enable it intentionally when the user wants continuous tables over strict page fidelity.
- The default HTML output now centers table content horizontally and vertically.
- Keep inline formulas inline inside mixed text cells. Only display math should be block-centered inside table cells.

#### Figures and diagrams

- If Doc2X output references images or extracted assets, keep them in the local export directory.
- Reuse the source figure when you need exact visual fidelity.
- Crop or clean only when it improves readability without changing meaning.
- Redraw only when the user explicitly wants a clean reconstruction or when the source is too blurry to preserve the required information.
- A redraw must preserve labels, structure, geometry relationships, axis direction, line style, and visual intent.
- Do not replace a source figure with a different nicer diagram.

If a page contains a figure and you keep the figure outside live text, add a note near the transcript such as:

```md
[Figure on page 3: geometry diagram with points A, B, C, D, P, E, F; dashed hidden edges; keep original labels and relative layout.]
```

### 5. Write `layout-brief.md`

This file is for layout and styling instructions only.

Include:

- paper size: A4
- target reading mode: print-first
- typography preferences
- whether figures stay inline or span width
- any page-break rules

Do not include content rewriting instructions.

### 6. Build `handout.html`

Build the HTML locally with `scripts/build_faithful_handout_html.py` as the default and primary path, using the finished transcript and a strict fidelity brief. This script is the vendored Kami-based A4 handout builder and is the workflow contract for this skill.

- A4 print CSS
- local `Kami`-based print kernel as the default page language
- stable pagination
- semantic headings, lists, tables, and figure captions
- preserve transcript order exactly
- no inserted teaching copy, summaries, or commentary
- keep the bundled `Kami` asset as the runtime source of truth; do not switch this skill back to loading style tokens from an external sibling repo at runtime

If `knowledge-to-print-html` is available, treat it only as optional downstream validation, review assistance, or print-check help, and require it to preserve the locally built Kami-based handout rather than replace it.

### 7. Validate before finishing

- Follow `references/review-gate.md` as the default review sequence.
- Run preflight validation before any page-review subagent is asked to approve a page.
- Run `scripts/validate_job_state.py` on the job directory.
- If `pages/` exists, visually compare the source pages against `source-transcript.md` and `handout.html`.
- Review `doc2x/parse-status.json` and `doc2x/parse-result.json` if the OCR output looks suspicious.
- If print output is part of the task, run the downstream print validators from `knowledge-to-print-html` when available.
- Record unresolved ambiguities in `handoff-notes.md`.

## Maintenance Guardrails

Use these when updating this skill itself:

- Keep the skill self-contained. If `SKILL.md` references a script or reference file, that file should live inside this skill folder and be tracked with it.
- Keep `assets/kami-default-kernel.css` and the OCR-specific CSS behavior aligned. If one side changes token names, update the compatibility layer deliberately.
- Do not reintroduce a workflow where Doc2X export markdown overwrites `source-transcript.md`.
- Do not broaden table-cell MathJax centering back to all SVG math containers; only display math should be block-centered in cells.
- Before calling this skill “done”, rerun tests, rebuild a real OCR artifact, regenerate screenshot/PDF outputs, and only then proceed to fresh subagent review.

## Typical Requests

- "把这个扫描版 PDF 原模原样转成可打印 HTML，最后导出 PDF。"
- "Keep the original questions and answers exactly, but make the layout cleaner for A4 printing."
- "This scan is blurry. Reuse figures when possible and only redraw the unreadable geometry diagrams."
- "OCR this worksheet without rewriting the content."
- "Use Doc2X API for OCR, then turn the result into A4 HTML/PDF."
- "Parse this scanned math PDF with Doc2X and keep formulas and tables faithful."

## Resources

### scripts/

- `doc2x_parse_job.py`: run the Doc2X upload -> poll -> export -> download workflow and initialize the local OCR job
- `init_scan_job.py`: create the working directory and render page images
- `render_pdf_pages.py`: render selected PDF pages to PNG with a manifest
- `prepare_scan_page.py`: clean and enhance noisy scan images
- `build_faithful_handout_html.py`: build the local Kami-based A4 handout HTML from the canonical transcript
- `validate_job_state.py`: check whether the expected working files exist

### references/

- `doc2x-api.md`: Doc2X request flow, environment variables, and output behavior
- `fidelity-rules.md`: content-preservation rules
- `figure-policy.md`: when to reuse, clean, crop, or redraw scanned figures
- `review-gate.md`: default page-by-page validation and review order
- `working-contract.md`: job structure and required files
