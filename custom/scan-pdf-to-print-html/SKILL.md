---
name: scan-pdf-to-print-html
description: Use when scanned or image-only PDFs need Doc2X OCR into a faithful, auditable page transcript and then A4 HTML/PDF, OR when an already-clean markdown file must become a printable A4 HTML/PDF handout. Best for textbooks, notes, worksheets, formulas, tables, diagrams, and question pages where content must stay source-faithful. For OCR inputs, `source-transcript.md` must be audited before HTML assembly; for clean markdown inputs, skip OCR and assemble directly.
---

# Scan Pdf To Print Html

Produce a Doc2X-backed OCR job with:

- `doc2x/page-transcript.raw.md`: untouched raw page transcript
- `source-transcript.md`: canonical transcript to audit and edit
- `handout.html` and PDF: final print outputs

Never rewrite, summarize, teach, merge away page provenance, or silently replace the canonical transcript with export markdown.

## Hard Contract

These apply in **every** mode:

- `source-transcript.md` is the only transcript file allowed to feed HTML.
- The main thread must never one-shot the full transcript into final HTML.
- Reviewer subagents start only after real HTML, screenshot, and PDF exist.

### OCR Hard Contract (scanned / Doc2X jobs only)

The gates below apply **only** to scanned-PDF jobs that go through Doc2X OCR. Markdown-source jobs (already-clean markdown) skip them — see Markdown-Source Mode below.

- `doc2x/export/export.md` is reference-only, and should be localized to sibling `images/` assets whenever the Doc2X zip already contains matching local crops.
- `job.json.transcript_audit_status` starts at `pending`; HTML is blocked until it is `approved`.
- `job.json.transcript_structure_lint_status` starts at `pending`; run the transcript-structure lint before approval.
- Final HTML must come from `prepare -> page subagents -> status -> assemble`.
- Pre-OCR body crop is mandatory when safe.
- Source pages are transcript units, not forced print-page boundaries.

Read these before work:

- `references/fidelity-rules.md`
- `references/working-contract.md`
- `references/review-gate.md`
- `references/math-rendering.md` — read when math looks too heavy/thick or a job needs the most elegant typography (MathJax default vs KaTeX switch)

## Required Workflow

1. Run `py -3 scripts/doc2x_parse_job.py --pdf "C:\path\scan.pdf" --out-dir "C:\path\job"`.
2. Inspect `doc2x/page-transcript.raw.md`, `source-transcript.md`, and `pages/` when review is needed.
3. Audit `source-transcript.md` against the raw transcript and source pages.
4. Run `py -3 scripts/lint_transcript_structure.py --job-dir "C:\path\job"`.
5. After the user approves the transcript and the lint result, set `job.json.transcript_audit_status` to `approved`.
6. Write `layout-brief.md`.
7. Build HTML only through the orchestrator path.
8. Run `py -3 scripts/validate_job_state.py "C:\path\job" --require-html`.
9. Export fresh screenshot and PDF (`py -3 scripts/render_html_to_pdf.py --html handout.html --pdf handout.pdf --screenshot handout-screenshot.png`), then start reviewer subagents.

If step 4 or step 5 never happened, step 8 must fail. Treat that failure as correct behavior.

## Markdown-Source Mode (clean canonical markdown input)

When the input is already a clean, well-structured markdown file — not a scanned PDF and not messy OCR output — skip Doc2X OCR and the audit/lint gates. This happens when a transcript was authored by hand or pre-cleaned upstream.

Use markdown-source mode when the input `.md`:
- has correct, intentional structure (headings, lists, tables, `$...$` math, `<figure>` blocks), and
- is **not** the raw Doc2X `page-transcript.raw.md` / `export.md` — those are OCR output and still belong to the audit path above.

Note: the builder treats bare adjacent `![](...)` images as OCR crops and clusters them into a ~92mm row. Wrap any intentional multi-image layout in a `<figure>` so it is preserved at its authored size.

Workflow:
1. Copy the input into the job dir as `source-transcript.md` (it IS the canonical transcript — no `doc2x/` artifacts exist).
2. Build HTML directly: `py -3 scripts/build_faithful_handout_html.py --md source-transcript.md --out-html handout.html --title "<title>"`.
3. Render: `py -3 scripts/render_html_to_pdf.py --html handout.html --pdf handout.pdf --screenshot handout-screenshot.png`.
4. Verify in a browser / PDF viewer: math rendered, 0 overflow (no sheet marked `data-fit-state="overflow"`), figures at intended size, title not duplicated.

Why `validate_job_state.py` does not apply here: it enforces the OCR-pipeline contract (`doc2x/`, `pages/`, audit/lint status). For markdown-source jobs there is no OCR, so those artifacts do not exist — running it produces false failures. Use the visual + builder-output checks above instead.

Everything else still holds: keep `source-transcript.md` canonical, never let an export markdown overwrite it, and start reviewer subagents only after real HTML + PDF + screenshot exist.

## Transcript Audit Rules

Read `references/transcript-audit-rules.md` before editing `source-transcript.md`.

During audit:

- Fix obvious OCR typos only when you can verify them from the source.
- If unsure, write `[TO VERIFY: ...]`.
- Preserve page markers, order, numbering, language, tables, formulas, and figure notes.
- Split merged multi-clause formulas into separate inline formulas.
- Normalize heading hierarchy. Promote title-like standalone lines to headings when the source clearly shows a heading.
- Keep the first real content heading on a page at `###`, not deeper.
- Do not jump heading levels by more than one step.
- If the first numbered heading on a page starts at `2` or `二`, treat it as a verification flag instead of silently trusting it.
- Prefer `\dfrac` for simple fractions; use `\tfrac` when numerator or denominator already contains a formula, operator, or nested fraction.
- Keep code as fenced code blocks.
- For choice examples, use one blockquote that contains the stem and the options.
- Put choice options in list form: `- A. ...`
- Normalize fill-in blanks to `__________`.
- Put solution text in its own paragraph starting with `解析：`.

## Builder Markdown Contract

The local builder now expects and enforces:

- centered fenced code blocks
- vendored `phycat`-style example blockquotes
- two-column even choice-option layout when options are list items inside the blockquote
- special styling for paragraphs beginning with `解析：`
- blank normalization to `__________`
- `\frac` promotion to `\dfrac` or `\tfrac`
- Doc2X crop clustering and size clamping
- centered table cells, but only display math may be block-centered in cells

## HTML Path

Read `references/page-fragment-worker.md` before dispatching workers.

Hard rules:

- Do not skip `status`.
- Do not approve placeholder HTML.
- Do not reintroduce raw full-width crop images or raw stacked split figures.
- Do not let `knowledge-to-print-html` replace the local Kami-based builder; it may only validate or review downstream.

## Files

- `scripts/doc2x_parse_job.py`
- `scripts/build_handout_via_subagents.py`
- `scripts/build_faithful_handout_html.py` — Kami-kernel A4 HTML builder (used in both OCR and markdown-source modes)
- `scripts/render_html_to_pdf.py` — Playwright HTML→A4 PDF + screenshot (engine-agnostic math wait)
- `scripts/lint_transcript_structure.py`
- `scripts/validate_job_state.py`
- `assets/kami-default-kernel.css`
- `assets/phycat-blockquote.css`
