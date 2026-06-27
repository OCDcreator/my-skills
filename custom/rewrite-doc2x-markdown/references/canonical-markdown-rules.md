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
- Question subpart labels such as `(1)`, `(2)`, `(3)` MUST stay inside the question callout when they are part of the original problem. **Each subpart MUST be on its own line** — never cram multiple `(N)` subparts onto a single line, which renders as an unreadable wall of text (变成一坨).
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
- <!-- evolved 2026-06-17 --> For simple formula lists, keep separators outside math delimiters: write `$m$, $n$`, `$\alpha$, $\beta$`, `${x}_{1}$, `${x}_{2} \in D$`. Keep commas inside math delimiters for intervals, coordinates, function arguments, arrays, and complex formulas such as `$f(x, y)$`, `$(0, 1)$`, or `$\left[ a, b\right]$`.
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
