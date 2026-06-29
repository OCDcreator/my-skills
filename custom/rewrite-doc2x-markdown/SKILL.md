---
name: rewrite-doc2x-markdown
description: Use when Doc2X OCR markdown, Doc2X export.md, page-transcript.raw.md, or source-transcript.md is messy, too long, poorly structured, or must be rewritten into a high-quality canonical Markdown transcript before downstream use. Also use when the user provides a PDF file alongside or instead of Markdown — this skill can extract specified PDF pages as proofreading images to verify transcription quality.
---

# Rewrite Doc2X Markdown

Create a clean, canonical Markdown document from Doc2X OCR output. This skill starts after Doc2X has returned Markdown and stops at Markdown: do not run OCR, render layouts, export final documents, or use any downstream skill. The only exception: you **may** render PDF pages as proofreading images when the user provides a PDF file — this is a quality aid, not a downstream output.

This SKILL.md is the **orchestrator**. Detailed rules live in `references/` (Layer 3) and are read on demand — each step below names the reference file to read before acting.

## References (read on demand, per step)

- `references/auto-fix-rules.md` — Step 1 mechanical text transformations
- `references/auto-fix-gate.md` — Step 1-GATE 7 mandatory verification checks (commands)
- `references/proofreading-checklist.md` — Step 2 quality verification against source page images
- `references/analysis-retypesetting.md` — Step 2.5 analysis re-typesetting rules + subagent template
- `references/question-block-rewrite-guide.md` — Step 2.7 question-block rewrite rules + subagent template
- `references/canonical-markdown-rules.md` — Step 3 structural formatting spec for the final Markdown
- `references/emphasis-and-color-rules.md` — bold/italic and semantic-color marking (used in Steps 2.7 & 3)
- `references/forbidden-patterns.md` — F1–F5 failure patterns (LESSONS LEARNED), always in force
- `references/self-check.md` — Step 6 self-check checklist (evidence + judgment items)
- `references/parallel-chunking.md` — Parallel Chunking Workflow for large documents (> 6 pages / > 300 lines)
- `references/opencode-agent-invocation.md` — **optional** high-performance dispatch path: three pre-registered OpenCode agents (`md-cleaner` / `question-block-rewriter` / `analysis-retypesetter`) that run Steps 1 / 2.7 / 2.5 with model + permissions + distilled prompt pre-configured. Use when the host detects `opencode` + the project's `.opencode/agents/`; fall back to host-native subagent otherwise.

Also read the local Obsidian Markdown syntax skill for syntax compatibility reference:
`C:\Users\lt\Desktop\Write\custom-project\my-skills\external\kepano-obsidian-skills\obsidian-markdown\SKILL.md`.

## Hard Contract

- Produce or replace `source-transcript.md` as the only required deliverable.
- Treat `doc2x/export/export.md` as a rich reference, not as canonical output.
- Use `doc2x/page-transcript.raw.md` or source page markers to preserve order, but do not emit generic visible headings like `## Page N`.
- The top title must describe the actual document or knowledge area; never use `# Source Transcript`.
- Do not depend on downstream builders, exporters, print workflows, or other skills.
- Do not paste a very long OCR markdown file into one prompt and pretend it was fully read. For long markdown, use the Parallel Chunking Workflow (`references/parallel-chunking.md`).
- Keep content source-faithful, but actively regenerate bad OCR Markdown structure.
- Do not continue beyond Markdown inside this skill.
- **PDF extraction allowed only as a proofreading aid**: you may render PDF pages to images for visual comparison, but never treat the rendered images or the PDF itself as a source for text extraction — use the Doc2X OCR markdown for that.
- **Doc2X is the primary source**: always use `doc2x/page-transcript.raw.md` as your base text. Do NOT use third-party image OCR tools (MCP screenshots, etc.) as a substitute — they produce worse results and miss content. The Doc2X export is the authoritative transcription.
- **Preserve ALL detail**: never summarize, condense, or remove derivation steps from analysis sections. Every step of every method (法一, 法二, 法三) must be preserved in full. Missing detail is a critical failure.
- **NEVER upload a full PDF to Doc2X when specific pages are requested**. When the user provides a PDF with a page range (e.g., "pages 6-36"), you MUST use `scripts/extract_and_submit.py --pdf <path> --pages <range> --output-dir <job>` to extract a sub-PDF first, then submit ONLY the sub-PDF to Doc2X. Uploading the full source PDF is a CRITICAL FAILURE that wastes the user's paid OCR quota. The script enforces this with a ratio guard (requests >60% of pages require explicit `--confirm-large`).
- **PDF outline is the heading-level ground truth**. When `doc2x/outline.md` exists and contains real bookmark entries (i.e. `extract-manifest.json` has `"has_outline": true`), the Markdown's heading depth (`#`/`##`/`###`/…) MUST follow the outline's indentation depth. Headings must not be assigned by feel or by OCR-implied structure alone. When the outline is empty (no PDF bookmarks), fall back to the original semantic judgment. See "标题层级参照" in `references/canonical-markdown-rules.md`.

## Forbidden Patterns (always in force)

F1–F5 are critical-failure patterns from past sessions. The one-line summary: **no regex for semantic rewrites (F1); no `\$` in regex replacements (F2); no unauthorized LaTeX conversions (F3); no dismissing user complaints without byte-level verification (F4); no silent chunk-boundary duplication (F5).** Read `references/forbidden-patterns.md` for the full reasoning and code examples before starting — these apply at every step.

## Preconditions & Skill Boundaries

**This skill REQUIRES pre-existing Doc2X OCR output.** It rewrites and cleans existing markdown — it does NOT perform OCR itself. If Doc2X has not been run, use the `scan-pdf-to-print-html` skill (which includes `doc2x_parse_job.py`) to run the full OCR pipeline first.

**Input handling**:

| Input | Status | Action |
|-------|--------|--------|
| `doc2x/page-transcript.raw.md` + `doc2x/export/export.md` | **Ideal** | Proceed with rewrite |
| PDF only, no Doc2X output | **Blocked** | Tell user: "Doc2X OCR not found. Run `scan-pdf-to-print-html` skill first, or manually upload PDF to Doc2X and provide the output files." |
| PDF + `page-transcript.raw.md` | **OK** | Proceed; use PDF only for proofreading images |
| Standalone markdown (no doc2x/) | **OK** | Proceed as-is, skip OCR quality gate |

**If you have a PDF but no Doc2X output**: You MUST run `scripts/extract_and_submit.py` to extract a sub-PDF (if page range specified) and prepare it for Doc2X submission. Do NOT submit the full source PDF directly — it wastes the user's OCR quota and is a Hard Contract violation.

```
py -3 scripts/extract_and_submit.py --pdf "C:\path\source.pdf" --pages 6-36 --output-dir "C:\path\job\"
```

The script writes `doc2x/source-pages.pdf` (the sub-PDF) and `doc2x/extract-manifest.json`. Submit ONLY the sub-PDF to Doc2X. If no page range is needed and the PDF is small (≤10 pages), use `--allow-full-pdf`.

## Inputs

Accept any of these: `doc2x/page-transcript.raw.md`; `doc2x/export/export.md`; `doc2x/export/images/`; an existing `source-transcript.md`; rendered page images the user provides; a standalone Doc2X markdown file; **a PDF file path** (with optional page range) for proofreading images via `scripts/extract_pdf_pages.py`. If only one Doc2X markdown file is provided, still apply this skill and write a new canonical markdown file beside it unless the user gives a different destination.

## Workflow

### Step 0 — Assess & Plan

1. **Determine document size**: count `## Page N` markers, total lines, and total characters.
2. **Decide execution mode**:
   - Small (≤ 6 pages or ≤ 300 lines): single-thread, full-file processing through Steps 1–7.
   - Large (> 6 pages or > 300 lines): use the **Parallel Chunking Workflow** (`references/parallel-chunking.md`), then continue with Steps 1-7 on the assembled result.
3. **Gather inputs**: confirm access to the raw transcript, page images for visual comparison, and any existing `source-transcript.md`.
4. **Load the heading-level ground truth**: check whether `doc2x/outline.md` exists and whether `doc2x/extract-manifest.json` reports `"has_outline": true`.
   - If yes → read `doc2x/outline.md` and treat its indentation depth as the authority for Markdown heading levels throughout this run. Carry it into every chunk and every self-check.
   - If `outline.md` is absent (older job) or `has_outline: false` (no PDF bookmarks) → proceed without it and fall back to semantic judgment; do NOT block.
5. **Verify upstream OCR quality** (GATE — if this fails, stop and inform the user):
   - Scan the raw transcript for signs of poor OCR parameters: broken `\frac` commands, missing `\` before LaTeX commands, garbled formula fragments, or unusually low formula count for a math document.
   - If formulas are systematically garbled (not just occasional typos), the OCR parameters were likely wrong (e.g., `formula_level=0` instead of `formula_level=1`). STOP and tell the user the raw input quality is too poor — do not attempt to rewrite garbage.
   - This is a **pre-condition gate**: rewriting cannot fix systematic OCR parameter errors.

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

- If no `--pages` is given, all pages are rendered. Output: `pdf-pages/page-001.png`, etc., plus `pdf-pages/manifest.json`.
- Use these images in Step 2 (Proofread). This step is **optional**: if the user only provides Markdown (no PDF), skip it.
- Page selection: "proofread pages 3-7" → `--pages "3-7"`; PDF without pages → render all; PDF + markdown → render only the pages matching the markdown content.

### Step 1 — Auto-Fix (Mechanical Cleanup)

Read `references/auto-fix-rules.md` and apply its rules in exact execution order (remove residual symbols → remove noise → normalize delimiters → split formulas → fix spacing → standardize fractions → normalize blanks → fix OCR characters). These are mechanical text transformations — execute without hesitation.

**Critical notes**:
- **Noise removal**: remove ALL Doc2X-internal artifacts (`<!-- doc2x score: N -->`, `<!-- Meanless: ... -->`, `<!-- Media -->`, `<!-- figureText: ... -->`, page-number lines like `N 老唐说题`, chapter headers like `第 N 章 导 数`). Do NOT leave `__________` fill-in-blank artifacts — section separators must be `---`, not `__________`.
- **Fraction standardization**: `\frac` → `\dfrac` for display-level; `\tfrac` for nested/inline. Inline math (`$...$`) prefers `\tfrac` to avoid line-height disruption.
- **Callout syntax check**: every `[!question]`/`[!example]`/`[!note]` must have a `> ` prefix. Bare `[!question]` without `>` is a syntax error.

### Step 1-GATE — Auto-Fix Stop-Gate (MANDATORY)

Before proceeding to Step 2, run the **7 mandatory verification checks** in `references/auto-fix-gate.md`. If ANY check fails, fix before continuing. This gate runs again after Step 2.7 assembly — formula integrity (`$` count, `\begin{array}` count, callout count) must survive every rewrite pass.

### Step 2 — Proofread (Quality Verification)

Read `references/proofreading-checklist.md` and compare the auto-fixed transcript against source page images page by page. Use the Step 0-A images (`pdf-pages/page-*.png`) if extracted, else whatever the user provided.

**Paragraph splitting rule** (carried into Steps 2.5 and 2.7): analysis paragraphs must be split at logical break points; each paragraph should be ≤ ~300 characters (formulas excluded). Split at punctuation（句号、分号、冒号）, new formula expressions, logic transitions（故/所以/因此/又因为/此时）, and method boundaries（法一/法二/法三）.

**Key checks**: (1) per-page image comparison; (2) Chinese/English typos (易知 not 易如, 必须有 not 必需有, 根据 not 根); (3) structure integrity; (4) cross-page integrity; (5) `[TO VERIFY]` marker management; (6) paragraph length ≤ 300 chars; (7) **Math-sense consistency** (added 2026-06-29): OCR can produce formula chains that are *transcription-faithful but mathematically impossible* — e.g. `i^{10+10+1}`, `(i²)^{505} = -2^{1010}`, `cos θ + sin θ` (dropped `i`). Do **not** blindly trust the raw transcript for *math correctness* — it is authoritative for *characters*, not for *math*. Scan each chain: does it hold? If impossible AND recoverable from context, fix and note it; if unrecoverable, mark `[TO VERIFY: 公式 OCR 损坏，数理不自洽]`. This is the *active* counterpart to F4's reactive byte-level check.

### Step 2.5 — Analysis Block Re-typesetting (Subagent-Driven)

**MANDATORY for documents with analysis/solution sections (解析/解/证明).** Doc2X dumps each analysis section as one massive unbroken paragraph; re-typeset each block into clean paragraphs and fix OCR typos.

**Scope**: mechanical paragraph *splitting* inside a single analysis block only (排版). The whole question-block structure is handled separately by Step 2.7 — do not let the two overlap.

**Full rules, subagent template, and verification commands**: read `references/analysis-retypesetting.md`. Quick reference: ≤ 3 examples → do it inline; > 3 examples → dispatch subagents (3-5 per subagent); after completion verify `$` count, `\begin{array}` count, and callout count are unchanged.

**Dispatch runtime**: host-native subagent (default) or the pre-registered OpenCode `analysis-retypesetter` agent (if detected). See `references/opencode-agent-invocation.md`.

### Step 2.7 — Question Block Rewrite (MANDATORY for question-heavy documents)

**MANDATORY for documents containing 例题/练习/Q&A blocks.** Runs after Step 2.5, before Step 3. OCR produces structurally messy question blocks (stems as plain paragraphs, options scattered, sub-parts crammed, analysis as one lump). **Rewriting is reliable** where auditing is not: the subagent rewrites each block cleanly against `doc2x/page-transcript.raw.md`, fixing every structural defect.

**Method** (rewrite, not audit): main agent locates every question block; each subagent reads the block's current state + the raw passage, rewrites per `references/question-block-rewrite-guide.md` (stem → `> [!question]` callout, options → table, sub-questions → own lines, analysis → ≤300-char paragraphs), fixes OCR typos, marks key points per `references/emphasis-and-color-rules.md` (≤2 per block), and may use the single-page re-OCR escape hatch on genuine content doubt. Main agent reassembles, then re-runs Step 1-GATE + Step 4 validator to confirm formula integrity survived.

**Do NOT rewrite**: pure knowledge-point narrative, section intros, summary tables without questions.

**Full rules, subagent template, single-page re-OCR appeal procedure, and self-checks**: read `references/question-block-rewrite-guide.md`.

**Dispatch runtime**: host-native subagent (default) or the pre-registered OpenCode `question-block-rewriter` agent (if detected). See `references/opencode-agent-invocation.md`.

### Step 3 — Structural Format (Canonical Markdown)

Read `references/canonical-markdown-rules.md` and apply it to the proofread transcript.

**Parser choice**: for formula-heavy math content, use **plain Markdown** for analysis (`**解析**`/`**解**` with paragraph breaks), NOT `<div class="analysis-block">` HTML (which requires MathML for all formulas — impractical). Use the HTML form only for zero-formula pure-text analysis.

**Long formulas**: display formulas > one line use `\begin{aligned}` with `\\` breaks, split at `=`/`+`/`-`/logical boundaries.

**Emphasis & color**: apply `references/emphasis-and-color-rules.md`. Downgrade mis-marked headings to bold/italic/color (don't delete); mark key points (conclusions/pitfalls/techniques) sparingly per the fixed four-color palette, color spans wrapping pure text only.

### Step 4 — Auto-Validate & Fix (HARD GATE)

**HARD GATE.** The validator must return exit code 0 before Step 5 or completion. If it reports FAIL, fix and re-run until it passes. Do NOT skip, do NOT proceed with known failures, do NOT claim ready if not passed.

The validator checks: fraction nesting (`lint_fraction_nesting`, brace-depth parser), Q&A ordering (`lint_qa_ordering`), analysis paragraph length (`lint_markdown_analysis_paragraphs` — structural evidence Step 2.7 ran), and question callout title line (`lint_question_callout_title_attached`).

**Two lint families — diagnose separately** (2026-06-28 lesson), or you can loop forever:
- **Rewrite-structure lints** = Step 2.7 rewrite-failure signals (`lint_question_callout_title_attached`, `lint_choice_options`, `lint_bare_question_starts`, `lint_qa_ordering`, `lint_markdown_analysis_paragraphs`). Fix by re-running Step 2.7.
- **Formula-normalization lints** = NOT a rewrite failure (`lint_fraction_nesting`, `lint_inline_math_spacing`, `lint_html_math`). The rewrite says "preserve LaTeX verbatim", so keeping `$\sqrt{1+\dfrac{1}{4}}$` intact is CORRECT — fix with `--fix` or a targeted edit, NOT by re-running Step 2.7.

**Known validator glitch — `lint_markdown_analysis_paragraphs` vs `\mathrm{}` tokens** (2026-06-29): the math-stripper can mis-split on `\mathrm{}` tokens (e.g. `\mathrm{i}\sin`), counting LaTeX fragments as prose. Symptom: a short line (~15 true chars) flagged as `prose chars=312`. **False FAIL** — verify actual prose length by hand; if genuinely short, insert a blank line between adjacent sub-answer lines. Do NOT re-run Step 2.7, do NOT delete `\mathrm{}` to appease the counter.

Run:
```
py -3 scripts/validate_canonical_markdown.py --md "C:\path\source-transcript.md" --fix
py -3 scripts/fix_callout_prefixes.py --md "C:\path\source-transcript.md" --fix
```

**Known limitations**: `--fix` may corrupt `---` → `__________` (Rule 5) — verify separators after. `fix_callout_prefixes.py` may wrongly prefix `##`/`###` lines — verify headings after.

### Step 5 — Quality Validation

```
py -3 scripts/validate_canonical_markdown.py --md "C:\path\source-transcript.md" --check-proofreading
```

**Known false positives** (do NOT waste time): "unclosed `$`/`$$` delimiter" (from `$$`-containing-`$`); "suspicious [已] near [己/巳]" / "[入] near [人]" (legitimate chars; verify once, dismiss; `\left\{`/`\begin{array}` often falsely flagged); "unbalanced braces" (valid `\left\{...\begin{array}...\end{array}\right.`); "HTML must use MathML" (`$...$` in choice-grid spans). If ALL failures are only these, report "confirmed false positives" and pass. Fix all others; re-run until only false positives remain.

### Step 6 — Self-Check (LESSONS LEARNED CHECKLIST)

Run the full self-check in `references/self-check.md`. **For every command-based check, paste the actual command output into your report** — do not just tick the box. Claims without evidence are treated as failures. For any N/A item, write "N/A — [reason]" instead of omitting it.

### Step 6.5 — Write Frontmatter Intent (for handout-bound documents)

If the rewritten `source-transcript.md` is destined for the `scan-pdf-to-print-html` handout pipeline (讲义-type, not a one-off note), record pagination + cover intent in frontmatter so `scan` doesn't re-ask.

1. Use ONE AskUserQuestion (batched): **pagination-level** (`h2` default, or `h3` when sub-sections live at h3 — e.g. an extracted chapter); **cover** (`true`/`false`).
2. Write as a leading YAML block at the very top:
   ```yaml
   ---
   pagination-level: h3
   cover: true
   ---
   ```
   Prepend before the existing first line (`# Title`). Do not modify the title or content.
3. If unsure or not handout-bound, skip — `scan` will ask via its own batched prompt.

**Field spec**: see `scan-pdf-to-print-html/references/frontmatter-spec.md`. Only these two fields are recognized; do not invent others.

### Step 7 — Report

Report only Markdown status:
- path to `source-transcript.md`
- whether `validate_canonical_markdown.py --fix` passed or failed
- whether `validate_canonical_markdown.py --check-proofreading` passed or failed
- number of unresolved `[TO VERIFY: ...]` markers and their page locations
- chunks or pages that need human review

Do not claim that downstream output is ready. High-quality Markdown is the handoff.

---

## Required Markdown Structures

Follow `references/canonical-markdown-rules.md` for the complete formatting specification. Do not deviate from or skip any formatting rules in that reference.

## Output Boundary

At completion, report only Markdown status (per Step 7). Do not claim that downstream output is ready. High-quality Markdown is the handoff.
