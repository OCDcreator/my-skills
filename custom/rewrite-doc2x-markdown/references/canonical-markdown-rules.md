# Canonical Markdown Rules

Use these rules when rewriting Doc2X output into `source-transcript.md`.

## Core Principle

Regenerate Markdown structure, not source meaning. Fix broken OCR layout, headings, formula grouping, table structure, image placement, question blocks, and analysis readability while preserving the original content order.

## Page And Heading Shape

- Start with a real title that describes the document or knowledge area.
- Never use `# Source Transcript` as the final title.
- Do not emit visible generic page headings such as `## Page 274`.
- Remove `<!-- source-page: N -->` markers; they are internal metadata and must not appear in the final transcript.
- Use real headings for titles and sections, based on the actual content structure.
- Remove numeric outline prefixes such as `1.`, `1.1`, and `1.1.1` from headings and body structure labels.
  - **Example**: `**1. 平移变换**` → `**平移变换**`；`**2. 伸缩变换**` → `**伸缩变换**`
  - **Exception**: Question subparts inside callouts like `(1) $f(x) = ...$` → keep as-is
- **Mis-marked heading downgrade**: when the heading validator flags a line as not a valid heading but the content is genuinely an *emphasis intent* (a highlighted term, a boxed conclusion, a key word the original print visually emphasized — not a real chapter/section), **downgrade to emphasis instead of deleting it**. Apply bold/italic or a semantic color per `emphasis-and-color-rules.md`. Example: OCR turned a boxed "★ 易错点" into `## 易错点`; the heading check rejects it, so downgrade to `<span style="color: red;">★ 易错点</span>` as inline emphasis, preserving the content.
- **Document headings are preserved during question-block rewrite** (added 2026-06-28 stress-test lesson). The Step 2.7 rewrite touches only question-block STRUCTURE; the document's section title hierarchy (`# 文档标题` / `## 第一节` / `### 经典例题`) is NOT a question block and **MUST pass through verbatim** — every `#`/`##`/`###` line keeps its original text, level, and position. Weaker models tend to frame "rewrite the question blocks" as "output ONLY the question blocks", silently dropping every heading. The output is a FULL rewrite of the document from its first `#` heading to its end, not an extract. See `question-block-rewrite-guide.md` → "Document headings preserved verbatim" for the literal-echo guard step.
  - WRONG (crammed on one line): `> (1) 求切线方程；(2) 求极值。`
  - RIGHT (one subpart per line):
    ```
    > (1) 求切线方程。
    >
    > (2) 求极值。
    ```
- Remove print header/footer noise such as `MST 高中基础知识与二级结论`.
- For long files, create `markdown-rewrite-plan.md` with checked chunks before final validation:
  `- [x] Page 274 - 线面平行`

### Heading Hierarchy

- `#` = Chapter title (level 1)
- `##` = Section title (level 2, e.g., "第一节", "第二节")
- `###` = Knowledge point title (level 3, e.g., "知识点一", "知识点二")
- `####` = Subsection title (level 4, e.g., "一、", "二、")
- Never skip levels or use inconsistent hierarchy.
- <!-- evolved 2026-06-17 --> Heading hierarchy is semantic, not just numeric. Topic headings and their generic child headings must form a meaningful outline: e.g. `### 指对同构：技巧与模型` may contain `#### 知识点总结`, `#### 经典例题`, and `#### 归纳总结`; those child labels should not appear as siblings of the owning topic. When the user reports heading hierarchy problems, sweep the whole affected chapter/section and inspect the rendered outline semantics, not only heading-level jumps.

#### 标题层级参照（outline.md 作为 ground truth）

When `doc2x/outline.md` exists with real bookmark entries (`extract-manifest.json` reports `"has_outline": true`), the Markdown heading depth is **not** assigned by feel or by OCR-implied structure — it follows the PDF outline's indentation depth. This is the mechanism that fixes the recurring "rewrite 出来的标题层级经常错" defect.

**Depth mapping rule:**

| outline.md indent level | Markdown heading |
|--------------------------|------------------|
| Level 1 (top-level, e.g. 第N章) | `#` |
| Level 2 (e.g. 第N节) | `##` |
| Level 3 (e.g. 知识点N) | `###` |
| Level 4+ | `####` / deeper, clamped at 6 |

- Read `doc2x/outline.md` once at Step 0 and carry it through every chunk and every self-check.
- Each Markdown heading's `#`-depth must equal the outline level of its matching entry. A heading that the outline places at Level 2 must be `##`, not `#` and not `###`.
- Outline entries suffixed with `（上下文）` sit just outside the extracted page range but still anchor the hierarchy above the in-range content — they establish the ancestor levels and must appear at their correct depth (typically as the document's top `#`/`##`).
- OCR often mislevels headings (a 知识点 becomes `##` instead of `###`, or a 第N节 collapses to a paragraph). Cross-check every section heading against outline.md during Step 6's "Semantic heading hierarchy" item; correct mismatches rather than deferring to `[TO VERIFY]`.
- When the outline and OCR disagree on a heading's *existence* (outline has it, OCR dropped it; or vice versa): trust the outline for *level*, but trust OCR content for *presence* — do not invent headings the OCR text does not support just because the outline lists them.
- When `outline.md` is empty (`has_outline: false`, no PDF bookmarks) or absent (older job), fall back to the semantic judgment rules above. The outline is an authority when present, never a blocker when absent. <!-- added 2026-06-27 -->

## Question Callouts

Each complete question stem must be one continuous Obsidian callout.

Use this shape:

```md
> [!question] 题干
> 已知条件……求……
>
> <div class="choice-grid" style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0.2rem 0.8rem;align-items:start;">
> <span>A. 选项一</span><span>B. 选项二</span><span>C. 选项三</span><span>D. 选项四</span>
> </div>
```

Hard rules:

- Put the stem, sub-questions, and choices inside the same callout.
- **Each numbered subpart `(1)`, `(2)`, `(3)` inside a callout MUST be on its own `>` line**, separated from the next subpart by a blank `>` spacer line. Putting `(1) … (2) … (3) …` on one line is a critical formatting failure (crammed into an unreadable lump).
- Prefix every line inside the callout with `>`, including blank spacer lines.
- Do not leave a naked blank line inside the callout.
- **Callout must end with a blank line (no `>`)** before `**解析**` or the next content. If the callout ending is directly followed by `**解析**` without an empty line, Obsidian will render `**解析**` inside the callout.
- **Every example/exercise labeled paragraph must live inside a callout (blockquote).** A line beginning with `例题N` / `练习N` (with optional `**bold**`, `【】`/`[]` brackets, or Chinese numerals) is an example label. If such a label is NOT on a `>` line, the downstream print builder renders it as a plain paragraph with no `.phycat-blockquote` styling — this is the root cause of "examples have no quote block" defects. The label, the stem, and any sub-questions/choices all belong in the same callout. The analysis (`**解析**`) that follows must stay OUT of the callout per the analysis rule below — only the question side is blockquoted. This extends the existing choice-callout rule from choice questions to ALL examples and exercises. <!-- evolved 2026-06-23 -->

### Title line holds only the label + source <!-- added 2026-06-27 -->

The callout's title line (the `[!question]` line) must contain **only** the example/exercise label and its optional source tag — never the stem body. The stem (the actual problem: 已知…/设…/若…/求…) starts on the **next** `>` line. The title line cannot be simultaneously the "题号" and the "题干第一句".

Source tags come in many shapes across different PDFs — all are legitimate on the title line:
- `例题 1 (2017・新课标 I )`
- `例题 1`
- `练习 2 【2018全国I】`
- `例 1`
- `例题 3  (2018 年 · 全国卷 Ⅰ)`

The deciding factor is the **stem**, not the source format: the stem's first sentence must begin on its own `>` line.

**WRONG** (stem glued onto the title line):
```md
> [!question] 例题 1 (2017・新课标 I ) 已知椭圆 $C : \dfrac{x^2}{a^2} + \dfrac{y^2}{b^2} = 1\left( {a > b > 0}\right)$，四点 ${P}_{1}\left( {1,1}\right)$。
```

**RIGHT** (label + source on the title line; stem on the next `>` line):
```md
> [!question] 例题 1 (2017・新课标 I )
> 已知椭圆 $C : \dfrac{x^2}{a^2} + \dfrac{y^2}{b^2} = 1\left( {a > b > 0}\right)$，四点 ${P}_{1}\left( {1,1}\right)$。
```

This is enforced by `lint_question_callout_title_attached` (Step 4 hard gate). The lint anchors on the universal label (`例题N`/`例N`/`练习N`), strips any source tag, then flags the callout if stem text remains on the title line. It is **non-auto-fixable** — deciding where to break the stem is a semantic judgment, so the fix is to re-split the title line by hand (or re-run Step 2.7 against the raw transcript).

### Choice Format

Use **Markdown tables** inside the callout for choices. Do not use HTML `<div>` or `<span>` structures — formulas inside HTML tags do not render in Obsidian.

**Short choices (≤ 15 Chinese characters per option) — ONE row, 4 columns:**

```md
> | A. 0 | B. 1 | C. 2 | D. 3 |
> | :---: | :---: | :---: | :---: |
```

**Long choices (> 15 Chinese characters per option) — TWO rows, 2 columns each:**

```md
> | A. 较长的选项内容 | B. 另一个选项 |
> | :---: | :---: |
> | C. 第三个选项 | D. 第四个选项 |
```

Do not add a second alignment row after the C/D row in a two-row choice table. In Obsidian/Typora this renders as an extra visible row beneath the choices; one alignment row after A/B is enough for the two-column table.

**Image options:**

```md
> | A | B | C | D |
> | :---: | :---: | :---: | :---: |
> | <img src="..." alt="A" style="max-width:22%;" /> | <img src="..." alt="B" style="max-width:22%;" /> | <img src="..." alt="C" style="max-width:22%;" /> | <img src="..." alt="D" style="max-width:22%;" /> |
```

Hard rules:

- Every cell in the table must have `> ` prefix (same as the rest of the callout).
- Formulas in cells use `$...$` — they are inside the table, which is inside the callout, so they render correctly in Obsidian.
- Do not use HTML `div` + `span` for choice grids — `$...$` inside `<span>` does not render.
- Do not use Markdown lists (`- A.`, `- B.`) for choices inside callouts — they break the table layout.
- Use `:---:` for centered alignment.

## Question Analysis Blocks

Question analysis follows the callout. **There must be an empty line between the callout and the analysis.**

**Q&A ordering rule (MANDATORY):** Each question's analysis/answer (`**解析**` / `**解答**` / `**证明**`) MUST appear DIRECTLY below its own question callout — never grouped separately. If a document has 练习1, 练习2, 练习3, the correct order is: 练习1 question → 练习1 analysis → 练习2 question → 练习2 analysis → 练习3 question → 练习3 analysis. Grouping all questions together then all analyses together is a structural failure. This applies to 例题 and 练习 alike.

For formula-heavy math content, use **plain Markdown** with `**解析**` or `**解**` heading, NOT HTML blocks. The HTML `analysis-block` format requires MathML for all formulas, which is impractical for complex math.

Use this shape:

```md
> | A. $x^2$ | B. $2^x$ | C. $x^{-1}$ | D. $x^3$ |
> | :---: | :---: | :---: | :---: |

**解析**

根据条件 $f(x) = ...$，分析如下...

具体步骤：
1. 先求导：$f'(x) = ...$
2. 判断单调性：...
3. 结论：答案为 A。
```

Hard rules:

- **There must be an empty line between the callout end and `**解析**`**. No `>` prefix on the empty line.
- Use `**解析**` or `**解**` in bold (not callout, not HTML block).
- Regenerate Doc2X's clumped analysis into readable paragraphs.
- Split by real solution logic, not by OCR line breaks.
- Keep compact: 2-4 short paragraphs; complex problems may use 6 paragraphs.
- Do not leave one huge dense paragraph, and do not scatter into one-line fragments.
- Do not add new teaching content not supported by the source.
- **All formulas in analysis use `$...$` or `$$...$$`** — this is Markdown, not HTML, so MathML is not needed.
- **Images in analysis**: If the analysis references a figure or diagram, use HTML `<img>` with the correct sizing (`max-width:20%`) and place it in the relevant paragraph. Do not use Markdown image syntax `![]()` inside analysis blocks.
- Only use HTML `analysis-block` when the analysis contains ZERO formulas (pure text).

## Formulas

- Follow the local `obsidian-markdown` skill's math syntax: inline math is `$...$`, display math is a standalone `$$...$$` block.
- Do not use `\(...\)` or `\[...\]`; these are not friendly for the user's Typora and Obsidian workflow.
- Inline math must not contain boundary spaces: write `$x$`, `$a \parallel b$`, and `$\alpha$`; never write `$ x $`, `$ a \parallel b $`, or `$ \alpha $`.
- Obsidian/Typora Markdown math is only reliable in normal Markdown, callouts, and blockquotes.
- HTML content must not contain Markdown math delimiters. Inside `<td>`, `<span>`, `<div>`, `<p>`, choice grids, tables, and analysis blocks, render formulas as MathML or accessible inline SVG. **This restriction applies to semantic-color spans too**: `<span style="color: ...;">` may only wrap pure text, never `$...$`. For emphasizing text that contains a formula, use bold/italic, or split the formula out and wrap only the prose parts — see `emphasis-and-color-rules.md` → "Formula Conflict".
- Use MathML for simple HTML formulas.
- For complex layout-sensitive HTML formulas such as cases, large braces, aligned multi-row implications, or matrices, prefer inline SVG generated by MathJax. This keeps the formula shape stable in Typora/Obsidian HTML blocks and avoids collapsed one-line MathML.
- Inline SVG math must be vector math, not a raster screenshot. Use `class="math-svg"`, `role="img"`, and a meaningful non-empty `aria-label`.
- Do not rely on MathML `<mtable>` alone if Typora/Obsidian collapses it into one line.
- If an HTML formula is too complex to express safely as MathML and SVG generation is not available, move that content out of HTML and rewrite it as normal Markdown with `$...$` or `$$...$$`.
- Preserve mathematical meaning and symbol order.
- Split fused Doc2X formulas into readable units.
- Keep punctuation outside math delimiters when possible.
- <!-- evolved 2026-06-17; multi-interval-list + dangling-tail added 2026-06-29 --> For simple formula lists, keep separators outside math delimiters: write `$m$, $n$`, `$\alpha$, $\beta$`, `${x}_{1}$, `${x}_{2} \in D$`. Keep commas inside math delimiters for intervals, coordinates, function arguments, arrays, and complex formulas such as `$f(x, y)$`, `$(0, 1)$`, or `$\left[ a, b\right]$`.
  - <!-- evolved 2026-06-29 --> **A list of multiple intervals is a LIST, not one interval.** Each interval is its own unit: the comma *between* intervals goes OUTSIDE the math, while the comma *inside* each interval stays in. WRONG (all crammed in one `$...$`): `$\lbrack {5.31}, {5.33}), \lbrack {5.33}, {5.35}), \cdots$`. RIGHT: `$\lbrack {5.31}, {5.33})$, $\lbrack {5.33}, {5.35})$, $\cdots$, $\left\lbrack {{5.47}, {5.49}}\right\rbrack$`. Same for percentage/value series: `${60}\%$, ${60}\%$, ${65}\%$, …` (not `${60}\% , {60}\% , {65}\%$`). Enforced by `lint_list_inside_math` (Step 4 validator).
- <!-- added 2026-06-29 --> **A formula must be complete inside its delimiters — never truncate.** If an equation continues past an operator/relation, the operand/result belongs INSIDE the `$...$`. WRONG (tail leaked out as prose): `方差 ${s}^{2} = \dfrac{1}{100}[\cdots] =$ 0.0296,` — the trailing `0.0296` is plain text because the span closed at `=$`. RIGHT: keep the whole equation in one span, or move it to a `$$...$$` display block (preferred for long chains — see "multi-equality chain" below). Enforced by `lint_formula_dangling_tail` (Step 4 validator).
- <!-- added 2026-06-29; reworked 2026-07-01 — replaced the ~90-source-char heuristic with
     a real-rendered-width three-band classifier (the char count badly over-estimated: a
     verbose-but-short-render formula like the sin β chain is 275 source chars but renders
     only ~360px). --> **A long multi-equality chain belongs in a `$$...$$` display block folded with `\begin{aligned}` — but "long" is judged by RENDERED WIDTH, not source characters.** Decide via the three-band classifier (A4 text area ≈ 695px @ 96dpi, font-size 12px):
  - **short** (renders ≤ 464px = A4 ⅔): keep inline, regardless of `=` count. Verbose LaTeX macros (`\overrightarrow{CM}` = 18 source chars, 1 render glyph) inflate source length without inflating render width — do NOT be fooled.
  - **long** (renders > 625px = A4 90%): convert to `$$\begin{aligned} a &= ... \\ &= ... \end{aligned}$$` — it almost certainly overflows or wraps ugly.
  - **medium** (renders 464–625px): judge in context — convert if it's a genuine multi-step derivation the reader follows step-by-step; keep inline if it's a compact evaluation that still fits.
  - **How to measure**: `lint_long_inline_formula` (Step 4 validator) is a COARSE signal — it estimates width by regex macro folding and over-flags. When it flags a formula, measure the TRUE width: `py -3 scripts/measure_inline_formula_width.py --md <file> --band medium,long --dedup` (renders via plain KaTeX print + headless Chromium, container-independent). A single long expression (one `=` or none, e.g. a big `\dfrac{1}{N}\sum...`) is a legitimate inline span and is NOT flagged.
- <!-- added 2026-06-30 — Doc2X abuses `aligned`; enumerate unrelated values with `gathered`/`\quad` --> **`\begin{aligned}` is for ONE calculation chain, NOT for enumerating unrelated formulas.** `\begin{aligned}` with `&=` aligns the steps of a *single* quantity being simplified (`P &= ... \\ &= ... \\ &= ...`); it is meaningless when each row is a *different* quantity. Doc2X abuses `aligned` to force-align the `=` signs of parallel values — that alignment has no mathematical meaning (the equations are independent, not a chain). WRONG: `\begin{aligned} P(A)&=\tfrac12\\ P(B)&=\tfrac12\\ P(AB)&=\tfrac14 \end{aligned}`. RIGHT: one display line with `\quad` separators `$$P(A)=\tfrac12,\quad P(B)=\tfrac12,\quad P(AB)=\tfrac14$$`; or `\begin{gathered}` (centers each line, does NOT align `=`) if they truly need separate lines. Rule of thumb: if each `&=` row is a *different* quantity, it is an enumeration → `gathered`/`\quad`; if the rows are the *same* quantity transformed step by step, it is a chain → `aligned`.
- <!-- added 2026-06-30 — KaTeX parse failure: `$$.`/`$$,` breaks the renderer --> **`$$` delimiters must sit on their own line; never let punctuation touch a `$$`.** Doc2X emits `$$...$$.`/`$$...$$,` (period/comma glued to the closing `$$`) and single-line `$$X$$`; in strict KaTeX these corrupt the parser state and every formula *after* the bad block silently fails to render (the visible error `You can't use 'macro parameter character '#' in math mode` is a red herring — it comes from the corrupted state machine, usually pointing at an unrelated `<span style="color:#...">` line). Always: closing `$$` alone on its line, punctuation (`.`/`,`/`；`) on the next line or outside the block. Unwrap single-line `$$X$$` → `$$\nX\n$$`. This is the block-level counterpart of "move punctuation outside `$...$`" (auto-fix-rules.md) and is enforced by the L204 standalone-delimiter rule below.
- <!-- evolved 2026-06-17 --> Display math delimiters must be standalone block lines. Never emit `$$formula$$` on one line; write `$$`, then the formula content, then `$$` on its own line. Multi-line display formulas must also place the opening and closing `$$` on separate lines.
- Prefer KaTeX-safe simple notation.
- Use `\mathbin{/\!/}` for parallel lines/planes. Do NOT use `\parallel`.
- Avoid fragile macros and environments: `\mspace`, `\left.`, `\overset{\large\frown}{...}`.
- **Preserve `\begin{array}` from Doc2X output as-is.** Do NOT convert to `\begin{cases}` or any other construct. The Doc2X `\begin{array}{l}...\end{array}` format is correct and should be kept verbatim. Unauthorized conversions are a critical error.
- For condition groups in normal Markdown, prefer `\begin{cases} ... \end{cases}` inside a `$$...$$` block **only when the source does not already use `\begin{array}`**. If Doc2X output uses `\begin{array}`, keep it. Inside HTML, use MathJax inline SVG for polished braces/cases; use `math-cases` with vertical `case-lines` and MathML fragments only as a fallback when SVG generation is unavailable.
- For arcs, prefer a simple notation such as `\widehat{AC}`.
- ALL normal fractions use `\dfrac{...}{...}` — both inline `$...$` and display `$$...$$`.
- Only nested fractions use `\tfrac{...}{...}`. **"Nested" means the fraction is INSIDE one of these contexts**:
  - The `{numerator}` or `{denominator}` braces of another `\dfrac{...}{...}` or `\tfrac{...}{...}`
  - An exponent: `^{...\dfrac...}` or `{e}^{\dfrac...}`
  - A subscript: `_{...\dfrac...}`
  - Inside `\sqrt{...\dfrac...}`
- **Function arguments are NOT nested contexts.** `\ln(\dfrac{1}{x})`, `\log(\dfrac{a}{b})`, `\sin(\dfrac{\pi}{2})` — the fraction inside the parentheses is a standalone fraction and must use `\dfrac`, NOT `\tfrac`. Being the argument (真数) of `\ln` or `\log` does not make it nested. Only `\log_{\tfrac{1}{2}}` (the BASE, written as a subscript) would use `\tfrac`.
- Never use plain `\frac{...}{...}`.
- Mark uncertain symbols locally with `[TO VERIFY: ...]`.
- Use `\lvert ... \rvert` for absolute values and vector magnitudes. Do NOT use `\left| ... \right|` which stretches incorrectly. Example: `\lvert \overrightarrow{AB}\rvert` not `\left| \overrightarrow{AB}\right|`.
- `\begin{array}` MUST have `\left\{` before and `\right.` after. Example: `\left\{ \begin{array}{l} ... \end{array}\right.`. Never have bare `\begin{array}` without the braces.

Example:

```md
若 $a \parallel \alpha$，$a \subset \beta$，且 $\alpha \cap \beta = b$，则 $a \parallel b$。
```

HTML MathML example:

```html
<td style="vertical-align:middle;"><math><mi>a</mi><mo>∥</mo><mi>α</mi></math></td>
```

HTML inline SVG math example:

```html
<span class="math-svg-wrap" style="display:inline-block;color:inherit;line-height:1;vertical-align:middle;">
  <svg class="math-svg" xmlns="http://www.w3.org/2000/svg" width="12ex" height="4ex" role="img" aria-label="a 平行 b" focusable="false" viewBox="0 0 120 40">
    <path d="M10 10H110M10 30H110" />
  </svg>
</span>
```

Fallback HTML condition-group example:

```html
<span class="math-cases" style="display:inline-flex;align-items:center;justify-content:center;gap:0.35em;line-height:1.2;">
  <math xmlns="http://www.w3.org/1998/Math/MathML" style="font-size:3.2em;line-height:1;"><mo>{</mo></math>
  <span class="case-lines" style="display:inline-flex;flex-direction:column;align-items:flex-start;gap:0.12em;">
    <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>a</mi><mo>⊄</mo><mi>α</mi></math>
    <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>b</mi><mo>⊂</mo><mi>α</mi></math>
    <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>a</mi><mo>∥</mo><mi>b</mi></math>
  </span>
  <math xmlns="http://www.w3.org/1998/Math/MathML"><mo>⇒</mo><mi>a</mi><mo>∥</mo><mi>α</mi></math>
</span>
```

## Vector Notation

- Vectors **a**, **b**, **c**, **e** must use bold notation: `$\mathbf{a}$`, `$\mathbf{b}$`, `$\mathbf{c}$`, `$\mathbf{e}$`.
- Never use plain `$a$`, `$b$`, `$c$` for vectors.
- Exception: Point labels like `$A$`, `$B$`, `$C$` stay as-is (these are not vectors).
- Exception: Triangle side lengths in 解三角形 sections stay as-is (these are scalar lengths, not vectors).

## Emphasis & Color

The rewrite may use emphasis (bold/italic) and semantic color to (a) redirect mis-marked headings and (b) proactively mark key points (conclusions, pitfalls, techniques) for reader attention.

**Full rules, palette, formula-conflict handling, and anti-over-marking criteria**: see `emphasis-and-color-rules.md`.

Quick reference (palette is fixed — never freelance colors):

| Meaning | Color |
|---------|-------|
| 结论 / 重点 / 关键定理 | `#9370DB` purple |
| 易错 / 警示 / 陷阱 | `red` |
| 口诀 / 技巧 / 方法名 | `green` |
| 补充 / 备注 / 拓展 | `blue` |

Hard rules:
- **Color spans wrap pure text only** — never `$...$`. For emphasizing formula-containing text, use bold/italic, or split and wrap prose parts only (the existing "HTML 内禁公式" rule applies to color spans).
- **Mark sparingly**: at most 1-2 spots per analysis block; never mark routine derivation steps. A page full of color has no emphasis.
- **One meaning = one color, document-wide**.

## Punctuation Consistency

Commas in the transcript must be clean and consistent. Hard rules:

- **Every English comma `,` must be followed by exactly one space** — never glued to the next character. `由题意可知,继续推导` is wrong; write `由题意可知, 继续推导`. (Chinese full-width `，` carries its own spacing and needs no extra ASCII space.)
- **Do not mix `，` and `,` within a single paragraph or callout** — pick one comma style per block and use it consistently throughout that block.
- **Default style stays as existing rules specify**: Chinese `，` in Chinese prose (per `proofreading-checklist.md` and `analysis-retypesetting.md`); English `, ` between adjacent formulas and in coordinate/list contexts.
- Collapse any double spaces after a comma (``,  `` → `, `).

Verify (judgment required — math spans and code are false-positive sources):
```bash
# English comma directly followed by a non-space character
rg -n ',[^ \n,)]' source-transcript.md
# Inspect each hit; skip false positives inside $...$ math (e.g. $f(x,y)$), code spans, HTML attributes.
```

This rule is **model-enforced**, not a validator regex — comma placement across mixed math/HTML/code contexts is semantic (per Forbidden Pattern F1) and a naive regex would misfire on function arguments like `$f(x, y)$`.

## Imaginary-Unit Notation (`\mathrm{i}`) <!-- added 2026-06-29 -->

In any document containing the imaginary unit (复数/代数/三角章节), normalize **every** imaginary-unit `i` to `\mathrm{i}` and ensure it is inside math delimiters. Doc2X emits `i` inconsistently (sometimes `\mathrm{i}`, sometimes bare `i`, sometimes a bare `i` in prose outside any `$...$`), and an italic `i` renders as a variable while an upright `\mathrm{i}` reads as the constant — the inconsistency is a real readability defect, not taste.

- **Inside `$...$` / `$$...$$`**: bare imaginary-unit `i` → `\mathrm{i}`. Covers both algebraic form (`(2+i)` → `(2+\mathrm{i})`, `{2i}` → `{2\mathrm{i}}`, `1-i` → `1-\mathrm{i}`) and trigonometric form (`cos θ + i sin θ` → `cos θ + \mathrm{i}\sin θ`).
- **In prose outside math**: a bare `i` mentioning the unit → `$\mathrm{i}$`; a half-wrapped `$b$ i` → `$b\mathrm{i}$`; a bare real number in vector/complex context (`得到 -1 的向量`) → `$-1$`.
- **Do NOT touch** the `i` inside `\sin` / `\cos` / `\tan` / `\ln` / `\lim` / `\operatorname{...}` etc. — those are LaTeX command names, not the imaginary unit. Deciding whether an `i` is the unit vs a command letter vs a variable requires reading the context — this is **semantic**, not regex-able (Forbidden Pattern F1).
- **Do NOT** change any value, sign, exponent, or structural macro — only the `i`→`\mathrm{i}` rendering and the prose-math wrapping. This rule layers on top of F3 (no unauthorized LaTeX conversions); it changes the *font command* of a single letter, not the formula structure.

This rule is **model-enforced**. Self-check after applying: a scan for bare imaginary-unit `i` inside math (excluding `\sin`/`\cos`/`\ln` internals) should return 0. Note the validator's prose-length counter (`lint_markdown_analysis_paragraphs`) can glitch on `\mathrm{}` tokens — see SKILL.md Step 4's known-glitch note.

## Analysis Block Re-typesetting

Detailed re-typesetting rules, OCR typo fixing procedures, subagent dispatch templates, and formula integrity verification commands are in **`references/analysis-retypesetting.md`**.

Key principles (summary):
- Doc2X dumps each analysis section as one massive paragraph — you MUST re-typeset into logical paragraphs
- Split at punctuation, method boundaries, logic transitions, and new formula introductions
- Maximum 300 characters per paragraph (formula content excluded)
- Fix OCR typos (已/己/巳, 人/入, 末/未, etc.) during re-typesetting
- For math-heavy content: use plain Markdown (`**解析**` with `$...$` / `$$...$$`), NOT `<div class="analysis-block">` HTML blocks

## Tables

- Use HTML tables, not Markdown pipe tables.
- Preserve row and column order.
- Do not invent a table header such as `| | 内容 |` when the source has no meaningful header.
- Center table content horizontally and vertically with HTML styles.
- If a table cell contains a formula, render that formula as MathML or accessible inline SVG; never put `$...$` or `\(...\)` inside `<td>`.
- If a table cell needs a multi-line condition group, prefer MathJax inline SVG. If using the `math-cases` fallback, its `case-lines` child must include `flex-direction:column`.
- If a table cell is unreadable, mark only that cell with `[TO VERIFY: ...]`.
- Do not flatten a table into a paragraph unless the source table cannot be reconstructed.

Use this shape:

```html
<table style="width:100%;border-collapse:collapse;text-align:center;vertical-align:middle;">
  <tr>
    <td style="vertical-align:middle;">文字语言</td>
    <td style="vertical-align:middle;">内容</td>
  </tr>
</table>
```

## Images

- Keep images near the text that refers to them.
- Prefer local image paths from the Doc2X export. **Paths are relative to `source-transcript.md`'s location.** Since `source-transcript.md` is in the job root and images are in `doc2x/export/images/`, the correct path is `doc2x/export/images/name.jpg` — NOT `images/name.jpg` (which would be a broken relative path).
- Use HTML figures with explicit sizing and centering styles.
- **Image sizing rules** (based on real-world rendering feedback):
  - ALL images use `max-width: 20%` — single figures, side-by-side figures, and triple figures alike.
  - Four choice images in a table row: `max-width: 20%` each (inside table cells, no flex needed).
- For standalone images outside callouts, use `<figure>` with `text-align:center`.
- For images inside callout tables, use `style="max-width:22%;"` directly in the `<img>` tag.
- Do not use Markdown image syntax `![]()` outside callouts; inside callouts, table cells may contain `<img>` tags.
- Do not put multiple `display:block` images under a plain `text-align:center` figure; they will stack vertically.
- Add a short figure note when the image role is not obvious.
- Do not promote tiny incidental crops into primary figures.
- If image content is required but unclear, write `[TO VERIFY: image detail unclear]`.
- Adjacent images (separated by one empty line, no prose between them) MUST be merged into a single side-by-side figure using `display:flex` layout. Pattern: `</figure>` + empty line + `<figure>` → merge into one `<figure>` with `display:flex`. This is enforced by `lint_adjacent_figures_must_merge` — emitting logically-grouped images (numbered 图1/图2/图3, multi-view sub-figures, sub-cases with no prose between them) as adjacent single-image figures stacks them vertically and is rejected. Independent figures separated by prose are not flagged. <!-- enforced 2026-06-23 -->

Use this shape for standalone images:

```html
<figure style="text-align:center;">
  <img src="../doc2x/export/images/example.jpg" alt="例题图" style="max-width:20%;height:auto;display:block;margin:0 auto;" />
</figure>
```

For two related images side-by-side (outside callouts):

```html
<figure style="display:flex;justify-content:center;align-items:center;gap:0.8rem;flex-wrap:nowrap;text-align:center;">
  <img src="../doc2x/export/images/example-1.jpg" alt="例题图1" style="max-width:20%;height:auto;display:block;margin:0 auto;" />
  <img src="../doc2x/export/images/example-2.jpg" alt="例题图2" style="max-width:20%;height:auto;display:block;margin:0 auto;" />
</figure>
```

## Common Failures To Fix

- Doc2X exported all analysis as one dense paragraph — MUST be re-typeset into logical paragraphs.
- Analysis sections not re-typeset: OCR typos and garbled text remain unfixed within analysis blocks.
- Choice options are outside the question block.
- Choice options are vertical lists even though a horizontal A4 grid would save space.
- A callout contains a naked blank line and breaks into two blocks.
- Question analysis still uses `> 解析：` instead of the required `**解析**` bold (for Markdown) or HTML `analysis-block` (for pure text).
- HTML table, choice grid, span, div, or analysis block contains `$...$` instead of MathML or inline SVG.
- HTML condition groups collapse into one line because they rely on `<mtable>` instead of MathJax inline SVG or a forced vertical `case-lines` fallback.
- Inline Markdown math has boundary spaces such as `$ x $`.
- Generic page headings, numeric outline prefixes, or print headers survive as content.
- Headings look like plain paragraphs or do not match the real document structure.
- Formula relations are fused into one unreadable inline formula — commas between independent relations must be split out.
- Plain `\frac` appears where `\dfrac` or nested `\tfrac` is required.
- Tables are converted into broken pipe text or prose.
- Images use Markdown syntax or lack sizing/centering control.
- Images use oversized max-width (72%, 45%, 36%, or 22.5%) instead of the correct size (20% for all images).
- Multiple images in one figure stack vertically because the figure lacks `display:flex`.
- `\begin{array}` was converted to `\begin{cases}` without authorization — this is a CRITICAL error, always preserve Doc2X's original LaTeX constructs.
- `\$` corruption: every `$` preceded by `\` due to incorrect regex replacement — verify with `rg '\\\$'` and must be 0.
- Paragraph splitting was done with regex scripts instead of semantic understanding — resulting in broken formulas or unnatural splits.
