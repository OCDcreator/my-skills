# Working Contract

Each scan job should live in its own directory.

The default workflow starts after `rewrite-doc2x-markdown` or another upstream source has produced a canonical `source-transcript.md`. For new PDF-only, scanned-PDF, image-only PDF, or messy Doc2X Markdown work, first use `rewrite-doc2x-markdown` to create and validate that transcript, then return here for print output.

The default HTML workflow is:

1. create an isolated job directory under `product/`
2. copy the approved canonical Markdown into `source-transcript.md`
3. write `layout-brief.md` for layout and styling instructions only
4. build `handout.html` through the local Kami builder or orchestrator path
5. export a fresh screenshot and vector PDF
6. validate the assembled output before review
7. run reviewer subagents only after real HTML, screenshot, and PDF exist

Local Python scripts own prepare, render, status, assemble, and validation steps. They do not directly invoke Codex subagent tools.

The main thread must not bypass this workflow by pasting the full transcript or full OCR markdown into one prompt and directly authoring the final `handout.html`.

## Upstream Markdown Boundary

- `rewrite-doc2x-markdown` owns Doc2X/OCR cleanup, long-document chunking, transcript proofreading, and canonical Markdown production.
- `scan-pdf-to-print-html` owns only the downstream print build from a canonical `source-transcript.md`.
- Raw Doc2X `export.md` and `page-transcript.raw.md` are not accepted as direct print inputs. Send them through `rewrite-doc2x-markdown` first.
- Legacy Doc2X job scripts remain available for old job directories, but new work should not start by running `scripts/doc2x_parse_job.py` from this skill.

## Required Files

- `job.json`: machine-readable job metadata
- `source-transcript.md`: faithful page-by-page transcript
- `layout-brief.md`: layout and styling instructions only
- `handoff-notes.md`: unresolved ambiguities, asset notes, figure handling notes, and upstream transcript notes or exceptions

When `job.json` sets `"html_builder": "subagent-orchestrated"`, the job also requires:

- `html-build-manifest.json`: page-level HTML build plan and status ledger

For legacy OCR jobs that contain recurring headers/footers or Doc2X figure crops, the compatibility contract also requires:

- if a safe body crop was part of the legacy OCR workflow, apply or record that crop before OCR instead of depending on post-OCR text matching as the primary cleanup method
- split crops that belong to one logical side-by-side source figure to stay adjacent in transcript/fragment order until local HTML assembly
- successful page meta files to repeat the same `source_fingerprint` as the manifest page entry before reuse is allowed

## Required Folders

- `doc2x/`: legacy API artifacts, polling results, and export downloads
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

`source-transcript.md` is the canonical page-level handoff file. In new jobs it should already be produced and validated by `rewrite-doc2x-markdown` before this skill starts.

- It must preserve visible page markers.
- If it came from OCR, it should be built and audited upstream by `rewrite-doc2x-markdown`.
- It must not be overwritten by merged export markdown from `doc2x/export/`.
- It must not be treated as a direct one-shot prompt to generate the final HTML in the main thread.
- Legacy OCR jobs still require `job.json.transcript_audit_status=approved` and `job.json.transcript_structure_lint_status=passed` or `passed-with-warnings` before HTML validation may pass.

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
- tiny Doc2X crop images, when present in a canonical transcript from upstream OCR cleanup, are expected to be size-clamped by the local builder, and adjacent crop-only figure rows are expected to become clustered layout in the final HTML.
- `references/page-fragment-worker.md` defines the exact worker read/write boundary for each page fragment.
- Reviewer subagents only start after the assembled `handout.html`, screenshot, and PDF are all real files for the current job.
