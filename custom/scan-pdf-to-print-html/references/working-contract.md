# Working Contract

Each scan job should live in its own directory.

The default HTML workflow is:

1. isolate body content before OCR when recurring non-body regions are present
2. prepare deterministic local job inputs
3. create `doc2x/page-transcript.raw.md` and an auditable `source-transcript.md`
4. lint transcript structure and record `job.json.transcript_structure_lint_status`
5. audit `source-transcript.md` and mark `job.json.transcript_audit_status=approved`
6. dispatch page-level subagents through Codex runtime
7. refresh manifest status locally
8. assemble the final HTML locally
9. validate the assembled output before review

Local Python scripts own only the pre-OCR normalization, prepare, status, and assemble steps. They do not directly invoke Codex subagent tools.

The main thread must not bypass this workflow by pasting the full transcript or full OCR markdown into one prompt and directly authoring the final `handout.html`.

## Required Files

- `job.json`: machine-readable job metadata
- `source-transcript.md`: faithful page-by-page transcript
- `doc2x/page-transcript.raw.md`: untouched raw Doc2X page transcript
- `layout-brief.md`: layout and styling instructions only
- `handoff-notes.md`: unresolved ambiguities, asset notes, figure handling notes, and pre-OCR body-crop decisions or exceptions

When `job.json` sets `"html_builder": "subagent-orchestrated"`, the job also requires:

- `html-build-manifest.json`: page-level HTML build plan and status ledger

For jobs that contain recurring headers/footers or Doc2X figure crops, the canonical contract also requires:

- if a safe body crop is possible, apply or record that crop before OCR instead of depending on post-OCR text matching as the primary cleanup method
- split crops that belong to one logical side-by-side source figure to stay adjacent in transcript/fragment order until local HTML assembly
- successful page meta files to repeat the same `source_fingerprint` as the manifest page entry before reuse is allowed

## Required Folders

- `doc2x/`: API artifacts, polling results, and export downloads

For `doc2x` jobs, local page images are optional.

- `pages/`: optional rendered source page images
- `pages-clean/`: optional cleaned versions used for reading assistance
- `handout-parts/`: required when `html_builder` is `subagent-orchestrated`; contains one fragment and one meta file per page, plus optional page error files

## Optional Folders

- `diagrams/`: redrawn or cleaned figures
- `tables/`: extracted table images or intermediate assets

## Final Deliverables

- `handout.html`
- final printed PDF if requested

For subagent-orchestrated HTML jobs, `handout.html` is not considered real output until:

- the file was produced by the local `prepare` -> subagent fragment writes -> local `status` -> local `assemble` path
- `job.json.transcript_audit_status` is `approved`
- `job.json.transcript_structure_lint_status` is `passed` or `passed-with-warnings`
- `html-build-manifest.json` exists and every page is marked `success`
- the referenced fragment and meta files exist under `handout-parts/`
- each successful page meta file carries a `source_fingerprint` that matches the manifest page entry
- each successful page fragment contains rendered HTML, not raw Markdown, and image-only split crops have been normalized into clustered layout instead of raw stacked output
- the final layout preserves transcript order and source provenance without requiring `1 source page = 1 output page`
- tiny image crops are not promoted to dominant full-width figures without an explicit source-based reason
- the local assembler has written the final `handout.html`

## Doc2X Artifacts

Typical `doc2x/` files:

- `preupload.json`
- `parse-status.json`
- `parse-result.json`
- `export-request.json`
- `export-result.json`
- `export/`
- `export/export.md` when Doc2X produced a markdown export worth keeping for reference

## Transcript Shape

`source-transcript.md` is the canonical page-level handoff file.

- It must preserve visible page markers.
- It should be built from page-level parse output and audited against `doc2x/page-transcript.raw.md`.
- It must not be overwritten by merged export markdown from `doc2x/export/`.
- It must not be treated as a direct one-shot prompt to generate the final HTML in the main thread.
- `job.json.transcript_audit_status` must be `approved` before HTML validation may pass.
- `job.json.transcript_structure_lint_status` must be `passed` or `passed-with-warnings` before HTML validation may pass.

Use visible page markers:

```md
# Source Transcript

## Page 1

...

## Page 2

...
```

Put figure notes inline near the content they belong to.

## Fragment Workflow Notes

- `html-build-manifest.json` is the canonical build ledger for page-fragment HTML jobs.
- `prepare`, runtime fragment writes, `status`, and `assemble` are mandatory checkpoints, not optional conveniences.
- each successful manifest page entry should carry `source_fingerprint`, and the matching page meta file must repeat the same value before resume-safe validation can pass.
- the manifest tracks source-page work units, but final print-page boundaries remain layout-owned and may merge or split source-page content.
- tiny Doc2X crop images are expected to be size-clamped by the local builder, and adjacent crop-only figure rows are expected to become clustered layout in the final HTML.
- `references/page-fragment-worker.md` defines the exact worker read/write boundary for each page fragment.
- Reviewer subagents only start after the assembled `handout.html`, screenshot, and PDF are all real files for the current job.
