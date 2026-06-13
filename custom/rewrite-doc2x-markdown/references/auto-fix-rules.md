# Auto-Fix Rules

Apply these rules mechanically before any structural rewriting. Do not hesitate, do not debate — each rule is a direct text transformation. Execute them in order on the raw Doc2X output.

## 1. Math Delimiter Normalization

```
BEFORE: \(a \parallel b\)  or  \[a \parallel b\]
AFTER:  $a \parallel b$    or  $$a \parallel b$$
```

- `\(...\)` → `$...$`
- `\[...\]` → `$$...$$` (standalone block)
- Do not touch `$...$` or `$$...$$` that are already correct.

## 2. Inline Math Boundary Spacing

```
BEFORE: $ x $ or $ a \parallel b $
AFTER:  $x$   or $a \parallel b$
```

Strip exactly one leading space and one trailing space inside `$...$` delimiters. Do not touch multi-line display math `$$...$$`.

## 3. Fraction Standardization

| Case | Rule | Example |
|------|------|---------|
| Simple display fraction | `\frac` → `\dfrac` | `\dfrac{1}{2}` |
| Nested fraction (numerator/denominator has formula) | `\frac` → `\tfrac` | `\dfrac{\tfrac{1}{2}}{3}` |
| Already `\dfrac` or `\tfrac` | skip | — |

## 4. Fused Formula Splitting

**This is the most commonly missed rule. Read carefully.**

Doc2X often merges multiple math relations into one inline formula blob. Every comma between two independent relations must be moved outside `$...$`.

### What to split

```
BEFORE: $f(x) = 0, x = 1$
AFTER:  $f(x) = 0$，$x = 1$

BEFORE: $f\left( x\right) = {e}^{x} + a{x}^{2} + e\left( 1 - x\right) \geq 0,\dfrac{{e}^{x} + e\left( 1 - x\right) }{{x}^{2}} + a \geq 0$
AFTER:  $f\left( x\right) = {e}^{x} + a{x}^{2} + e\left( 1 - x\right) \geq 0$，$\dfrac{{e}^{x} + e\left( 1 - x\right) }{{x}^{2}} + a \geq 0$

BEFORE: $a = \dfrac{1}{e}, {x}_{0} = e$
AFTER:  $a = \dfrac{1}{e}$，${x}_{0} = e$
```

Rules:
- Split at commas between **complete, independent relations** (two things that each have `=`, `≥`, `≤`, `>`, `<`).
- Move punctuation (commas, periods) **outside** `$...$` delimiters.
- Replace the comma with a Chinese comma `，` when in Chinese text context.
- Keep implication chains together (do not split at `\Rightarrow`).
- Keep function arguments together: `$f(x, y)$` is NOT fused — the comma is inside a function call.

### How to verify after applying

After applying this rule, run:
```bash
rg -n '\$[^$]*[，,][^$]*[=<>≥≤][^$]*\$' source-transcript.md
```
Any result that shows TWO independent relations (`=`, `≥`, etc.) separated by a comma inside one `$...$` is a MISSED split. Fix it before proceeding.

**This rule requires semantic understanding — do NOT use regex to apply it.** Use subagents to read and split fused formulas manually.

## 5. Fill-in-Blank Normalization

```
BEFORE: ____ or ---- or ______ or ----------
AFTER:  __________
```

All fill-in blanks become exactly ten underscores with no spaces.

**⚠️ KNOWN BUG — HTML COMMENT CORRUPTION:**
This rule (or the validator's `--fix` mode) may incorrectly transform `--` inside HTML comments. The pattern `<!-- page 289 -->` contains `--` which gets matched as a fill-in-blank dash, producing `<!__________ page 289 __________>`.

**Prevention:** After applying this rule (or after running `validate_canonical_markdown.py --fix`), ALWAYS check:
```bash
rg -n '<!_' source-transcript.md    # Should return 0 results
rg -n '<!--' source-transcript.md   # HTML comments should start with <!-- not <!_
```
If corrupted, restore `<!-- ... -->` format manually.

## 6. Doc2X OCR Residual Symbol Removal

### Leading orphan punctuation

```
BEFORE: ）例题   。定理   ，已知   例题。）   。文本
AFTER:  例题     定理     已知     例题。    文本
```

Remove these when they appear at the start of a line or paragraph:
- `）`, `））`, `)))`
- `。`, `，`, `、`
- `..`, `...` (only if clearly not an ellipsis — keep `...` in math context)
- `.)`, `。) `

### Stray escape characters from Doc2X internal formatting

```
BEFORE: \*   \#   \_   \[   \]
AFTER:  *    #    _    [    ]
```

Remove backslash escapes that Doc2X injected but are not real LaTeX commands.

## 7. Print Header/Footer Noise Removal

Delete lines matching any of these patterns when they repeat across multiple pages:

```
MST 高中基础知识与二级结论
(any line that is only a chapter/section name repeated at page top, not inline with content)
(any line that is only a bare page number like "274" on its own line)
```

Do NOT delete chapter/section names that appear as real in-content headings.

## 8. Common OCR Character Fixes

| Doc2X output | Fix | Context check required |
|-------------|-----|----------------------|
| `己` | `已` | Verify from page image |
| `末` | `未` | Verify from page image |
| `千` | `干` | Verify from page image |
| `人` | `入` | Verify from page image |
| `白` | `日` | Verify from page image |
| `α` (fullwidth) | `α` (halfwidth) | In formula context |
| `β` (fullwidth) | `β` (halfwidth) | In formula context |
| `∥` (fullwidth) | `\parallel` | In formula context |

If you cannot confirm the fix from the page image, leave the character and add `[TO VERIFY: char]` nearby.

## 9. Doc2X Numbered List Artifact Cleanup

Doc2X sometimes renders numbered lists with artifacts:

```
BEFORE: 1.. 定义   或   1。。定义
AFTER:  1. 定义
```

```
BEFORE: ①. 内容   或   ①.. 内容
AFTER:  ① 内容
```

Remove the extra `.` or `。` after numbered markers.

## Execution Order

Always execute rules in this order:
1. Rule 6 (residual symbol removal) — clean noise first
2. Rule 7 (page header/footer) — remove noise
3. Rule 9 (list artifacts) — normalize numbering
4. Rule 1 (math delimiters) — normalize delimiters
5. Rule 4 (fused formulas) — split merged formulas
6. Rule 2 (math spacing) — strip boundary spaces (AFTER splitting)
7. Rule 3 (fractions) — standardize fractions
8. Rule 5 (fill-in blanks) — normalize underscores
9. Rule 8 (OCR chars) — fix characters (requires page image comparison)
