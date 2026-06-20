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
for markdown-source jobs, use rendered-output checks plus `validate_sheet_bottom_margin.py --html handout.html`; for legacy OCR/orchestrator jobs, also run `validate_job_state.py --require-html`
10. confirm the validator saw the real HTML path and the real orchestrator artifacts that apply to the job:
for legacy jobs, `handout.html`; for subagent-orchestrated jobs, `handout.html` plus a complete `html-build-manifest.json` and `handout-parts/`
11. export fresh screenshot and PDF
12. check known failure classes: formulas visible, tables centered, image cells frameless, split figures clustered side-by-side when appropriate, small crop images not oversized, output page breaks chosen by layout rather than blindly mirroring source pages, no sheet left in adaptive-fit overflow state, and no obvious overflow or clipping
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
