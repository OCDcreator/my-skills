---
name: rewrite-doc2x-markdown
description: Use when Doc2X OCR markdown, Doc2X export.md, page-transcript.raw.md, or source-transcript.md is messy, too long, poorly structured, or must be rewritten into a high-quality canonical Markdown transcript before downstream use.
---

# Rewrite Doc2X Markdown

Create a clean, canonical Markdown document from Doc2X OCR output. This skill starts after Doc2X has returned Markdown and stops at Markdown: do not run OCR, render layouts, export final documents, take screenshots, or use any downstream skill.

## References

Read these before starting work:

- `references/auto-fix-rules.md` — mechanical text transformations to apply first
- `references/proofreading-checklist.md` — quality verification against source page images
- `references/canonical-markdown-rules.md` — structural formatting rules for the final Markdown

Also read the local Obsidian Markdown syntax skill for syntax compatibility reference:
`C:\Users\lt\Desktop\Write\custom-project\my-skills\external\kepano-obsidian-skills\obsidian-markdown\SKILL.md`.

## Hard Contract

- Produce or replace `source-transcript.md` as the only required deliverable.
- Treat `doc2x/export/export.md` as a rich reference, not as canonical output.
- Use `doc2x/page-transcript.raw.md` or source page markers to preserve order, but do not emit generic visible headings like `## Page N`.
- The top title must describe the actual document or knowledge area; never use `# Source Transcript`.
- Do not depend on downstream builders, exporters, print workflows, or other skills.
- Do not paste a very long OCR markdown file into one prompt and pretend it was fully read.
- For long markdown, use the Parallel Chunking Workflow below.
- Keep content source-faithful, but actively regenerate bad OCR Markdown structure.
- Do not continue beyond Markdown inside this skill.

## Inputs

Accept any of these inputs:

- `doc2x/page-transcript.raw.md`
- `doc2x/export/export.md`
- `doc2x/export/images/`
- existing `source-transcript.md`, if present
- rendered page images, if the user provides them
- a standalone Doc2X markdown file

If only one Doc2X markdown file is provided, still apply this skill and write a new canonical markdown file beside it unless the user gives a different destination.

## Workflow

### Step 0 — Assess & Plan

1. **Determine document size**: count `## Page N` markers, total lines, and total characters.
2. **Decide execution mode**:
   - Small (≤ 6 pages or ≤ 300 lines): single-thread, full-file processing.
   - Large (> 6 pages or > 300 lines): use the Parallel Chunking Workflow (see below), then continue with Steps 1-6 on the assembled result.
3. **Gather inputs**: confirm you have access to the raw transcript, page images for visual comparison, and any existing `source-transcript.md`.

### Step 1 — Auto-Fix (Mechanical Cleanup)

Apply `references/auto-fix-rules.md` in exact execution order. These are mechanical text transformations — execute them without hesitation.

Rules are applied in order: remove residual symbols → remove noise → normalize delimiters → split formulas → fix spacing → standardize fractions → normalize blanks → fix OCR characters.

### Step 2 — Proofread (Quality Verification)

Apply `references/proofreading-checklist.md`. Compare the auto-fixed transcript against source page images page by page.

Key checks in order:
1. Per-page image comparison (missing lines, missing characters, heading misidentification)
2. Chinese/English typos (confusable pairs)
3. Structure integrity (heading levels, blockquote splits, option grouping, image/table presence)
4. Cross-page integrity (cross-page callouts, tables, formulas, heading consistency)
5. `[TO VERIFY: ...]` marker management — resolve or leave with a count

This step produces an interim corrected transcript. Do NOT skip to formatting until proofreading is complete.

### Step 3 — Structural Format (Canonical Markdown)

Apply `references/canonical-markdown-rules.md` to the proofread transcript. This is the full set of formatting rules — all formatting requirements remain in effect.

### Step 4 — Auto-Validate & Fix

Run the validator in fix mode to handle any residual mechanical issues:

```
py -3 .codex\skills\rewrite-doc2x-markdown\scripts\validate_canonical_markdown.py --md "C:\path\source-transcript.md" --fix
```

or:

```
py -3 .codex\skills\rewrite-doc2x-markdown\scripts\validate_canonical_markdown.py --job-dir "C:\path\job" --fix
```

This auto-corrects: math spacing, delimiter normalization, fraction standardization, blank line splits, header noise, and leading orphan punctuation.

### Step 5 — Quality Validation

Run the validator in proofreading mode:

```
py -3 .codex\skills\rewrite-doc2x-markdown\scripts\validate_canonical_markdown.py --md "C:\path\source-transcript.md" --check-proofreading
```

Fix all reported issues (unclosed formulas, heading jumps, missing options, suspicious characters). Re-run until clean.

### Step 6 — Report

Report only Markdown status:

- path to `source-transcript.md`
- whether `validate_canonical_markdown.py` (with `--fix`) passed
- whether `validate_canonical_markdown.py` (with `--check-proofreading`) passed
- number of `[TO VERIFY: ...]` markers remaining
- a brief per-page summary of corrections made during auto-fix and proofreading
- chunks or pages that need human review

Do not claim that downstream output is ready. High-quality Markdown is the handoff.

---

## Parallel Chunking Workflow

Use this when the document exceeds a single-context threshold (> 6 pages, > 300 lines, or > 10,000 characters).

### Chunk Planning

1. Scan the raw transcript and find all `## Page N` markers.
2. Group pages into chunks of 3-5 pages each. Chunk boundaries must fall on `## Page N` markers.
   - If a question callout or table spans a page boundary, assign it to the chunk containing the starting page.
3. Create `markdown-rewrite-plan.md` with checked chunks:

```markdown
# Markdown Rewrite Plan
- [ ] Chunk 1: Page 274-277 (线面平行 → 线面垂直判定)
- [ ] Chunk 2: Page 278-281 (面面平行 → 例题6)
- [ ] Chunk 3: Page 282-284 (综合练习)
```

### Parallel Dispatch

| Total pages | Chunks | Parallel batch size | Batches |
|-------------|--------|---------------------|---------|
| 7-10        | 2-3    | 3                   | 1       |
| 11-20       | 4-6    | 4                   | 1       |
| 21-35       | 7-10   | 5                   | 2       |
| 36-50       | 11-15  | 5                   | 2-3     |
| >50         | 16+    | 5                   | 3+      |

For each chunk, dispatch a subagent with:
- The chunk's raw transcript (page range)
- The chunk's page images
- Instructions: execute Steps 1-3 (auto-fix → proofread → format) on this chunk only
- The current `canonical-markdown-rules.md` as reference
- Output: cleaned Markdown for the chunk + `[TO VERIFY]` markers encountered

After each batch completes, check for failed chunks (subagent error or timeout > 5 min). Mark failed chunks in `markdown-rewrite-plan.md` and re-dispatch them in the next batch.

### Assembly

1. Concatenate chunks in page order.
2. Check chunk boundaries for:
   - Truncated formulas or tables at page breaks.
   - Heading level consistency across chunks (adjacent chunks must not jump levels).
   - Duplicate or missing `## Page N` markers.
3. Merge all `[TO VERIFY: ...]` markers from subagent reports into a single list.
4. Run Steps 4-5 (validate --fix → validate --check-proofreading) on the assembled document.
5. Run a final read-through pass to verify callouts, analysis blocks, tables, formulas, and image references did not break during concatenation.

---

## Required Markdown Structures

Follow `references/canonical-markdown-rules.md` for the complete formatting specification. Do not deviate from or skip any formatting rules in that reference.

## Output Boundary

At completion, report only Markdown status:

- path to `source-transcript.md`
- whether `validate_canonical_markdown.py` (with `--fix`) passed or failed
- whether `validate_canonical_markdown.py` (with `--check-proofreading`) passed or failed
- number of unresolved `[TO VERIFY: ...]` markers and their page locations
- chunks or pages that need human review

Do not claim that downstream output is ready. High-quality Markdown is the handoff.
