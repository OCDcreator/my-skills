---
name: rewrite-doc2x-markdown
description: Use when Doc2X OCR markdown, Doc2X export.md, page-transcript.raw.md, or source-transcript.md is messy, too long, poorly structured, or must be rewritten into a high-quality canonical Markdown transcript before downstream use. Also use when the user provides a PDF file alongside or instead of Markdown — this skill can extract specified PDF pages as proofreading images to verify transcription quality.
---

# Rewrite Doc2X Markdown

Create a clean, canonical Markdown document from Doc2X OCR output. This skill starts after Doc2X has returned Markdown and stops at Markdown: do not run OCR, render layouts, export final documents, or use any downstream skill. The only exception: you **may** render PDF pages as proofreading images when the user provides a PDF file — this is a quality aid, not a downstream output.

This SKILL.md is the **orchestrator**. Detailed rules live in `references/` (Layer 3) and are read on demand — each step below names the reference file to read before acting.

## References (read on demand, per step)

- `references/refinement-agent-chain.md` — **the refinement chain (Steps 1.5 + 2.7)**: 9 single-responsibility roles (skeleton → source-merger → subparts → options-table → analysis-retypesetter → comma-splitter → typo → displacement → key-point), each with a path-independent `--only` self-check. **Read this before Step 1.5 and Step 2.7.** This is the single source for both the main-agent path (default) and the subagent path (opt-in).
- `references/auto-fix-rules.md` — Step 1 mechanical text transformations
- `references/auto-fix-gate.md` — Step 1-GATE 7 mandatory verification checks (commands)
- `references/proofreading-checklist.md` — Step 2 quality verification against source page images
- `references/analysis-retypesetting.md` — Step 2.5 analysis re-typesetting rules + subagent template (analysis is the SOLE domain of the `analysis-retypesetter` role in the chain)
- `references/question-block-rewrite-guide.md` — **fallback** rules for the legacy single-agent `question-block-rewriter` (the fine-grained chain in `refinement-agent-chain.md` is now the default; this guide is the fallback path)
- `references/canonical-markdown-rules.md` — Step 3 structural formatting spec for the final Markdown
- `references/emphasis-and-color-rules.md` — bold/italic and semantic-color marking (used in Steps 2.7 & 3)
- `references/forbidden-patterns.md` — F1–F5 failure patterns (LESSONS LEARNED), always in force
- `references/self-check.md` — Step 6 self-check checklist (evidence + judgment items)
- `references/parallel-chunking.md` — Parallel Chunking Workflow for large documents (> 6 pages / > 300 lines)
- `references/opencode-agent-invocation.md` — **optional** dispatch path: OpenCode agents (`md-cleaner`, the 8 refinement-chain roles, plus the legacy `question-block-rewriter`/`analysis-retypesetter`) with model + permissions + distilled prompt pre-configured. Use when the host detects `opencode` + the project's `.opencode/agents/`; fall back to host-native subagent otherwise.

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
- **Back up before rewriting.** Before any rewrite/clean pass that edits `source-transcript.md` in place, create a timestamped backup beside it (`source-transcript.md.bak-YYYY-MM-DD`, suffix `-2`/`-3` if a same-day backup exists). The rewrite touches the only canonical transcript; a bad auto-fix or an over-eager `--fix` is irreversible without the backup. <!-- evolved 2026-06-30 — rework: user explicitly required backup; rescued 3 frontmatter corruptions in the 概率 job -->
- **Default executor is the main agent; subagents are opt-in.** Every refinement role (Steps 1.5 + 2.7) is executed by the main agent itself by default — reading each role's logic from `references/refinement-agent-chain.md` and running that role's `--only` self-check inline. Dispatch to `.opencode/agents/*.md` happens **only when the user explicitly asks to use subagents** (e.g. "用子代理 / dispatch agents / parallelize"). The choice is the user's, never the skill's — do not auto-dispatch based on document size. <!-- evolved 2026-06-30 — rework: user feedback that the main agent can do these jobs itself; subagents made the task simpler per-role but are not the default path -->
- **Path-independent self-check after every role.** Whichever executor runs a refinement role (main agent OR subagent), it MUST run that role's `--only` lint (`py -3 scripts/validate_canonical_markdown.py --md <file> --only <role's lints>`) right after editing, fix any FAIL in place, and retry up to 3 times. Still-failing after 3 retries → mark `[TO VERIFY: <role> self-check 未通过]` and move on (do NOT loop forever). This minimizes rework: a defect is caught inside the role before the next role ever sees it. **BUT: a passing `--only` lint is necessary, not sufficient — the lints are coarse nets with known blind spots.** For the semantic roles this matters most: ③'s `lint_list_inside_math` is SILENT on point/equation/variable fusion (`$A(...),B(...)$`, `$f=1,g=2$`, `$A,B,C$`); ⑤'s `lint_markdown_analysis_paragraphs` only checks paragraph *length*, not whether you actually re-typeset; ⑥'s `--check-proofreading` returns 100+ FAILs where most are known false positives that can hide a real defect. A role-③/⑤ pass that does **nothing** can still return a clean lint. Therefore the executor MUST hand-verify the role's actual deliverable (see each role's "Anti-shortcut clause" in `.opencode/agents/*.md` and `references/refinement-agent-chain.md`) — do NOT treat a green lint as proof the role is complete (F4). <!-- evolved 2026-06-30 — rework #2: a prior run passed every `--only` lint and self-declared all 8 roles done, yet ③ had left ~90 fused formulas un-split and ⑤ had done zero retypesetting. The lints cannot see these; only the executor can. -->

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

<!-- evolved 2026-06-30 — rework: orchestrator ran md-cleaner on an already-generated
     source-transcript.md, wasting a pass; md-cleaner is for raw OCR input only. -->
**Input boundary — md-cleaner / Step 1 runs on RAW OCR markdown only.** If `source-transcript.md` already exists, do NOT re-run Step 1 / md-cleaner on it — "cleaning" a generated canonical transcript means re-running the **Step 2.7 refinement chain** (①②③④⑤⑥⑦⑧), not md-cleaner. md-cleaner removes Doc2X noise and standardizes delimiters; once the transcript is canonical, those artifacts are already gone and the work is refinement (question structure, analysis retypesetting, formula commas), which is the chain's job.

Read `references/auto-fix-rules.md` and apply its rules in exact execution order (remove residual symbols → remove noise → normalize delimiters → split formulas → fix spacing → standardize fractions → normalize blanks → fix OCR characters). These are mechanical text transformations — execute without hesitation.

**Critical notes**:
- **Noise removal**: remove ALL Doc2X-internal artifacts (`<!-- doc2x score: N -->`, `<!-- Meanless: ... -->`, `<!-- Media -->`, `<!-- figureText: ... -->`, page-number lines like `N 老唐说题`, chapter headers like `第 N 章 导 数`). Do NOT leave `__________` fill-in-blank artifacts — section separators must be `---`, not `__________`.
- **Fraction standardization**: `\frac` → `\dfrac` for display-level; `\tfrac` for nested/inline. Inline math (`$...$`) prefers `\tfrac` to avoid line-height disruption.
- **Callout syntax check**: every `[!question]`/`[!example]`/`[!note]` must have a `> ` prefix. Bare `[!question]` without `>` is a syntax error.

### Step 1-GATE — Auto-Fix Stop-Gate (MANDATORY)

Before proceeding to Step 2, run the **7 mandatory verification checks** in `references/auto-fix-gate.md`. If ANY check fails, fix before continuing. This gate runs again after Step 2.7 assembly — formula integrity (`$` count, `\begin{array}` count, callout count) must survive every rewrite pass.

### Step 1.5 — Build Source Skeleton (the first refinement-chain role)

Read `references/refinement-agent-chain.md` (role ★) before acting. This step establishes the `source-transcript.md` **skeleton** — the correct `#`/`##`/`###` heading hierarchy (from `doc2x/outline.md` when `has_outline: true`, else by semantic judgment) and question-block boundaries — so every later refinement role operates on a structurally stable base. This is the layer that was missing before (the old pipeline edited raw directly and let heading-level alignment drift).

**Executor**: by default the main agent does this itself, reading role ★'s logic from `refinement-agent-chain.md`; dispatch `source-skeleton-builder` only if the user explicitly asked for subagents.

**Self-check** after the skeleton is written: `py -3 scripts/validate_canonical_markdown.py --md <file> --only "lint_headings_and_print_noise,lint_numeric_outline_labels"`. Fix FAILs in place, retry ≤3, then proceed to Step 2.

### Step 2 — Proofread (Quality Verification)

Read `references/proofreading-checklist.md` and compare the auto-fixed transcript against source page images page by page. Use the Step 0-A images (`pdf-pages/page-*.png`) if extracted, else whatever the user provided.

**Paragraph splitting rule** (carried into Steps 2.5 and 2.7): analysis paragraphs must be split at logical break points; each paragraph should be ≤ ~300 characters (formulas excluded). Split at punctuation（句号、分号、冒号）, new formula expressions, logic transitions（故/所以/因此/又因为/此时）, and method boundaries（法一/法二/法三）.

**Key checks**: (1) per-page image comparison; (2) Chinese/English typos (易知 not 易如, 必须有 not 必需有, 根据 not 根); (3) structure integrity; (4) cross-page integrity; (5) `[TO VERIFY]` marker management; (6) paragraph length ≤ 300 chars; (7) **Math-sense consistency** (added 2026-06-29): OCR can produce formula chains that are *transcription-faithful but mathematically impossible* — e.g. `i^{10+10+1}`, `(i²)^{505} = -2^{1010}`, `cos θ + sin θ` (dropped `i`). Do **not** blindly trust the raw transcript for *math correctness* — it is authoritative for *characters*, not for *math*. Scan each chain: does it hold? If impossible AND recoverable from context, fix and note it; if unrecoverable, mark `[TO VERIFY: 公式 OCR 损坏，数理不自洽]`. This is the *active* counterpart to F4's reactive byte-level check.

### Step 2-Dispatch — Declare Executor + Which Roles Run (MANDATORY)

<!-- evolved 2026-06-30 — strengthened: the chain now splits Step 2.7 into 8 single-responsibility roles; the dispatch decision now also covers (a) who executes (main agent default vs subagent opt-in) and (b) which roles each dispatched subagent runs. The 2026-06-29 anti-pattern (subagent ran only 2.5, skipped 2.7) is now prevented by naming the roles explicitly. -->

The refinement chain (`references/refinement-agent-chain.md`) runs as a fixed sequence of single-responsibility roles. Two decisions apply to every run:

**Decision 1 — who executes (default: main agent; opt-in: subagent).** By default the main agent runs every role itself, reading each role's logic from `refinement-agent-chain.md` and running that role's `--only` self-check inline. Dispatch to `.opencode/agents/*.md` happens **only when the user explicitly asks** (e.g. "用子代理 / dispatch agents / parallelize"). Do NOT auto-dispatch by document size — the choice is the user's.

**Decision 2 — which roles each executor runs.** The chain's 8 refinement roles (①source-merger → ④subparts → ②options-table → ⑤analysis-retypesetter → ③comma-splitter → ⑥typo → ⑦displacement → ⑧key-point) cover question-block structure + analysis. Verify the document needs each before running it:

| document shape | roles to run |
|---|---|
| has 例题/练习/Q&A blocks (most common) | **all 8** (①②④⑥⑦⑧ for question blocks + ⑤ for analysis + ③ for formulas) |
| has analysis/解析 but NO question blocks | ⑤ (analysis) + ③ (formulas) only |
| has question blocks but analysis already clean | ①②④⑥⑦⑧ + ③ (skip ⑤) |

**Anti-pattern (the 2026-06-29 failure, restated for the chain)**: an executor told vaguely "clean the markdown" runs only the cheap roles (e.g. ⑤ analysis splitting) and silently skips the question-block roles (①②④), leaving structure broken. The fix is forcing the executor to **name the roles**. When dispatching, the prompt MUST state the exact role list (e.g. "Run roles ①②④⑥⑦⑧ + ③"), and the post-return self-check (item: "all named roles ran?") confirms it. If the document has question blocks and the question-block roles did not run, that is a defect — re-run them.

### Step 2.5 — Analysis Block Re-typesetting (refinement-chain role ⑤)

**MANDATORY for documents with analysis/solution sections (解析/解/证明).** This is refinement-chain role ⑤ (`references/refinement-agent-chain.md`), and ⑤ is the **SOLE owner of analysis paragraphs** — no other role splits or reflows analysis (the old redundancy with `question-block-rewriter` is removed). Doc2X dumps each analysis section as one massive unbroken paragraph; ⑤ re-typesets each block into clean ≤300-char paragraphs and fixes OCR typos inside the analysis.

**Scope**: mechanical paragraph *splitting* inside a single analysis block only (排版). Question-block structure is handled by roles ①②④ — do not let them overlap.

**Full rules and verification commands**: read `references/analysis-retypesetting.md`. **Executor**: by default the main agent runs ⑤ itself; dispatch the `analysis-retypesetter` agent only if the user explicitly asked for subagents. **Self-check**: `--only "lint_markdown_analysis_paragraphs,lint_analysis"` (path-independent contract).

### Step 2.7 — Refinement Chain (MANDATORY for question-heavy documents)

<!-- evolved 2026-06-30 — rework: the old single-agent question-block-rewriter bundled 4 jobs and weaker models skipped/collided them. Split into 8 single-responsibility roles (chain), each with its own --only self-check. Main agent is the default executor; subagents are opt-in (user must ask). -->

**MANDATORY for documents containing 例题/练习/Q&A blocks.** Runs after Step 1.5 (skeleton), before Step 3. OCR produces structurally messy question blocks; the refinement chain fixes them one role at a time, each role with a single responsibility and a path-independent `--only` self-check that catches its own defects before the next role starts. This split replaced the old monolithic `question-block-rewriter` (which bundled title/options/subparts/analysis into one agent and was unreliable on weaker models).

**Read `references/refinement-agent-chain.md` before acting** — it is the single source for the 8 roles' logic, the role→lint map, the IRON LAW, and the path-independent self-check contract. The chain order:

```
① question-source-merger     (title line = label + source only)
④ question-subparts-splitter ((1)(2)(3) onto own lines)
② question-options-to-table  (A/B/C/D → table)
⑤ analysis-retypesetter      (analysis paragraphs — SOLE owner; Step 2.5)
③ math-comma-splitter        (split commas out of $...$)
⑥ ocr-typo-fixer             (己/已/巳, 人/入, 末/未, i↔1)
⑦ sentence-displacement-fixer(return stem-tail/analysis-opener to place)
⑧ key-point-marker           (≤2 marks/block, palette, pure-text spans)
```

**Executor**: by default the main agent runs each role itself, reading the role's logic from `refinement-agent-chain.md` and running that role's `--only` lint right after (fix FAILs in place, retry ≤3, mark `[TO VERIFY]` if still failing). Dispatch to `.opencode/agents/*.md` (①②③④⑥⑦⑧ each have a matching agent file; ⑤ uses `analysis-retypesetter`) **only when the user explicitly asks for subagents**.

**Do NOT refine**: pure knowledge-point narrative, section intros, summary tables without questions (OCR handles those well enough).

**Fallback**: the legacy `question-block-rewriter` agent (single-agent, all jobs bundled) is retained in `references/question-block-rewrite-guide.md` for when OpenCode subagents are requested but the fine-grained chain is unavailable, or for a tiny document where the user wants the fast single-agent path. It is NOT the default.

### Step 2.8 — Math-Sense Cross-Review Subagent (MANDATORY for formula-heavy docs, added 2026-06-29)

<!-- evolved 2026-06-29 — recurrence (root cause C): the rewriter trusted raw OCR for *math correctness*, not just characters. "③ 频率 = 样本容量" survived because the raw transcript itself was OCR-garbled and no one re-derived it. A validator cannot judge math truth; a second model reading the formulas with fresh eyes can. This is the multi-agent cross-examination defense the user requested. -->

Code validators (Step 4) catch *structural* defects (truncated formulas, wrong delimiters) but **cannot judge math truth** — whether `频率 = 样本容量` is a valid identity, whether a sign/exponent makes the equation balance, whether a derived value follows from the given data. The 2026-06-29 `③频率=样本容量` defect (raw OCR dropped "频数/") survived all structural lints because the structure was clean; only re-deriving the math caught it.

**For formula-heavy documents** (statistics, probability, calculus, complex numbers — any chapter with computation), after Steps 2.5/2.7, dispatch a **separate cross-review subagent** whose ONLY job is math-sense verification — it does NOT rewrite structure, it audits each formula chain for mathematical self-consistency:

- **Re-derive, don't eyeball**: for each result/answer, walk the computation from the given data and confirm the printed value is what the formula produces (e.g. `12 × 25% = 3`, `s² = (1/n)Σ(xᵢ−x̄)² = 0.036`). If the printed result ≠ the derived result, that is a defect.
- **Identity check**: does each stated equality hold? `频率 = 样本容量` fails (频率 = 频数/样本容量); `样本容量 = 频数/频率` holds. Flag identities that are mathematically false even if OCR-faithful.
- **Sign/exponent/unit sanity**: a variance is non-negative; a probability is in [0,1]; a percentage × count gives a count. Impossible values signal OCR or derivation error.
- **Cross-reference against `doc2x/page-transcript.raw.md`**: when a formula is mathematically impossible, check whether the raw OCR is itself garbled (the `③` case: raw said `频率 = 样本容量`, which is OCR-wrong). If raw is wrong, re-derive the correct form from context (the `①` rule `面积=组距×频率/组距=频率` implies `样本容量=频数/频率`); if unrecoverable, mark `[TO VERIFY: raw OCR 数理不自洽，未能恢复]`.
- **Report**: list each audited chain, its derived-vs-printed status, and any fix applied. Flag unrecoverable cases for human review.

This is independent from the Step 2 math-sense check (which the rewriter does inline) — a fresh subagent is not anchored to the rewriter's assumptions and catches what the rewriter rationalized past. The cross-review runs BEFORE Step 3 so structural formatting is applied to already-correct math.

### Step 3 — Structural Format (Canonical Markdown)

Read `references/canonical-markdown-rules.md` and apply it to the proofread transcript.

**Parser choice**: for formula-heavy math content, use **plain Markdown** for analysis (`**解析**`/`**解**` with paragraph breaks), NOT `<div class="analysis-block">` HTML (which requires MathML for all formulas — impractical). Use the HTML form only for zero-formula pure-text analysis.

<!-- evolved 2026-06-30 — rework: user reported HTML <table> cells with $...$ render as
     raw text; Markdown processors pass HTML blocks through without scanning $ for KaTeX. -->
**HTML blocks (`<table>`, `<div>`) do NOT render `$...$`** — the Markdown processor passes HTML through verbatim, never scanning `$` for KaTeX. This generalizes the `<div class="analysis-block">` rule above to ALL HTML blocks (tables especially). If an HTML block contains formulas, either (a) **convert it to a Markdown table** (`| ... |`) so `$...$` renders (preferred — consistent with the rest of the document), or (b) hand-write the formulas as **MathML** (`<math>...</math>` — KaTeX's `ignoredTags` includes `math`, so the browser renders it natively; but `mathvariant` browser support is uneven, so prefer option (a) unless the table's styling is load-bearing). Doc2X often emits definition/property tables as HTML `<table>` with plain-text math inside `<td>` — these are the prime candidates for conversion.

**Long formulas**: display formulas > one line use `\begin{aligned}` with `\\` breaks, split at `=`/`+`/`-`/logical boundaries. **Whether an inline `$...$` chain is "too long" is judged by RENDERED WIDTH, not source characters** — see `references/canonical-markdown-rules.md` (Formulas → "long multi-equality chain") for the three-band classifier (short ≤464px keep inline / long >625px convert to aligned / medium 464–625px judge in context; A4 text ≈695px).

<!-- evolved 2026-07-01 — the three-band rule + measure tool now live in canonical-markdown-rules.md
     (single source); SKILL.md keeps only the pointer + the one command. -->
When `lint_long_inline_formula` (Step 4, coarse signal — estimates width by macro folding, over-flags verbose-but-short formulas like the sin β chain: 275 source chars, ~360px render) flags a formula, **measure the true width** before converting:

```
py -3 scripts/measure_inline_formula_width.py --md <file> --band medium,long --dedup
```

This is a standalone tool (plain KaTeX print + headless Chromium, ~1s) — NOT wired into the per-role `--only` self-check; call it once when the coarse lint flags something. Do NOT blindly convert every lint FLAG to aligned.

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

**Known limitations**: `fix_callout_prefixes.py` may wrongly prefix `##`/`###` lines — verify headings after.

**`--fix` vs frontmatter — do not learn this the hard way** (evolved 2026-06-30, recurred 3× in one 概率 job): `validate_canonical_markdown.py --fix` applies Rule 5 (`---` → `__________`) indiscriminately — **including the frontmatter `---` fences**, not just section separators. Corrupted frontmatter is silent: `parse_frontmatter()` returns `{}`, so `pagination-level`/`cover` intent vanishes and downstream pagination breaks with no error message. Therefore:
- If `source-transcript.md` has frontmatter, **do not run `--fix` on it blindly.** Either (a) strip the frontmatter block, run `--fix`, then restore the frontmatter; or (b) run `--fix`, then immediately re-assert both fences are still `---` (not `__________`) and re-parse with `parse_frontmatter()` to confirm the metadata dict is non-empty.
- After any `--fix` run on a frontmatter-bearing file, the first 5 lines MUST still parse as frontmatter. Re-fix the fences before declaring the file clean. This is a verification step, not optional.

<!-- evolved 2026-06-30 — rework: Rule 5 also corrupts Markdown TABLE separator rows
     (| :---: | → | :__________: |), not just frontmatter; lint_tables is silent on this. -->
**Rule 5 also corrupts Markdown table separator rows** (`| :---: |` → `| :__________: |`), not just frontmatter fences. After any `--fix` run, also grep for underscore-corrupted separators (`rg '^>?\s*\|.*_{5,}'`) and restore them to `---`. `lint_tables` does NOT catch underscore separators (it checks column count / option integrity, not the separator characters) — you MUST verify by eye. Two such corruptions were found in one 立体几何 job (one inside a callout `> | :__________: |`).

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
