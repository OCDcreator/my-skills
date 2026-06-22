# Review Gate

Use this default review order for every faithful print handout:

1. confirm `source-transcript.md` is canonical Markdown; if it came from PDF/OCR/Doc2X output, confirm `rewrite-doc2x-markdown` already completed and do not print directly from raw `export.md` or `page-transcript.raw.md`
2. run generator unit tests
3. run `validate_math_quote_leakage.py --md source-transcript.md`
4. build a real `handout.html` locally through the Kami builder or the orchestrator path
5. when using the orchestrator path, prepare local page packets and `html-build-manifest.json`
6. when using the orchestrator path, have Codex runtime page-level subagents write real files under `handout-parts/`
7. when using the orchestrator path, run local `status` to refresh manifest state from real worker outputs
8. when using the orchestrator path, assemble a real `handout.html` locally
9. run the validation command that matches the job type:
for markdown-source jobs, use `validate_rendered_handout_contract.py --html handout.html` plus `validate_sheet_bottom_margin.py --html handout.html` (add `--require-katex --disallow-mathjax` to the rendered-contract validator after final KaTeX post-processing for math-heavy jobs); when a job explicitly requires each lecture to start on a fresh sheet, the preceding sheet must carry `data-ends-before-lecture="true"` for the trailing-blank exemption to count; for legacy OCR/orchestrator jobs, also run `validate_job_state.py --require-html`
10. confirm the validator saw the real HTML path and the real orchestrator artifacts that apply to the job:
for legacy jobs, `handout.html`; for subagent-orchestrated jobs, `handout.html` plus a complete `html-build-manifest.json` and `handout-parts/`
11. export fresh screenshot and PDF
12. check known failure classes: formulas visible, tables centered, image cells frameless, split figures clustered side-by-side when appropriate, small crop images not oversized, output page breaks chosen by layout rather than blindly mirroring source pages, no sheet left in adaptive-fit overflow state, and no obvious overflow or clipping. For marked full-page covers or special sheets (`.concept-map-sheet`, `[data-sheet-role="cover"]`, `[data-cover-sheet="true"]`), verify the screen-preview A4 frame aligns with the first regular `.sheet` on `left` and `width`; this catches a cover using `margin: 0` while regular sheets use centered preview margins, but should not be applied to unmarked ordinary pages or print-mode zero margins. For question/example blockquotes, also verify the rendered DOM: `lead-tag-example` badges are visible for `例/例题/练习` labels, the `.phycat-blockquote` left accent rule is visible as a computed accent rule rather than a generic 1px/plain/same-color box border, option tables inside blockquotes are transparent/borderless with matching `th`/`td` styles, and option images are large enough to read. Non-blockquote knowledge/data tables may use ruled styling when source fidelity requires it; do not judge them by the blockquote option-table rule. <!-- strengthened 2026-06-22 -->
13. if `knowledge-to-print-html` review tooling is available, run its page-review packet generation
14. review page 1 with a fresh reviewer subagent
15. fix page 1 and revalidate before page 2
16. continue sequentially until all pages pass

Reject the job immediately if any of these shortcuts occurred:

- a new PDF/OCR/Doc2X task used this skill to create canonical Markdown instead of starting with `rewrite-doc2x-markdown`
- raw Doc2X `export.md` or `page-transcript.raw.md` fed HTML directly
- for legacy OCR jobs, `validate_job_state.py --require-html` passed before `job.json.transcript_audit_status` became `approved`
- for legacy OCR jobs, `validate_job_state.py --require-html` passed before `job.json.transcript_structure_lint_status` became `passed` or `passed-with-warnings`
- the main thread directly generated the final `handout.html` from the full transcript or full OCR markdown
- `status` was skipped between fragment generation and `assemble`
- repeated header/footer cleanup for a legacy OCR job depended primarily on post-OCR text matching instead of a feasible pre-OCR body crop

Reviewer subagents must not approve placeholder output. They only enter after the real local `handout.html`, real screenshot, and real PDF exist for the current job.
