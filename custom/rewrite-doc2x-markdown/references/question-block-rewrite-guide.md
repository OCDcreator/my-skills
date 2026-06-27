# Question Block Rewrite Guide

Detailed rules and subagent instructions for **Step 2.7 — Question Block Rewrite** of the main workflow. Loaded when the document contains examples/exercises/Q&A blocks (例题/练习/题).

This guide and `analysis-retypesetting.md` have **separate responsibilities**:

- `analysis-retypesetting.md` → mechanical paragraph splitting inside a single analysis block (排版 only)
- this guide → the **whole question-block structure** (题干 → callout, 选项 → table, 子问 → own lines, 解析 → paragraphs), rewritten against the raw transcript

## Why Rewrite Instead of Audit

OCR produces structurally messy question blocks: stems dumped as plain paragraphs, options scattered outside the question, sub-parts crammed on one line, analysis as one giant lump, or sentences displaced between stem and analysis. "Auditing" (finding problems then fixing) is unreliable — it depends on the model noticing problems it often misses. **Rewriting is reliable**: the subagent rewrites each question block cleanly against the raw transcript, and the rewrite itself fixes every structural defect without needing to detect them first.

## Rewrite Scope

Rewrite **only question blocks**: each `例题N` / `练习N` / `例` / Q&A unit, as a complete structure:

- the question stem (题干)
- all choice options (A. B. C. D. / 甲乙丙丁) or fill-in parts
- sub-questions `(1) (2) (3)`
- the analysis/solution/proof (解析/解/证明) that belongs to that question

**Do NOT rewrite**: pure knowledge-point narrative (知识点叙述), section intros, summary tables without questions. OCR handles those well enough; rewriting them wastes tokens and risks introducing errors.

## Reference Authority (HARD REQUIREMENT)

When rewriting a question block, the subagent MUST read the corresponding passage in `doc2x/page-transcript.raw.md` (the per-page Doc2X OCR result) and treat it as the **content truth**. Rewrite the structure against it — do not infer content from the existing `source-transcript.md` text alone, do not invent, do not summarize.

`page-transcript.raw.md` is assembled per-page from Doc2X OCR, so it is already a "page-level OCR markdown" — use it directly without re-running OCR.

## Rewrite Format (per `canonical-markdown-rules.md`)

- **Document headings (`#`/`##`/`###`) are preserved verbatim — do NOT rewrite or drop them** (CRITICAL for weaker models). The rewrite touches only question-block STRUCTURE; the document's section title hierarchy (`# 文档标题` / `## 第一节` / `### 经典例题`) is NOT a "question block" and must pass through untouched. Weaker models tend to frame "rewrite the question blocks" as "output ONLY the question blocks", silently dropping every heading. Guard against this with a **literal-echo step** (see Step 0 in the Subagent Template below): before rewriting, scan the document for every `#`-prefixed line and copy each one verbatim into the output at its original position/level. Even a heading that looks "unimportant" must be kept. The output is a FULL rewrite of the document, from its first `#` heading to its end, not a extract of the question blocks. <!-- added 2026-06-28 stress-test lesson: weak models drop headings unless given an explicit copy step -->
- **Title line holds only the label + source** (CRITICAL — most common OCR defect). The `[!question]` title line carries only the `例题N`/`例N`/`练习N` label and its optional source tag (`(2017・新课标 I)`/`【2018全国I】`/year digits/nothing). The stem body (the actual problem — 已知…/设…/若…/求…) MUST begin on the next `>` line. OCR routinely glues the stem's first sentence onto the title line; during rewrite, split it off. The title line must never be both the "题号" and the "题干第一句". Source tags vary across PDFs (round/angle/【】 brackets, year digits, exam names, or none) — judge by the stem, not the source shape. See `canonical-markdown-rules.md` → "Title line holds only the label + source" for good/bad examples. (Enforced by `lint_question_callout_title_attached`.)
- **Stem** → a single `> [!question]` callout containing the stem, options, and sub-questions together.
- **Choice options** → markdown table inside the callout (`≤15` chars/option: one row × 4 cols; `>15` chars: two rows × 2 cols). Every table line prefixed with `>`.
- **Sub-questions** `(1) (2) (3)` → each on its own `>` line, separated by a blank `>` spacer line. Never cram multiple `(N)` onto one line.
- **Analysis** → outside the callout, `**解析**` / `**解**` in bold, with a blank line between the callout end and `**解析**`. Split into logical paragraphs (`≤300` chars each, formula content excluded).
- **Formulas** → `$...$` inline, `$$...$$` display on standalone lines. Preserve every LaTeX construct from the raw transcript verbatim; never convert `\begin{array}` ↔ `\begin{cases}`.

## Key-Point Marking (during rewrite)

While rewriting a question block against the raw transcript, the subagent may **sparingly** mark key points to guide the reader's attention. Full rules live in `emphasis-and-color-rules.md`; the essentials:

**What to mark (pick at most 1-2 per block — over-marking defeats emphasis):**
- **Conclusion sentence** → purple `#9370DB`: `<span style="color: #9370DB;">因此答案为 A</span>`
- **易错 / pitfall note** → red: `<span style="color: red;">注意此处易漏掉隐含条件</span>`
- **Technique / 口诀 name** → green: `<span style="color: green;">分离参数法</span>`

**What NOT to mark:** derivation steps, intermediate results, routine definitions, every word OCR bolded. When in doubt, do not mark.

**Formula conflict (critical):** color spans wrap **pure text only** — never `$...$`. If the text you want to emphasize contains a formula, use bold/italic, or split and wrap only the prose parts:
- Wrong: `<span style="color: #9370DB;">因此 $f(x)$ 取极小值</span>`
- Right: `**因此 $f(x)$ 取极小值**` (bold) or `<span style="color: #9370DB;">因此</span> $f(x)$ <span style="color: #9370DB;">取极小值</span>` (split)

**Mis-marked headings:** if a line in the block was turned into a `#`/`##` heading by OCR but is really emphasis (e.g. a boxed "★ 易错点" or "口诀"), downgrade it to inline emphasis per the palette — do not delete it.

## Rewrite vs Do-Not-Touch Boundary

Permitted during rewrite (these fix OCR structural damage):

- Split analysis into logical paragraphs at punctuation / method boundaries / logic transitions / new-formula points
- Move a displaced sentence back to where it belongs (stem tail sentence that OCR shoved into the analysis; analysis opener stranded in the stem)
- Fix OCR typos (己/已/巳, 人/入, 末/未, …)
- Adjust formatting (callout wrapping, option table layout, sub-question line breaks)
- Split a fused formula, move punctuation outside `$`

Forbidden (these corrupt content):

- Delete any derivation step (法一/法二/法三 must all be preserved in full)
- Add content not present in the raw transcript
- Change formula LaTeX structure or convert constructs
- Summarize or condense the analysis

## Single-Page Re-OCR Appeal (when the subagent doubts the raw transcript)

If the subagent reads a passage in `page-transcript.raw.md` and **genuinely doubts** its content (a formula looks wrong, a number seems garbled, a sentence is broken in a way that suggests an OCR error rather than a structural one), it may request a **single-page re-OCR** as a second opinion. This is the only escape hatch from "raw is the truth".

**Hard constraints on the appeal:**

1. **One page only.** The appeal is for the single page the doubtful content sits on — never a range, never "the surrounding pages too". Re-OCR-ing multiple pages to resolve one doubt wastes quota and is forbidden.
2. **Extract that one page into a sub-PDF first, then submit only it:**
   ```bash
   py -3 scripts/extract_and_submit.py \
       --pdf "doc2x/source-pages.pdf" \
       --pages "<N>" \
       --output-dir "<job>/doc2x/appeal-page-<N>" \
       --allow-full-pdf
   ```
   Then submit `appeal-page-<N>/doc2x/source-pages.pdf` to Doc2X (`doc2x_parse_pdf_submit` → `doc2x_parse_pdf_wait_text`, or `doc2x_parse_pdf_submit` → export). Note: `source-pages.pdf` is already the sub-PDF, so `<N>` here is the **1-based page within the sub-PDF**, not the source book page.
3. **Compare the new OCR result against the raw transcript.** If the new result clarifies the doubt, use it as the corrected reference for that passage.
4. **Give up after one retry.** If the single-page re-OCR still does not resolve the doubt (the result is equally unclear, or disagrees in a way you cannot adjudicate), **stop** — do not re-OCR again, do not escalate to neighboring pages. The most likely cause is that the PDF itself is unclear, which no amount of OCR will fix. Mark the spot `[TO VERIFY: 单页重 OCR 仍不清晰，疑 PDF 原文模糊]` and move on.

**The appeal is for content doubt, not for structure.** Structural messiness (stem not in callout, options scattered, analysis as one lump) is fixed by rewriting — never by re-OCR. Re-OCR is only for "I think the OCR misread a symbol/number/word here".

## Subagent Self-Check (after rewriting each block)

Before reporting a rewritten block as done, verify:

- **All document headings preserved**: every `#`/`##`/`###` heading from the original document is still present in the output, at its original level. No section title was dropped or merged. (The most common failure for weaker models.)
- **Title line is label-only**: the `[!question]` title line contains only the `例题N`/`例N`/`练习N` label and its source tag — the stem body starts on the next `>` line. No stem sentence glued onto the title line.
- **Option count matches raw**: the number of choice options in the rewritten callout equals the number in the raw transcript passage (no option dropped or invented).
- **`$` conservation**: count of `$` in the rewritten block equals count in the raw passage (no delimiter added/lost).
- **No analysis paragraph > 300 chars** (formula content excluded).
- **Callout closed**: the `> [!question]` block ends with a blank line (no `>`) before `**解析**`; `**解析**` is NOT inside the callout.
- **No content added/removed**: every derivation step in the raw passage is present; nothing new was invented.
- **Constructs preserved**: `\begin{array}` / `\begin{cases}` counts unchanged vs raw; no unauthorized conversions.

## Subagent Instructions Template

For each chunk of 3-5 question blocks, dispatch a subagent with this prompt:

```
You are rewriting question blocks (例题/练习/Q&A) in a math transcript. For each
question block in your assigned range:

0. PRESERVE DOCUMENT HEADINGS (do this FIRST, before any rewrite). Scan the
   document for EVERY line that starts with `#`/`##`/`###`. Write each one
   down verbatim. When you produce your output, copy these heading lines into
   their original positions and levels, unchanged — even ones that look
   "unimportant". Your output is a FULL rewrite of the document (from its
   first `#` heading to its end), NOT an extract of just the question blocks.
   Weaker models routinely drop section titles here; the explicit copy step
   is what prevents that.
1. READ the block's current state in source-transcript.md.
2. READ the corresponding passage in doc2x/page-transcript.raw.md (locate it by
   page marker / position). The raw transcript is your CONTENT TRUTH.
3. REWRITE the block cleanly against the raw, following these rules:
   - TITLE LINE: the > [!question] line holds ONLY the 例题N/例N/练习N label
     and its source tag (e.g. (2017・新课标 I), 【2018全国I】, year, or none).
     The stem body (已知…/设…/若…/求…) MUST start on the NEXT > line. OCR
     often glues the stem's first sentence onto the title line — SPLIT IT OFF.
   - Stem + options + sub-questions → one > [!question] callout
   - Options → markdown table inside the callout (≤15 chars: 1 row × 4 cols;
     >15 chars: 2 rows × 2 cols); every line prefixed with >
   - Sub-questions (1)(2)(3) → each on its own > line, blank > spacer between
   - Analysis → outside callout, **解析** bold, blank line before it; split into
     logical paragraphs ≤300 chars each (formulas excluded)
   - Preserve every LaTeX construct verbatim; never convert begin{array}↔cases
4. FIX OCR typos (己/已/巳, 人/入, 末/未) by comparing to the raw passage.
5. MOVE displaced sentences back where they belong (stem tail shoved into
   analysis; analysis opener stranded in stem).
6. SPARINGLY MARK key points (≤2 per block): conclusion sentence → purple
   #9370DB, 易错/pitfall → red, technique/口诀 name → green. Color spans wrap
   PURE TEXT only, never $...$ (use bold for formula-containing text). See
   emphasis-and-color-rules.md. Downgrade mis-marked headings to emphasis.
7. DO NOT: delete derivation steps, add content, summarize, or change formula
   structure. You are rewriting STRUCTURE, not content.
8. IF you genuinely doubt a symbol/number/word in the raw passage: you may
   request a SINGLE-PAGE re-OCR of that one page only
   (extract_and_submit.py --pages <N> --allow-full-pdf → doc2x_parse_pdf_submit).
   Compare the new result; if it clarifies the doubt, use it. If it does NOT
   resolve the doubt after one retry, STOP — mark [TO VERIFY: 单页重 OCR 仍不清晰]
   and move on. Do NOT re-OCR again, do NOT expand to neighboring pages.
9. SELF-CHECK each rewritten block: ALL document headings (#/##/###) preserved
   verbatim, title line is label+source only (no stem glued on), option count
   matches raw, $ count matches raw, no analysis paragraph >300 chars, callout
   closed, no content added.

REPORT:
- Number of question blocks rewritten
- Any single-page re-OCR appeals made (page number, whether resolved)
- Any [TO VERIFY] markers left and why
- $ count before/after for your range (must match)
```

## Post-Assembly Verification

After subagents finish and the main agent reassembles:

1. Run the existing Step 1-GATE checks (fused formulas, `\$` corruption, `\begin{array}` count, callout count) — the rewrite must not have damaged formula integrity.
2. Run Step 4 validator (`validate_canonical_markdown.py --fix`).
3. Spot-check 2-3 rewritten blocks against their raw passages to confirm structure was cleaned and content preserved.
4. Confirm no `[TO VERIFY: 单页重 OCR 仍不清晰]` markers indicate a systemic clarity problem (if many appear, the PDF source quality itself is the issue — report to the user rather than looping).
