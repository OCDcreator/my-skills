# Review Gate

Use this default review order for every faithful OCR handout:

1. confirm pre-OCR body cropping was applied when safely possible, or confirm `handoff-notes.md` records why it was not
2. run generator unit tests
3. audit `source-transcript.md` against `doc2x/page-transcript.raw.md` and the rendered pages
4. run `lint_transcript_structure.py --job-dir ...` and inspect its heading-level findings and warnings
5. after the user approves the transcript, set `job.json.transcript_audit_status=approved`
6. prepare the local page packets and `html-build-manifest.json`
7. have Codex runtime page-level subagents write real files under `handout-parts/`
8. run local `status` to refresh manifest state from real worker outputs
9. assemble a real `handout.html` locally
10. run `validate_job_state.py --require-html`
11. confirm the validator saw the real HTML path, the transcript approval, the structure-lint status, and the real orchestrator artifacts that apply to the job:
for legacy jobs, `handout.html`; for subagent-orchestrated jobs, `handout.html` plus a complete `html-build-manifest.json` and `handout-parts/`
12. export fresh screenshot and PDF
13. check known failure classes: formulas visible, tables centered, image cells frameless, split figures clustered side-by-side when appropriate, small crop images not oversized, output page breaks chosen by layout rather than blindly mirroring source pages, no sheet left in adaptive-fit overflow state, and no obvious overflow or clipping
14. if `knowledge-to-print-html` review tooling is available, run its page-review packet generation
15. review page 1 with a fresh reviewer subagent
16. fix page 1 and revalidate before page 2
17. continue sequentially until all pages pass

Reject the job immediately if any of these shortcuts occurred:

- `validate_job_state.py --require-html` passed before `job.json.transcript_audit_status` became `approved`
- `validate_job_state.py --require-html` passed before `job.json.transcript_structure_lint_status` became `passed` or `passed-with-warnings`
- the main thread directly generated the final `handout.html` from the full transcript or full OCR markdown
- `status` was skipped between fragment generation and `assemble`
- repeated header/footer cleanup depended primarily on post-OCR text matching instead of a feasible pre-OCR body crop

Reviewer subagents must not approve placeholder output. They only enter after the real local `handout.html`, real screenshot, and real PDF exist for the current job.
