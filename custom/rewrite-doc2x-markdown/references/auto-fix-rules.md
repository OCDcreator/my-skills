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

Doc2X often merges multiple math relations into one inline formula blob.

```
BEFORE: $a // \alpha , a \subset \beta , \alpha \cap \beta = b \Rightarrow a // b$
AFTER:  $a \parallel \alpha$，$a \subset \beta$，$\alpha \cap \beta = b \Rightarrow a \parallel b$
```

Rules:
- Split at commas between complete relations.
- Move punctuation (commas, periods) outside `$...$` delimiters.
- Replace `//` with `\parallel` in math context.
- Keep implication chains together (do not split at `\Rightarrow`).

## 5. Fill-in-Blank Normalization

```
BEFORE: ____ or ---- or ______ or ----------
AFTER:  __________
```

All fill-in blanks become exactly ten underscores with no spaces.

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
