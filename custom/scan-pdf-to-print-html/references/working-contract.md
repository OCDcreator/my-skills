# Working Contract

Each scan job should live in its own directory.

## Required Files

- `job.json`: machine-readable job metadata
- `source-transcript.md`: faithful page-by-page transcript
- `layout-brief.md`: layout and styling instructions only
- `handoff-notes.md`: unresolved ambiguities, asset notes, and figure handling notes

## Required Folders

- `doc2x/`: API artifacts, polling results, and export downloads

For `doc2x` jobs, local page images are optional.

- `pages/`: optional rendered source page images
- `pages-clean/`: optional cleaned versions used for reading assistance

## Optional Folders

- `diagrams/`: redrawn or cleaned figures
- `tables/`: extracted table images or intermediate assets

## Final Deliverables

- `handout.html`
- final printed PDF if requested

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
- It should be built from page-level parse output.
- It must not be overwritten by merged export markdown from `doc2x/export/`.

Use visible page markers:

```md
# Source Transcript

## Page 1

...

## Page 2

...
```

Put figure notes inline near the content they belong to.
