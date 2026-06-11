---
name: scan-pdf-to-print-html
description: Use when scanned or image-only PDFs need Doc2X OCR into a faithful, auditable page transcript and then A4 HTML/PDF. Best for textbooks, notes, worksheets, formulas, tables, diagrams, and question pages where content must stay source-faithful and `source-transcript.md` must be audited before HTML assembly.
---

# Scan Pdf To Print Html

Produce a Doc2X-backed OCR job with:

- `doc2x/page-transcript.raw.md`: untouched raw page transcript
- `source-transcript.md`: canonical transcript to audit and edit
- `handout.html` and PDF: final print outputs

Never rewrite, summarize, teach, merge away page provenance, or silently replace the canonical transcript with export markdown.

## Hard Contract

- `source-transcript.md` is the only transcript file allowed to feed HTML.
- `doc2x/export/export.md` is reference-only.
- `doc2x/export/export.md` should be localized to sibling `images/` assets whenever the Doc2X zip already contains matching local crops.
- `job.json.transcript_audit_status` starts at `pending`; HTML is blocked until it is `approved`.
- `job.json.transcript_structure_lint_status` starts at `pending`; run the transcript-structure lint before approval.
- Final HTML must come from `prepare -> page subagents -> status -> assemble`.
- The main thread must never one-shot the full transcript into final HTML.
- Pre-OCR body crop is mandatory when safe.
- Source pages are transcript units, not forced print-page boundaries.
- Reviewer subagents start only after real HTML, screenshot, and PDF exist.

Read these before work:

- `references/fidelity-rules.md`
- `references/working-contract.md`
- `references/review-gate.md`

## Required Workflow

1. Run `py -3 scripts/doc2x_parse_job.py --pdf "C:\path\scan.pdf" --out-dir "C:\path\job"`.
2. Inspect `doc2x/page-transcript.raw.md`, `source-transcript.md`, and `pages/` when review is needed.
3. Audit `source-transcript.md` against the raw transcript and source pages.
4. Run `py -3 scripts/lint_transcript_structure.py --job-dir "C:\path\job"`.
5. After the user approves the transcript and the lint result, set `job.json.transcript_audit_status` to `approved`.
6. Write `layout-brief.md`.
7. Build HTML only through the orchestrator path.
8. Run `py -3 scripts/validate_job_state.py "C:\path\job" --require-html`.
9. Export fresh screenshot and PDF, then start reviewer subagents.

If step 4 or step 5 never happened, step 8 must fail. Treat that failure as correct behavior.

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
- `scripts/build_faithful_handout_html.py`
- `scripts/lint_transcript_structure.py`
- `scripts/validate_job_state.py`
- `assets/kami-default-kernel.css`
- `assets/phycat-blockquote.css`
