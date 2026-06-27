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
- `references/analysis-retypesetting.md` — detailed rules and subagent template for Step 2.5 analysis re-typesetting
- `references/question-block-rewrite-guide.md` — detailed rules and subagent template for Step 2.7 question-block rewrite against the raw transcript
- `references/emphasis-and-color-rules.md` — bold/italic and semantic-color marking: mis-marked heading downgrade, proactive key-point marking, fixed color palette, formula-conflict handling

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
- **NEVER upload a full PDF to Doc2X when specific pages are requested**. When the user provides a PDF with a page range (e.g., "pages 6-36"), you MUST use `scripts/extract_and_submit.py --pdf <path> --pages <range> --output-dir <job>` to extract a sub-PDF first, then submit ONLY the sub-PDF to Doc2X. Uploading the full source PDF is a CRITICAL FAILURE that wastes the user's paid OCR quota. The script enforces this with a ratio guard (requests >60% of pages require explicit `--confirm-large`).
- **PDF outline is the heading-level ground truth**. When `doc2x/outline.md` exists and contains real bookmark entries (i.e. `extract-manifest.json` has `"has_outline": true`), the Markdown's heading depth (`#`/`##`/`###`/…) MUST follow the outline's indentation depth. Headings must not be assigned by feel or by OCR-implied structure alone. When the outline is empty (no PDF bookmarks), fall back to the original semantic judgment. See "标题层级参照" in `references/canonical-markdown-rules.md`.

## Preconditions & Skill Boundaries

**This skill REQUIRES pre-existing Doc2X OCR output.** It rewrites and cleans existing markdown — it does NOT perform OCR itself. If Doc2X has not been run, use the `scan-pdf-to-print-html` skill (which includes `doc2x_parse_job.py`) to run the full OCR pipeline first.

**Input handling**:

| Input | Status | Action |
|-------|--------|--------|
| `doc2x/page-transcript.raw.md` + `doc2x/export/export.md` | **Ideal** | Proceed with rewrite |
| PDF only, no Doc2X output | **Blocked** | Tell user: "Doc2X OCR not found. Run `scan-pdf-to-print-html` skill first, or manually upload PDF to Doc2X and provide the output files." |
| PDF + `page-transcript.raw.md` | **OK** | Proceed; use PDF only for proofreading images |
| Standalone markdown (no doc2x/) | **OK** | Proceed as-is, skip OCR quality gate |

**If you have a PDF but no Doc2X output**: You MUST run `scripts/extract_and_submit.py` to extract a sub-PDF (if page range specified) and prepare it for Doc2X submission. Do NOT submit the full source PDF directly — this wastes the user's OCR quota and is a Hard Contract violation.

```
py -3 scripts/extract_and_submit.py --pdf "C:\path\source.pdf" --pages 6-36 --output-dir "C:\path\job\"
```

The script writes `doc2x/source-pages.pdf` (the sub-PDF) and `doc2x/extract-manifest.json`. Submit ONLY the sub-PDF to Doc2X. If no page range is needed and the PDF is small (≤10 pages), use `--allow-full-pdf`.

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

## Forbidden Patterns (LESSONS LEARNED)

These patterns caused critical failures in past sessions. Violating them is a critical error.

### F5 — No silent chunk-boundary duplication

When dispatching subagents for parallel chunking, **each chunk must process its assigned pages and STOP** — never continue into the next chunk's content. If a section heading (e.g., `## 题型-3`) appears at the boundary between chunk N and chunk N+1, it belongs to **chunk N+1 only**, not both.

After assembly, if duplicate section headers or duplicate bullet points appear at chunk boundaries, remove the duplication immediately. The assembler is responsible for clean boundaries — subagents must not "helpfully" include the next section's opening.

### F1 — No regex for semantic rewrites

**NEVER** use Python `re.sub()`, `str.replace()`, or any script to perform:
- Fused formula splitting (Rule 4) — requires understanding which commas separate independent formulas
- Paragraph splitting — requires understanding logical break points
- Structural formatting (callouts, bold markers) — requires understanding document structure
- Analysis block re-typesetting — requires understanding reasoning flow

These transformations need **semantic understanding**. Use subagents to read and edit manually, chunk by chunk.

**Scripts are ONLY allowed for**: pure mechanical substitution (`\(` → `$`), noise tag deletion, `\frac` → `\dfrac`, and other single-pattern replacements that cannot misfire.

> **F6 (no regex for fraction nesting) has been removed** — the `lint_fraction_nesting` validator now automates this check with a brace-depth parser. See Step 4.

### F2 — No `\$` in regex replacement strings

**NEVER** write `re.sub(pattern, r'\$', text)` or `re.sub(pattern, '\\$', text)`. In Python, the replacement string `r'\$'` inserts a literal backslash + dollar sign (`\$`), corrupting every `$` in the document.

**Correct way** to strip boundary spaces from `$ a $`:
```python
text = re.sub(r'\$ +', '$', text)   # plain string, NOT raw string with backslash
text = re.sub(r' +\$', '$', text)
```

### F3 — No unauthorized format conversions

**NEVER** convert `\begin{array}` to `\begin{cases}`, `\left\{` to other brace constructs, or change any LaTeX structural macro from Doc2X output. The Doc2X formulas are authoritative — only split fused formulas and move punctuation; never alter the internal LaTeX structure.

### F4 — No dismissing user complaints without byte-level verification

When a user reports a problem (e.g., "the formulas look wrong"):
1. **Immediately check the actual file bytes** — use `Read` tool or `grep` on the file, not reasoning
2. If the problem exists, fix it
3. If you believe it doesn't exist, **show the evidence** (actual byte content) and let the user judge
4. **NEVER** claim "it's just a rendering issue" without checking the raw file content first

## Workflow

### Step 0 — Assess & Plan

1. **Determine document size**: count `## Page N` markers, total lines, and total characters.
2. **Decide execution mode**:
   - Small (≤ 6 pages or ≤ 300 lines): single-thread, full-file processing.
   - Large (> 6 pages or > 300 lines): use the Parallel Chunking Workflow (see below), then continue with Steps 1-7 on the assembled result.
3. **Gather inputs**: confirm you have access to the raw transcript, page images for visual comparison, and any existing `source-transcript.md`.
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

### Step 1-GATE — Auto-Fix Stop-Gate (MANDATORY)

Before proceeding to Step 2, run these **mandatory verification checks**. If ANY check fails, go back and fix before continuing. Do NOT skip this gate.

```bash
# Check 1: No fused formulas remain (Rule 4)
# Look for commas between independent relations inside $...$
rg -n '\$[^$]*[，,][^$]*[=<>≥≤][^$]*\$' source-transcript.md
# If any results appear that contain TWO independent relations split by a comma, they must be split.
# Exception: a single relation with a comma in a function argument like $f(x,y)$ is NOT fused.

# Check 2: No boundary spaces in inline math (Rule 2)
rg -n '\$ +[^\$]' source-transcript.md   # opening $ followed by space
rg -n '[^\$] +\$' source-transcript.md   # closing $ preceded by space
# Both should return 0 results (excluding $$ display blocks).

# Check 3: No \$ corruption (Forbidden Pattern F2)
rg -n '\\\$' source-transcript.md
# Must return 0 results.

# Check 4: \begin{array} count unchanged (Forbidden Pattern F3)
# Count in source-transcript.md should match raw transcript
rg -c '\\begin\{array\}' source-transcript.md
rg -c '\\begin\{array\}' doc2x/page-transcript.raw.md
# Counts must be equal.

# Check 5: No \begin{cases} introduced
rg -c '\\begin\{cases\}' source-transcript.md
# Must be 0 unless raw transcript already had cases.

# Check 6: Every 例/例题 has a callout (structural rule)
rg -c '> \[!question\]' source-transcript.md
# Should match the number of examples in the document.

# Check 7: No example/exercise label sits OUTSIDE a callout (the downstream
# "examples have no quote block" defect). Run the validator's dedicated lint
# rather than a manual rg, because it correctly scopes to question callouts.
py -3 scripts/validate_canonical_markdown.py --md source-transcript.md
# A non-zero exit with "example/exercise stem must be wrapped in a `> [!question]`
# callout" means a 例题N/练习N paragraph is a bare paragraph. Fix by wrapping
# it (and its stem/options) in a `> [!question]` callout. Note: analysis
# (解析) paragraphs must stay OUT of callouts — only the question side is wrapped.
```

If any check fails, fix the issue and re-run the check before proceeding.

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

### Step 2.5 — Analysis Block Re-typesetting (Subagent-Driven)

**This step is MANDATORY for documents with analysis/solution sections (解析/解/证明).**

Doc2X dumps each analysis section as one massive unbroken paragraph. Use subagents to re-typeset each block into clean paragraphs and fix OCR typos.

**Scope of this step**: mechanical paragraph *splitting* inside a single analysis block only (排版). The **whole question-block structure** (stem → callout, options → table, sub-questions → own lines, analysis → paragraphs) is handled separately by Step 2.7. Do not let the two steps overlap.

**Full rules, subagent template, and verification commands**: see `references/analysis-retypesetting.md`.

Quick reference:
- ≤ 3 examples: do it inline (read and edit each block yourself)
- > 3 examples: dispatch subagents (3-5 examples per subagent)
- After completion: verify `$` count, `\begin{array}` count, and callout count are unchanged

### Step 2.7 — Question Block Rewrite (MANDATORY for question-heavy documents)

**This step is MANDATORY for documents containing 例题/练习/Q&A blocks.** It runs after Step 2.5 and before Step 3.

**Why this step exists**: OCR produces structurally messy question blocks — stems dumped as plain paragraphs, options scattered outside the question, sub-parts crammed on one line, analysis as one giant lump, sentences displaced between stem and analysis. Auditing (find problems then fix) is unreliable because the model often fails to notice the problems. **Rewriting is reliable**: the subagent rewrites each question block cleanly against `doc2x/page-transcript.raw.md`, and the rewrite itself fixes every structural defect without needing to detect them first.

**Method** — rewrite, not audit:

1. The main agent scans `source-transcript.md` and locates every question block (each `例题N` / `练习N` / `例` / Q&A unit: stem + options + sub-questions + its analysis).
2. **For long documents**: reuse the Parallel Chunking page ranges — each chunk's subagent handles the question blocks within its pages. Do not scan twice.
3. Each subagent:
   - Reads the block's current state in `source-transcript.md`.
   - Reads the corresponding passage in `doc2x/page-transcript.raw.md` (locate by page marker/position). **The raw transcript is the content truth.**
   - Rewrites the block cleanly per `references/question-block-rewrite-guide.md`: stem → `> [!question]` callout, options → markdown table, sub-questions → own lines, analysis → paragraphs `≤300` chars.
   - Fixes OCR typos and moves displaced sentences back where they belong, by comparing to the raw passage.
   - **Marks key points** per `references/emphasis-and-color-rules.md`: in each rewritten block, sparingly mark the conclusion sentence (purple `#9370DB`), any 易错/警示 (red), and technique/口诀 names (green) — at most 1-2 marks per block, color spans wrap pure text only (never `$...$`), and headings flagged as not-a-heading-but-emphasis are downgraded to emphasis rather than deleted.
   - **Single-page re-OCR appeal (escape hatch)**: if and only if the subagent genuinely doubts a symbol/number/word in the raw passage (content doubt, NOT structure mess), it may re-OCR that **one page only** — extract with `extract_and_submit.py --pages <N> --allow-full-pdf`, submit to Doc2X, compare. If the retry does not resolve the doubt, **stop and mark `[TO VERIFY: 单页重 OCR 仍不清晰，疑 PDF 原文模糊]`** — do not re-OCR again, do not expand to neighboring pages. The PDF itself is likely unclear.
4. The main agent reassembles the subagents' rewritten blocks into `source-transcript.md`.
5. After assembly, run the existing Step 1-GATE checks and Step 4 validator to confirm formula integrity (`$` count, `\begin{array}` count, callout count) survived the rewrite.

**Do NOT rewrite**: pure knowledge-point narrative (知识点叙述), section intros, summary tables without questions — OCR handles those well enough.

**Full rules, subagent template, single-page re-OCR appeal procedure, and self-checks**: see `references/question-block-rewrite-guide.md`.

### Step 3 — Structural Format (Canonical Markdown)

Apply `references/canonical-markdown-rules.md` to the proofread transcript.

**Parser choice rule:**
For formula-heavy math content (calculus, algebra with many inline formulas), use **plain Markdown** for analysis sections (`**解析**` / `**解**` with regular paragraph breaks), NOT `<div class="analysis-block">` HTML blocks. The HTML analysis-block format requires MathML for all formulas inside it, which is impractical for complex math content. Use the exemption clause: *"If an HTML formula is too complex to express safely as MathML and SVG generation is not available, move that content out of HTML and rewrite it as normal Markdown."*

Only use `<div class="analysis-block">` when the analysis section contains ZERO formulas (pure text).

**Long formula formatting:**
For display formulas longer than one line, use `\begin{aligned}` with `\\` line breaks. Split at `=` signs, `+`/`-` operators, or logical boundaries. Every long formula must be readable without horizontal scrolling.

**Emphasis & color:**
Apply `references/emphasis-and-color-rules.md`. Check two things: (1) any line flagged by the heading validator as not-a-heading but genuinely an emphasis intent is downgraded to bold/italic or a semantic color (not deleted); (2) key points worth marking (conclusions, pitfalls, techniques) are marked per the fixed four-color palette — sparingly, with color spans wrapping pure text only.

### Step 4 — Auto-Validate & Fix (HARD GATE)

**This step is a HARD GATE.** The validator must return exit code 0 before you can proceed to Step 5 or report completion. If the validator reports FAIL, you MUST fix the issues and re-run until it passes. Do NOT skip this step, do NOT proceed with known failures, and do NOT claim the document is ready if the validator has not passed.

The validator now checks:
- **Fraction nesting** (`lint_fraction_nesting`): `\dfrac` inside another fraction's braces/exponent/subscript/sqrt should be `\tfrac`; `\tfrac` in non-nested context (e.g., `\ln` argument) should be `\dfrac`. This is a brace-depth parser — it catches what regex cannot.
- **Q&A ordering** (`lint_qa_ordering`): consecutive `[!question]` callouts without analysis between them are flagged. Each question's analysis must follow directly.
- **Markdown analysis paragraph length** (`lint_markdown_analysis_paragraphs`): this is the **structural evidence that Step 2.7 (question-block rewrite) actually ran**. It flags any plain-Markdown `**解析**` / `**解**` / `**证明**` paragraph whose PROSE exceeds 300 chars (math content stripped before counting, so a long LaTeX display formula with short prose does NOT false-positive). A skipped or sloppy Step 2.7 leaves OCR's one-giant-paragraph analysis dumps intact, and this lint catches exactly that. **This lint is non-auto-fixable** — over-long analysis cannot be fixed by regex; the fix is to re-run Step 2.7 against the raw transcript. If this lint fires, the document is NOT ready.

Run the validator in fix mode to handle any residual mechanical issues:

```
py -3 scripts/validate_canonical_markdown.py --md "C:\path\source-transcript.md" --fix
```

or:

```
py -3 scripts/validate_canonical_markdown.py --job-dir "C:\path\job" --fix
```

After `--fix`, check for callout prefix issues:

```
py -3 scripts/fix_callout_prefixes.py --md "C:\path\source-transcript.md" --fix
```

This auto-corrects: math spacing, delimiter normalization, fraction standardization, blank line splits, header noise, leading orphan punctuation, and callout prefix integrity.

**Known validator limitations:**
The `--fix` mode may incorrectly transform `---` (horizontal rule) into `__________` (fill-in-blank) due to Rule 5 (Fill-in-Blank Normalization). After running `--fix`, visually check that section separators remain as `---` and haven't been corrupted.

The `fix_callout_prefixes.py` script may add `> ` to lines that are intentionally outside callouts. After running it, verify that standalone paragraphs and section headers were not incorrectly prefixed. Lines starting with `##` or `###` should NOT receive a `> ` prefix.

### Step 5 — Quality Validation

Run the validator in proofreading mode:

```
py -3 scripts/validate_canonical_markdown.py --md "C:\path\source-transcript.md" --check-proofreading
```

**Known false positives** (do NOT waste time on these):
- "possible unclosed inline math `$` delimiter" — triggered by `$$...$$` blocks that contain `$` inside them; these are NOT actual errors in formula-heavy content.
- "suspicious character [已] near [己/巳]" and "[入] near [人]" — these are legitimate Chinese characters that appear correctly in context. Verify once, then dismiss. Also note: `\left\{` and `\begin{array}` patterns are often falsely flagged as containing "已" due to the `{` character.
- "possible unclosed display math `$$` delimiter" — same as above, false alarm.
- "unbalanced braces" — triggered by `\left\{ \begin{array}{l} ... \end{array}\right.` patterns. These are valid LaTeX constructs, not actual brace errors. Verify by counting `\left`/`\right` pairs and `\begin{array}`/`\end{array}` pairs match.
- "HTML content must use MathML or inline SVG for formulas" — triggered by `$...$` inside `<span>` elements in choice grids. For formula-heavy math content, this is impractical. The canonical rules explicitly allow plain Markdown for math-heavy analysis sections. This is a known validator limitation.

If ALL failures are only these known false positives, report them as "confirmed false positives" and pass the step.

Fix all other reported issues (unclosed formulas, heading jumps, missing options, suspicious characters). Re-run until only false positives remain.

### Step 6 — Self-Check (LESSONS LEARNED CHECKLIST)

Before reporting, run through this checklist. **For every command-based check, paste the actual command output into your report** — do not just tick the box. Claims without evidence are treated as failures.

#### Evidence-based checks (run command, paste output)

Run each command and include the output in your report. **Do not skip any check.** If a check is not applicable, write "N/A — [reason]" instead of omitting it.

1. **No \$ corruption**: `rg -c '\\\$' source-transcript.md` → must be 0
2. **No \begin{cases} introduced**: `rg -c '\\begin\{cases\}' source-transcript.md` → must match raw transcript count
3. **\begin{array} preserved**: `rg -c '\\begin\{array\}' source-transcript.md` vs `rg -c '\\begin\{array\}' doc2x/page-transcript.raw.md` → source must be >= raw. Note: `\begin{array}` inside `\left\{` constructs is correct — do NOT count these as errors.
4. **Fused formulas split**: `rg -n '\$[^$]*[，,][^$]*[=<>≥≤][^$]*\$' source-transcript.md` → no independent relations fused. Note: `\begin{array}` rows with `,` separators are NOT fused formulas.
5. **Paragraph length**: `rg -n '.{300,}' source-transcript.md` → remaining long lines must be pure formula blocks only
6. **HTML comment integrity**: `rg -n '<!_' source-transcript.md` → must be 0 (Rule 5 corruption check)
7. **No inline-style display math**: `rg -n '^\$\$.+\$\$$|^> \$\$.+\$\$$' source-transcript.md` → must be 0; display math uses standalone `$$` delimiter lines.
8. **`--fix` pass**: `validate_canonical_markdown.py --fix` → PASS, except for known false positives (HTML/MathML warnings for formula-heavy content)
9. **Proofreading**: `validate_canonical_markdown.py --check-proofreading` → only known false positives remain (suspicious character, unbalanced braces from `\begin{array}`)
10. **Image sizing**: `rg -n 'max-width:72%|max-width:45%' source-transcript.md` → must be 0 (images should use max-width:36% for single, max-width:22.5% for double, per canonical rules)

#### Judgment-based checks (verify, mark pass/fail)

You MUST check all items below. Do not skip any. If an item is not applicable, write "N/A — [reason]" instead of omitting it.

- [ ] **Callout syntax**: every `[!question]`, `[!example]`, `[!note]`, `[!warning]` has `> ` prefix (use `rg -n '^\[!'` to verify — any match means a broken callout)
- [ ] **Subpart line breaks**: every `(1)`/`(2)`/`(3)` question subpart inside a callout is on its own `>` line — no single `>` line contains two or more `(N)` subparts (grep suspect lines with `rg -n '\([0-9]+\)[^(]*\([0-9]+\)'` inside callout regions, then confirm each remaining hit is a false positive like coordinate pairs)
- [ ] **Comma consistency & spacing**: every English `,` is followed by exactly one space (never glued like `,x`), no double spaces after a comma, and no paragraph/callout mixes `，` and `,` (grep `rg -n ',[^ \n,)]'`; confirm each remaining hit is a math/code false positive like `$f(x,y)$`)
- [ ] **Simple formula-list comma placement**: simple variable/symbol lists are split into separate inline math spans (`$m$, $n$`, `$\alpha$, $\beta$`, `${x}_{1}$, `${x}_{2} \in D$`); commas inside intervals, coordinates, function arguments, arrays, and complex formulas are preserved.
- [ ] **Semantic heading hierarchy**: inspect the rendered outline, not only heading-level jumps. Topic headings should own generic children such as `知识点总结`, `经典例题`, `归纳总结`, `特别地`, and `基本规律`; those child labels should not become siblings of their owning topic. **When `doc2x/outline.md` exists with real entries** (`has_outline: true`), this check is NOT optional guesswork: verify each Markdown heading's `#`-depth matches the outline entry's indentation depth (Level 1 → `#`, etc., applying the fixed offset from `references/canonical-markdown-rules.md` → "标题层级参照"). Mismatches must be corrected, not deferred to `[TO VERIFY]`.
- [ ] **解析 bold**: every analysis section has `**解析**` or `**解**` in bold
- [ ] **Content preservation**: ALL derivation steps preserved — no summarizing of 法一/法二/法三
- [ ] **Doc2X primacy**: content scope matches `doc2x/page-transcript.raw.md` — no detail removed
- [ ] **Noise removal**: no `<!-- doc2x score -->`, `<!-- Meanless -->`, `__________` artifacts, stray page numbers
- [ ] **Adjacent figures merged**: logically-grouped images (numbered 图1/图2/图3, multi-view of one figure, sub-cases with no prose between them) are merged into ONE `<figure style="display:flex;...">` with all `<img>` inside — never emitted as adjacent single-image `<figure>` blocks separated only by blank lines, which stack vertically. ✅ Automated by `lint_adjacent_figures_must_merge` (Step 4 validator). Prose-separated independent figures are NOT flagged.
- [ ] **Fraction rules**: ✅ Automated by `lint_fraction_nesting` (Step 4 validator). No bare `\frac`; nested fractions use `\tfrac`; function arguments use `\dfrac`. The validator's brace-depth parser catches both directions.
- [ ] **Long formulas**: display formulas > 60 chars use `\begin{aligned}` with line breaks
- [ ] **Horizontal rules**: `---` separators not corrupted to `__________`
- [ ] **OCR typos fixed**: confusable characters (已/己, 人/入, 末/未) verified in analysis blocks
- [ ] **Emphasis & color consistency**: semantic colors come only from the fixed palette (purple 结论 / red 易错 / green 口诀 / blue 备注) — same meaning = same color document-wide; color spans wrap pure text only, never `$...$` (verify `rg -n '<span[^>]*color[^>]*>[^<]*\$' source-transcript.md` returns nothing); no over-marking (at most 1-2 marks per analysis block); mis-marked headings were downgraded to emphasis rather than deleted.
- [ ] **Question-block rewrite (Step 2.7)**: report whether Step 2.7 ran, how many question blocks were rewritten against `page-transcript.raw.md`, whether all subagents carried the raw-transcript reference, and how many single-page re-OCR appeals were made (with outcomes). If the document had question blocks but Step 2.7 was skipped, that is a defect — question-block structure is the most common source of "unclean" output.
- [ ] **Chunk boundary clean**: if parallel chunks were used, no duplicate headings or bullet points at boundaries, and no bare callouts without `>` prefix
- [ ] **Q&A ordering**: ✅ Automated by `lint_qa_ordering` (Step 4 validator). Each question's analysis follows directly.
- [ ] **Image paths**: ✅ Automated by `lint_image_path` (Step 4 validator). Paths use `doc2x/export/images/...`.
- [ ] **Sweep-on-report**: if the user reports ANY rule violation on a specific instance, you MUST immediately sweep the ENTIRE document for all other instances of the same violation class — do not fix only the one the user pointed out

### Step 7 — Report

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
- Instructions: execute Steps 1 through 2.7 (auto-fix → stop-gate → proofread → analysis re-typesetting → **question-block rewrite**) on this chunk only, then apply Step 3 (structural format) formatting rules
- The current `canonical-markdown-rules.md`, `auto-fix-rules.md`, `analysis-retypesetting.md`, and `question-block-rewrite-guide.md` as reference
- **CRITICAL**: subagent must split fused formulas (Rule 4), re-typeset analysis blocks into logical paragraphs, rewrite each question block's whole structure against the raw transcript (stem → callout, options → table, sub-questions → own lines), and fix OCR typos — these are the most commonly missed steps
- **BOUNDARY RULE**: the subagent must NOT include content from the next chunk. If the chunk ends mid-page or at a section boundary, the subagent stops at its last assigned line. It must NOT "continue" into the next chunk to "finish the section"
- Output: cleaned Markdown for the chunk + `[TO VERIFY]` markers encountered

After each batch completes, check for failed chunks (subagent error or timeout > 5 min). Mark failed chunks in `markdown-rewrite-plan.md` and re-dispatch them in the next batch.

### Assembly

1. Concatenate chunks in page order.
2. **Critical — Callout Prefix Check**: After assembly, run `rg -c '^\[!question\]' source-transcript.md` and `rg -c '^\[!example\]' source-transcript.md`. If any result is > 0, STOP. The `>` prefix was lost during assembly. Fix immediately by prefixing all bare `[!question]` and `[!example]` lines with `> `.
3. Check chunk boundaries for:
   - **Duplicate content**: if the last section of chunk N is also the first section of chunk N+1, remove the duplicate. This commonly happens when a section heading appears on the boundary page. Keep the version from the chunk where the section's EXAMPLES/CONTENT live, not the chunk that only has the heading.
   - Truncated formulas or tables at page breaks.
   - Heading level consistency across chunks (adjacent chunks must not jump levels). **When `doc2x/outline.md` exists**, re-verify the assembled document's heading depths against the outline after concatenation — chunk-local decisions can drift at boundaries.
   - Duplicate or missing `## Page N` markers.
3. Merge all `[TO VERIFY: ...]` markers from subagent reports into a single list.
4. Run Step 1-GATE checks on the assembled document (fused formulas, `\$` corruption, `\begin{array}` count, callout count).
5. Run Steps 4-5 (validate --fix → validate --check-proofreading) on the assembled document.
6. Run Step 6 (self-check) on the assembled document.
7. Run a final read-through pass to verify callouts, analysis blocks, tables, formulas, and image references did not break during concatenation.

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
