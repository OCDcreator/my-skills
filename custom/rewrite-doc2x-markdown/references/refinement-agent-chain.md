# Refinement Agent Chain (职责链)

This is the **single source of truth** for how the Doc2X-cleaned raw markdown is refined into the final `source-transcript.md`. Every refinement step is defined here once. **Two execution paths consume this same definition**:

- **DEFAULT — main agent (orchestrator) does it itself.** The main agent reads each role's logic below and executes it inline, running that role's self-check `--only` lint right after. This is the default; no subagent is spawned.
- **OPT-IN — subagent dispatch.** Only when the user *explicitly* asks to use subagents (e.g. "用子代理 / dispatch agents / parallelize"), the main agent dispatches the matching `.opencode/agents/*.md` file, which embeds the *same* logic and the *same* self-check. The choice is the **user's**, never the skill's.

Both paths run the **identical self-check** after each role, so a subagent return and a main-agent pass are equally trustworthy (path-independent verification).

> Why a chain instead of one monolithic rewriter? The old `question-block-rewriter` bundled 4 jobs (title line, options-to-table, sub-question splitting, analysis paragraphs) into one agent. On weaker models that bundle was too much — jobs collided and got skipped. Splitting into single-responsibility roles, each with its own `--only` self-check, makes each task simple enough to do reliably and lets the self-check pin failures to the exact role that caused them.

## The chain

After `md-cleaner` (Step 1) has produced clean raw markdown, the refinement chain runs in this **fixed order**. Each role edits the file **in place** and runs its self-check before the next role starts.

```
clean raw markdown
      │
      ├─ ★ source-skeleton-builder   (骨架: establish heading levels + block boundaries)
      ├─ ① question-source-merger    (标题行: title line = label + source only)
      ├─ ④ question-subparts-splitter(子问题: (1)(2)(3) onto own lines)
      ├─ ② question-options-to-table (选项: A/B/C/D → table)
      ├─ ⑤ analysis-retypesetter     (解析: ≤300-char paragraphs — SOLE owner of analysis)
      ├─ ③ math-comma-splitter       (公式: split enumerated/fused commas out of $...$)
      ├─ ⑥ ocr-typo-fixer            (错字: 已/己/巳, 人/入, 末/未, i(虚)↔1)
      ├─ ⑦ sentence-displacement-fixer (错位句: return stem-tail/analysis-opener to place)
      └─ ⑧ key-point-marker          (着色: ≤2 marks/block, palette, pure-text spans)
      │
      ▼
final source-transcript.md  (main agent then runs full validator + self-check)
```

### Why this order

- **Skeleton first (★)** establishes the heading hierarchy + question-block boundaries, so every later role operates on a structurally stable document — no role has to re-derive heading levels (the old drift problem).
- **Structure roles (①④②)** fix the callout *skeleton* (title line, sub-questions, options) before any content-level work, because later roles' self-check lints assume a well-formed callout.
- **⑤ retypesetter** owns analysis paragraphs exclusively; running it after ② means option tables are already stable and won't shift analysis positions.
- **③ comma-splitter** runs after structure is fixed because it re-balances `$` delimiters; doing it earlier risks being undone by structural edits.
- **Semantic roles (⑥⑦)** need the document structurally clean to compare against raw and locate displaced sentences.
- **⑧ key-point-marker** runs last so its color spans are applied to already-final text and never accidentally moved/merged by an earlier role.

## Universal IRON LAW (every role)

- ❌ NEVER delete, summarize, or invent content. Every derivation step (法一/法二/法三) survives in full.
- ❌ NEVER change a formula's value, sign, exponent, or LaTeX structure. Only delimiters/spacing/layout.
- ❌ NEVER convert `\begin{array}` ↔ `\begin{cases}` or alter `\left\{` / any structural macro (forbidden F3).
- ✅ `doc2x/page-transcript.raw.md` is content truth for *characters*; roles fix *structure/format*, not characters they cannot verify.
- ✅ Preserve EVERY `#`/`##`/`###` heading verbatim — weaker models drop headings; the skeleton role establishes them, later roles must not remove them.

## Path-independent self-check contract

After each role finishes its edit, run that role's `--only` lint (see the role→lint map below). This is the feedback loop that minimizes rework: a defect is caught and fixed *inside* the role before the next role ever sees it.

```bash
py -3 scripts/validate_canonical_markdown.py --md "<file>" --only "<this role's lints>"
```

- If exit code = 0 → role is clean, proceed to the next role.
- If exit code = 1 → read the `FAIL:` lines, fix them in place, re-run the `--only` lint. **Retry up to 3 times.**
- If still failing after 3 retries → mark the spot `[TO VERIFY: <role> self-check 未通过 — <FAIL summary>]` and move on. Do NOT loop forever (forbidden — see SKILL.md "Two lint families" warning). Report the unresolved markers to the main agent.

This contract is identical whether the executor is the main agent or a subagent. A subagent's self-report is NOT proof — the main agent independently re-runs the full validator (Step 4) after the whole chain completes.

## Role → lint map (authoritative)

This is the single mapping used by every `--only` self-check. If a lint name here does not exist, the validator aborts loudly (see `validate_canonical_markdown.py --only` unknown-name guard).

| Role | `--only` lints | Coverage note |
|---|---|---|
| ★ source-skeleton-builder | `lint_headings_and_print_noise,lint_numeric_outline_labels` | catches stray print noise + outline-label leaks |
| ① question-source-merger | `lint_question_callout_title_attached` | direct hit: title-line rule |
| ④ question-subparts-splitter | `lint_bare_question_starts,lint_qa_ordering` | structural, coarse |
| ② question-options-to-table | `lint_choice_options,lint_tables` | direct hit: option/table rules |
| ⑤ analysis-retypesetter | `lint_markdown_analysis_paragraphs,lint_analysis` | paragraph-length + HTML-analysis block |
| ③ math-comma-splitter | `lint_formula_dangling_tail,lint_list_inside_math,lint_long_inline_formula,lint_inline_math_spacing` | the four formula-format lints |
| ⑥ ocr-typo-fixer | `--check-proofreading` (NOT `--only`) | **coarse signal** — runs the dedicated proofreading pass (confusable chars, delimiter balance); char correctness still needs raw comparison. See note below the table. |
| ⑦ sentence-displacement-fixer | `lint_qa_ordering` | **coarse signal** — displacement is semantic |
| ⑧ key-point-marker | *(none — IRON LAW self-check)* | no lint for color rules; rely on the role's own checklist |

**Why ⑥ uses `--check-proofreading`, not `--only lint_proofreading`:** `lint_proofreading` is a dedicated proofreading lint that lives on its own CLI branch (`--check-proofreading`), NOT in the `lint_markdown()` registry that `--only` filters. So `--only lint_proofreading` would error with "unknown lint name". Role ⑥ invokes the proofreading pass directly:
```bash
py -3 scripts/validate_canonical_markdown.py --md "<file>" --check-proofreading
```

**Honest framing for ⑥⑦⑧**: their lints are coarse structural signals, not semantic truth-checkers. The proofreading pass flags *some* confusable chars but cannot confirm a char is *correct*; `lint_qa_ordering` flags mis-ordered analysis but cannot tell a *displaced sentence* from a misplaced one. These roles MUST additionally compare against `page-transcript.raw.md` by hand — the lint is a coarse net, not proof. (Verification Ceiling: a content skill has no runtime; layered defense = lint + raw-comparison + main-agent full-validator + human review.)

## Per-role logic

Each subsection below is the **reusable prompt logic**. The main agent reads it and executes; the matching `.opencode/agents/<name>.md` (when dispatched) embeds the same logic — they must stay in sync. **If you change a role's logic here, the agent file must be updated too** (single source = this file).

### ★ source-skeleton-builder — establish the document skeleton

**Goal**: turn the clean raw markdown into a `source-transcript.md` *skeleton* with the correct `#`/`##`/`###` heading hierarchy and question-block boundaries, so every later role works on a structurally stable base. This is the new layer that was missing before (the old pipeline edited raw directly, letting heading-level alignment drift across roles).

**Inputs**: clean raw markdown + `doc2x/outline.md` (if `extract-manifest.json` reports `"has_outline": true`).

**Steps**:
1. If `outline.md` exists with real entries → treat its indentation depth as **ground truth** for heading levels. Map outline Level 1 → `#`, Level 2 → `##`, etc. (apply the fixed offset from `canonical-markdown-rules.md` → "标题层级参照"). Do not invent levels.
2. If `outline.md` is absent or `has_outline: false` → **fall back to semantic judgment**: read the whole document, understand its structure, and assign `#`/`##`/`###` by meaning (chapter → `#`, section → `##`, sub-section → `###`). This is judgment, not guesswork — a knowledge chapter has a natural hierarchy.
3. Ensure the top title describes the actual document (never `# Source Transcript`).
4. Mark each question block's boundary (`例题N`/`练习N`/`例`) so later roles can locate blocks. Do NOT touch stem text, options, or analysis content — skeleton only.
5. Write/replace `source-transcript.md`.

**Does NOT do**: stem rewording, option tables, sub-question splitting, analysis paragraph splitting, typo fixing, color marking. Those belong to later roles.

**Self-check**: `py -3 scripts/validate_canonical_markdown.py --md "<file>" --only "lint_headings_and_print_noise,lint_numeric_outline_labels"`. Retry ≤3; `FAIL: top title must describe the document` or outline-label leaks must be fixed before ① starts.

### ① question-source-merger — title line = label + source only

**Goal**: every `> [!question]` title line holds ONLY the question label (`例题N`/`例N`/`练习N`) and its optional source tag; the stem body starts on the next `>` line. Also normalize bare-number titles to `例题N` and strip OCR noise (`$λ$ 13` → `例题13`).

**Full transformation rules + examples**: see `.opencode/agents/question-source-merger.md` (the agent file is the canonical spec for this role; this chain references it to avoid duplication). When the main agent executes this role inline, it follows the same rules.

**Does NOT do**: options, sub-questions, analysis.

**Self-check**: `--only "lint_question_callout_title_attached"`. Must be clean before ④.

### ④ question-subparts-splitter — sub-questions on their own lines

**Goal**: inside each `> [!question]` callout, every `(1)`/`(2)`/`(3)` sub-question sits on its own `>` line, separated by a blank `>` spacer. Never cram two `(N)` markers onto one `>` line.

**Steps**:
1. Scan each callout for `(1)(2)(3)` (and ①②③) markers.
2. If two or more share a single `>` line, split them onto separate `>` lines with a blank `>` line between.
3. Do NOT rewrite sub-question text; only reflow line breaks.

**Does NOT do**: title line (①'s job), options (②'s job), analysis (⑤'s job).

**Self-check**: `--only "lint_bare_question_starts,lint_qa_ordering"`. Coarse signal — also eyeball that no `>` line has two `(N)` markers.

### ② question-options-to-table — options become a table

**Goal**: convert A/B/C/D option lists inside each callout into a Markdown table (1×4 short / 2×2 medium / 4×1 long), every line `>`-prefixed, center-aligned.

**Full layout thresholds + examples**: see `.opencode/agents/question-options-to-table.md` (canonical spec).

**Does NOT do**: stem, sub-questions, analysis.

**Self-check**: `--only "lint_choice_options,lint_tables"`. Must be clean before ⑤.

### ⑤ analysis-retypesetter — analysis paragraphs (SOLE owner)

**Goal**: re-typeset each 解析/解/证明 block into logical paragraphs ≤300 chars (formulas excluded), fix OCR typos *inside* analysis, verify formula integrity.

**This role is the SOLE owner of analysis paragraphs.** No other role splits or reflows analysis — that was the old redundancy (question-block-rewriter also touched analysis). The boundary is now clean: ⑤ owns analysis; ①④② own callout structure; they do not overlap.

**Full rules + subagent template**: see `references/analysis-retypesetting.md`.

**Does NOT do**: callout structure, options, color marking.

**Self-check**: `--only "lint_markdown_analysis_paragraphs,lint_analysis"`. Note the known `\mathrm{}` glitch (SKILL.md:204): if `lint_markdown_analysis_paragraphs` reports a long line whose true prose is short, verify by hand; do NOT re-run the role to appease the counter.

### ③ math-comma-splitter — split commas out of formulas

**Goal**: find `，`/`、` wrongly pulled inside `$...$`/`$$...$$` by OCR, split enumerated symbols / fused independent formulas into separate math blocks, while preserving structural commas (intervals, coordinates, function args, arrays, piecewise).

**Full split/keep rules + examples**: see `.opencode/agents/math-comma-splitter.md` (canonical spec). **Read it in full before acting** — it covers three fusion shapes that the self-check lint CANNOT detect: (a) multiple labeled coordinate points crammed in one span (`$A(0,0), B(3,-2), C(5,1)$` — each point is independent, split; the comma *inside* `(x,y)` stays), (b) multiple independent equations fused by a comma (`$|AC|=\sqrt{26}, |BD|=\sqrt{26}$`), (c) multiple independent variables (`$A, B, C$`, `$k, l_1$`). <!-- evolved 2026-06-30 — lint_list_inside_math only matches interval-list patterns [a,b), [c,d); it is SILENT on point/equation/variable enumerations. A role-③ pass that splits nothing can still return a clean self-check. The executor must hand-scan for these three shapes; do NOT treat a clean lint as proof the role is done (F4). -->

**Does NOT do**: structure, typos, color. Only formula delimiter hygiene.

**Self-check**: `--only "lint_formula_dangling_tail,lint_list_inside_math,lint_long_inline_formula,lint_inline_math_spacing"`. `$` count must stay balanced before/after. **Ceiling note**: this lint is a coarse net — it will not flag the point/equation/variable fusion shapes above even when they are un-split, so a passing self-check does NOT prove the role is complete. Hand-verify the three shapes against the document.

### ⑥ ocr-typo-fixer — fix confusable characters

**Goal**: compare against `page-transcript.raw.md` and fix confusable characters: `己/已/巳`, `人/入`, `末/未`, `千/干`, `土/士`, and the high-risk **i(虚数单位)↔1** confusion in complex-number docs. Normalize Chinese punctuation `。，；：` vs English `.,;:` in prose (not inside math).

**Method**: read the raw passage at each location, confirm the correct char, edit in place. Do NOT change formula content; only prose characters.

**Does NOT do**: structure, formula splitting, color.

**Self-check**: run the dedicated proofreading pass (NOT `--only` — see the note under the role→lint map): `py -3 scripts/validate_canonical_markdown.py --md "<file>" --check-proofreading` — **coarse**. It flags *some* confusables but cannot confirm correctness; hand-compare against raw. Retry ≤3; remaining doubts → `[TO VERIFY: ⑥ 错字未确认]`.

### ⑦ sentence-displacement-fixer — return displaced sentences

**Goal**: OCR sometimes shoves a stem's tail sentence into the analysis, or strands an analysis opener in the stem. Read each block against raw and move misplaced sentences back where they belong.

**Method**: for each question block, check (a) does the stem end abruptly with a sentence that continues in the analysis? (b) does the analysis open with a phrase that belongs to the stem? Move the sentence; do NOT rewrite it.

**Does NOT do**: typos (⑥), structure, color. Only sentence relocation.

**Self-check**: `--only "lint_qa_ordering"` — **coarse**. Displacement is semantic; the lint only catches gross analysis-position errors. Hand-verify against raw.

### ⑧ key-point-marker — sparing semantic color

**Goal**: mark at most 1-2 key points per question block to guide the reader.

**Palette** (fixed — see `references/emphasis-and-color-rules.md`):
- **Conclusion sentence** → purple `#9370DB`
- **易错 / pitfall** → red
- **Technique / 口诀 name** → green
- **Remark / 备注** → blue

**Rules**:
- Color spans wrap **pure text only** — never `$...$`. If the marked text contains a formula, use bold/italic or split the span around the formula.
- Downgrade OCR-mis-marked headings (a boxed "★ 易错点" turned into `##`) to inline emphasis — do NOT delete.
- Over-marking defeats emphasis; when in doubt, do not mark.

**Does NOT do**: structure, typos, formula splitting.

**Self-check**: no lint for color rules. Rely on the IRON LAW checklist: every span wraps pure text? ≤2 marks per block? palette consistent? Verify `rg -n '<span[^>]*color[^>]*>[^<]*\$' source-transcript.md` returns nothing (no color wrapping `$`).

## After the chain — main agent full validation

Once all 9 roles are done (by whichever path), the main agent runs the **full** validator (no `--only`):

```bash
py -3 scripts/validate_canonical_markdown.py --md "<file>" --fix
py -3 scripts/fix_callout_prefixes.py --md "<file>" --fix
py -3 scripts/validate_canonical_markdown.py --md "<file>" --check-proofreading
```

Then Step 4/5/6/7 of SKILL.md as normal. The per-role `--only` self-checks minimize what reaches here, but the full validator is the final cross-cutting gate.

## Fallback: the old `question-block-rewriter`

The bundled `question-block-rewriter` agent (one agent doing title+options+subparts+analysis) is retained as a **fallback**. Use it ONLY when:
- OpenCode subagents are requested AND the fine-grained chain is unavailable (e.g. a role's `.md` file is missing), OR
- the user explicitly asks for the single-agent fast path on a tiny document.

Its full rules live in `references/question-block-rewrite-guide.md`. It is NOT the default refinement path anymore; the chain above is.
