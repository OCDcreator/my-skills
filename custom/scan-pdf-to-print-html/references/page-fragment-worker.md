# Page Fragment Worker Contract

Use this contract for page-level subagents that generate HTML fragments for the default scan-to-print workflow.

## Purpose

Each worker owns exactly one source page and writes exactly one page fragment that will later be merged into the shared Kami print document.

The overall workflow is:

1. local Python prepares page packets and `html-build-manifest.json`
2. Codex runtime dispatches page-level subagents
3. each worker writes its fragment files under `handout-parts/`
4. local Python refreshes manifest status
5. local Python validates and assembles the final `handout.html`

Python scripts prepare and assemble locally. Codex runtime performs the true subagent dispatch.

Worker scope rule:

- A worker owns one source-page packet, not one final print page.
- The final layout engine may merge or split source-page content across output pages.
- Do not encode `1 source page = 1 output page` assumptions into fragment markup.

## Worker Reads

The worker may read only the inputs prepared for its assigned page:

- the assigned page section from `source-transcript.md`
- `layout-brief.md`
- `handoff-notes.md` when it contains page-relevant fidelity notes
- page-local source assets already created for that page, such as images under `diagrams/`, `tables/`, `pages/`, or `pages-clean/`
- the job's `html-build-manifest.json` entry for that page

If more context seems necessary, the worker should report the gap instead of reading unrelated pages.

## Worker Writes

The worker may write only these files for its assigned page inside `handout-parts/`:

- `page-XXXX.fragment.html`
- `page-XXXX.meta.json`
- optional `page-XXXX.error.txt`

The worker must not edit:

- `job.json`
- `source-transcript.md`
- `layout-brief.md`
- `handoff-notes.md`
- `html-build-manifest.json`
- `handout.html`
- any other page's fragment, meta, or error files

## Fragment Markup Rules

`page-XXXX.fragment.html` must contain only the page body content that belongs inside the shared Kami shell.

Allowed markup:

- headings
- paragraphs
- lists
- tables
- figures
- inline math
- display math
- small semantic wrappers needed for page-local structure

Forbidden markup:

- `<!doctype ...>`
- `<html>`
- `<head>`
- `<body>`
- shared `<script>` tags
- global `<style>` blocks
- page shell chrome, including shared headers, footers, page numbers, or print controls
- forced print-page wrappers or source-page-sized shells that assume the fragment must equal one final output page
- cross-page navigation, review UI, or orchestration status banners
- markdown fences or raw markdown that was not converted to HTML

Hard media-layout rules:

- If one logical source figure was split into multiple image crops, keep those crop tags adjacent in the fragment.
- Do not insert explanatory text, headings, or spacer markup between members of the same split figure group.
- Do not rely on raw `<br>` stacking as the final intended layout for split side-by-side figures; the builder must restore adjacent crop-only images into clustered rows or grids deterministically.
- Do not enlarge tiny crop images with inline width/height styles, full-width wrappers, or other markup that implies they should dominate the page.

## Meta File Rules

`page-XXXX.meta.json` should be a JSON object describing the page result, with:

- `page_number`
- `status`
- `source_fingerprint`
- optional `warnings`
- optional short notes about unresolved fidelity issues for this page

`source_fingerprint` must exactly match the assigned page entry in `html-build-manifest.json`. This is required for stale-safe resume behavior: a previous successful fragment/meta pair must not be reused after the source transcript content for that page changes.

Use `status: "success"` only when the fragment is ready for local assembly. If the page cannot be completed faithfully, write `page-XXXX.error.txt` with the blocking issue and mark the meta status accordingly.

Do not mark `status: "success"` if:

- the fragment still contains raw Markdown instead of rendered HTML
- the fragment contains empty media placeholders instead of real figure markup
- split figure crops were rearranged or separated from each other
- the fragment hardcodes output-page layout assumptions that belong to the shared assembler

## Fidelity Rules

- Preserve transcript order exactly for the assigned page.
- Do not rewrite, summarize, explain, or teach the content.
- Keep formulas, tables, labels, and figure references faithful to the source transcript.
- Preserve adjacency of figure members that belong to one logical clustered source figure so the builder can restore that group later.
- If something is unreadable or ambiguous, surface it as a warning or error instead of guessing.

## Review Boundary

Worker output is not reviewer-approved output by itself.

Reviewer subagents only start after:

- real fragment files exist
- local assembly has produced the real `handout.html`
- real screenshot and PDF exports exist for the current job
