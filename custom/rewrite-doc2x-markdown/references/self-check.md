# Step 6 — Self-Check (LESSONS LEARNED CHECKLIST)

Before reporting, run through this checklist. **For every command-based check, paste the actual command output into your report** — do not just tick the box. Claims without evidence are treated as failures.

## Evidence-based checks (run command, paste output)

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

## Judgment-based checks (verify, mark pass/fail)

You MUST check all items below. Do not skip any. If an item is not applicable, write "N/A — [reason]" instead of omitting it.

- [ ] **Callout syntax**: every `[!question]`, `[!example]`, `[!note]`, `[!warning]` has `> ` prefix (use `rg -n '^\[!'` to verify — any match means a broken callout)
- [ ] **Subpart line breaks**: every `(1)`/`(2)`/`(3)` question subpart inside a callout is on its own `>` line — no single `>` line contains two or more `(N)` subparts (grep suspect lines with `rg -n '\([0-9]+\)[^(]*\([0-9]+\)'` inside callout regions, then confirm each remaining hit is a false positive like coordinate pairs)
- [ ] **Callout title line is label-only**: every `> [!question]` title line holds only the `例题N`/`例N`/`练习N` label and its source tag — the stem body (已知…/设…/若…/求…) starts on the next `>` line. ✅ Automated by `lint_question_callout_title_attached` (Step 4 validator). No stem sentence glued onto the title line.
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
- [ ] **Imaginary-unit notation** (added 2026-06-29): in complex-number/algebra/trig docs, every imaginary-unit `i` is `\mathrm{i}` and wrapped in `$...$`; no bare `i` inside math (excluding `\sin`/`\cos`/`\ln` command internals). See `references/canonical-markdown-rules.md` → "Imaginary-Unit Notation".
- [ ] **Question-block rewrite (Step 2.7)**: report whether Step 2.7 ran, how many question blocks were rewritten against `page-transcript.raw.md`, whether all subagents carried the raw-transcript reference, and how many single-page re-OCR appeals were made (with outcomes). If the document had question blocks but Step 2.7 was skipped, that is a defect — question-block structure is the most common source of "unclean" output.
- [ ] **Chunk boundary clean**: if parallel chunks were used, no duplicate headings or bullet points at boundaries, and no bare callouts without `>` prefix
- [ ] **Q&A ordering**: ✅ Automated by `lint_qa_ordering` (Step 4 validator). Each question's analysis follows directly.
- [ ] **Image paths**: ✅ Automated by `lint_image_path` (Step 4 validator). Paths use `doc2x/export/images/...`.
- [ ] **Sweep-on-report**: if the user reports ANY rule violation on a specific instance, you MUST immediately sweep the ENTIRE document for all other instances of the same violation class — do not fix only the one the user pointed out
