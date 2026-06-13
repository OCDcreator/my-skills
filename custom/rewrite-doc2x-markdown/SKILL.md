---
name: rewrite-doc2x-markdown
description: Use when Doc2X OCR markdown, Doc2X export.md, page-transcript.raw.md, or source-transcript.md is messy, too long, poorly structured, or must be rewritten into a high-quality canonical Markdown transcript before downstream use. Also use when the user provides a PDF file alongside or instead of Markdown — this skill can extract specified PDF pages as proofreading images to verify transcription quality.
---

# Rewrite Doc2X Markdown

Create a clean, canonical Markdown document from Doc2X OCR output. This skill starts after Doc2X has returned Markdown and stops at Markdown: do not run OCR, render layouts, export final documents, or use any downstream skill. The only exception: you **may** render PDF pages as proofreading images when the user provides a PDF file — this is a quality aid, not a downstream output.

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
- **PDF extraction allowed only as a proofreading aid**: you may render PDF pages to images for visual comparison, but never treat the rendered images or the PDF itself as a source for text extraction — use the Doc2X OCR markdown for that.
- **Doc2X is the primary source**: always use `doc2x/page-transcript.raw.md` as your base text. Do NOT use third-party image OCR tools (MCP screenshots, etc.) as a substitute — they produce worse results and miss content. The Doc2X export is the authoritative transcription.
- **Preserve ALL detail**: never summarize, condense, or remove derivation steps from analysis sections. Every step of every method (法一, 法二, 法三) must be preserved in full. Missing detail is a critical failure.

## Inputs

Accept any of these inputs:

- `doc2x/page-transcript.raw.md`
- `doc2x/export/export.md`
- `doc2x/export/images/`
- existing `source-transcript.md`, if present
- rendered page images, if the user provides them
- a standalone Doc2X markdown file
- **a PDF file path** (with optional page range) — used to render proofreading images via `scripts/extract_pdf_pages.py`

If only one Doc2X markdown file is provided, still apply this skill and write a new canonical markdown file beside it unless the user gives a different destination.

## Workflow

### Step 0 — Assess & Plan

1. **Determine document size**: count `## Page N` markers, total lines, and total characters.
2. **Decide execution mode**:
   - Small (≤ 6 pages or ≤ 300 lines): single-thread, full-file processing.
   - Large (> 6 pages or > 300 lines): use the Parallel Chunking Workflow (see below), then continue with Steps 1-6 on the assembled result.
3. **Gather inputs**: confirm you have access to the raw transcript, page images for visual comparison, and any existing `source-transcript.md`.

### Step 0-A — Extract PDF Pages (optional)

If the user provides a **PDF file path** (instead of or alongside Markdown), extract specific pages as proofreading images:

```bash
py -3 scripts/extract_pdf_pages.py ^
  --pdf "C:\path\document.pdf" ^
  --out-dir "C:\path\job\pdf-pages" ^
  --pages "1-3,7" ^
  --dpi 200 ^
  --format png
```

- If no `--pages` is given, all pages are rendered.
- The script outputs `pdf-pages/page-001.png`, `pdf-pages/page-002.png`, etc., plus a `pdf-pages/manifest.json`.
- Use these images in Step 2 (Proofread) for visual comparison against the Markdown transcript.
- This step is **optional**: if the user only provides Markdown (no PDF), skip it entirely.

> **When to extract which pages:**
> - If the user says "proofread pages 3-7 of this PDF", use `--pages "3-7"`.
> - If the user provides a PDF without specifying pages, render all pages.
> - If the user provides both a PDF and a Doc2X markdown file, render only the pages that correspond to the markdown content (match `## Page N` markers to page numbers).

### Step 1 — Auto-Fix (Mechanical Cleanup)

Apply `references/auto-fix-rules.md` in exact execution order. These are mechanical text transformations — execute them without hesitation.

Rules are applied in order: remove residual symbols → remove noise → normalize delimiters → split formulas → fix spacing → standardize fractions → normalize blanks → fix OCR characters.

**Critical notes on auto-fix:**

- **Noise removal**: remove ALL Doc2X-internal artifacts including `<!-- doc2x score: N -->`, `<!-- Meanless: ... -->`, `<!-- Media -->`, `<!-- figureText: ... -->`, page number lines like `N 老唐说题`, and chapter header lines like `第 N 章 导 数`. Do NOT leave `__________` fill-in-blank artifacts from auto-fix noise either — verify the separator between sections is `---` not `__________`.
- **Fraction standardization**: `\frac` → `\dfrac` for display-level formulas; use `\tfrac` only when numerator/denominator contains operators or nested fractions. Inline math (`$...$`) should prefer `\tfrac` to avoid line-height disruption.
- **Callout syntax check**: after auto-fix, verify every `[!question]` or `[!example]` or `[!note]` has a `> ` prefix. The pattern `> [!question]` is required; bare `[!question]` without `>` is a syntax error.

### Step 2 — Proofread (Quality Verification)

Apply `references/proofreading-checklist.md`. Compare the auto-fixed transcript against source page images page by page.

If PDF pages were extracted in Step 0-A, use those images (`pdf-pages/page-*.png`). Otherwise, use whatever page images the user provided (e.g., `doc2x/export/images/`).

**IMPORTANT — paragraph splitting rule:**
Analysis paragraphs must be split at logical break points. A paragraph inside an analysis section should not exceed approximately 300 characters. Split at:
- Punctuation breaks（句号、分号、冒号）
- New formula expressions (`$...$` or `$$...$$` blocks)
- Logic transitions（"故"、"所以"、"因此"、"又因为"、"此时"）
- Method boundaries（方案一/方案二/方案三、法一/法二/法三）

Each logical step gets its own paragraph. A single long paragraph containing multiple reasoning steps is a formatting failure.

Key checks in order:
1. Per-page image comparison (missing lines, missing characters, heading misidentification)
2. Chinese/English typos (confusable pairs) — check "易知" not "易如", "必须有" not "必需有", "根据" not "根", "初高分流" vs actual text
3. Structure integrity (heading levels, blockquote splits, option grouping, image/table presence)
4. Cross-page integrity (cross-page callouts, tables, formulas, heading consistency)
5. `[TO VERIFY: ...]` marker management — resolve or leave with a count
6. **Paragraph length check**: verify no analysis paragraph exceeds 300 characters

### Step 3 — Structural Format (Canonical Markdown)

Apply `references/canonical-markdown-rules.md` to the proofread transcript.

**Parser choice rule:**
For formula-heavy math content (calculus, algebra with many inline formulas), use **plain Markdown** for analysis sections (`**解析**` / `**解**` with regular paragraph breaks), NOT `<div class="analysis-block">` HTML blocks. The HTML analysis-block format requires MathML for all formulas inside it, which is impractical for complex math content. Use the exemption clause: *"If an HTML formula is too complex to express safely as MathML and SVG generation is not available, move that content out of HTML and rewrite it as normal Markdown."*

Only use `<div class="analysis-block">` when the analysis section contains ZERO formulas (pure text).

**Long formula formatting:**
For display formulas longer than one line, use `\begin{aligned}` with `\\` line breaks. Split at `=` signs, `+`/`-` operators, or logical boundaries. Every long formula must be readable without horizontal scrolling.

### Step 4 — Auto-Validate & Fix

Run the validator in fix mode to handle any residual mechanical issues:

```
py -3 scripts/validate_canonical_markdown.py --md "C:\path\source-transcript.md" --fix
```

or:

```
py -3 scripts/validate_canonical_markdown.py --job-dir "C:\path\job" --fix
```

This auto-corrects: math spacing, delimiter normalization, fraction standardization, blank line splits, header noise, and leading orphan punctuation.

**Known validator limitations:**
The `--fix` mode may incorrectly transform `---` (horizontal rule) into `__________` (fill-in-blank) due to Rule 5 (Fill-in-Blank Normalization). After running `--fix`, visually check that section separators remain as `---` and haven't been corrupted.

### Step 5 — Quality Validation

Run the validator in proofreading mode:

```
py -3 scripts/validate_canonical_markdown.py --md "C:\path\source-transcript.md" --check-proofreading
```

**Known false positives** (do NOT waste time on these):
- "possible unclosed inline math `$` delimiter" — triggered by `$$...$$` blocks that contain `$` inside them; these are NOT actual errors in formula-heavy content.
- "suspicious character [已] near [己/巳]" and "[入] near [人]" — these are legitimate Chinese characters that appear correctly in context. Verify once, then dismiss.
- "possible unclosed display math `$$` delimiter" — same as above, false alarm.

If ALL failures are only these known false positives, report them as "confirmed false positives" and pass the step.

Fix all other reported issues (unclosed formulas, heading jumps, missing options, suspicious characters). Re-run until only false positives remain.

### Step 6 — Self-Check (LESSONS LEARNED CHECKLIST)

Before reporting, run through this checklist to catch the most common failures:

- [ ] **Callout syntax**: every `[!question]`, `[!example]`, `[!note]`, `[!warning]` is preceded by `> ` (e.g., `> [!question]`, never bare `[!question]`).
- [ ] **Paragraph splitting**: no analysis paragraph exceeds 300 characters. Each logical step is its own paragraph.
- [ ] **Content preservation**: ALL derivation steps preserved. No summarizing or condensing of 法一/法二/法三 sections.
- [ ] **Doc2X primacy**: content matches Doc2X raw output in scope. No detail removed compared to `doc2x/page-transcript.raw.md`.
- [ ] **Noise removal**: no `<!-- doc2x score -->`, `<!-- Meanless -->`, `__________` artifacts, stray "老唐说题" page numbers, or chapter header lines remain.
- [ ] **Fraction rules**: display formulas use `\dfrac`, inline math uses `\tfrac` where denominator has operators. No bare `\frac`.
- [ ] **Long formulas**: display formulas longer than ~60 characters use `\begin{aligned}` with line breaks.
- [ ] **Horizontal rules**: check `---` separators weren't auto-fixed to `__________`.
- [ ] **`--fix` pass**: `validate_canonical_markdown.py --fix` returns PASS.
- [ ] **Proofreading**: only known false positives remain, or actual issues are fixed.

### Step 6 — Report

Report only Markdown status:

- path to `source-transcript.md`
- whether `validate_canonical_markdown.py` (with `--fix`) passed
- whether `validate_canonical_markdown.py` (with `--check-proofreading`) passed
- number of `[TO VERIFY: ...]` markers remaining
- a brief per-page summary of corrections made during auto-fix and proofreading
- chunks or pages that need human review
- **Self-check results**: which items from the self-check list passed/failed

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
- [ ] Chunk 1: Page 274-277 (section description)
- [ ] Chunk 2: Page 278-281 (section description)
- [ ] Chunk 3: Page 282-284 (section description)
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
