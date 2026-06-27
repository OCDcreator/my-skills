# Emphasis & Color Rules

Rules for emphasis and color marking during rewrite. Two purposes: (1) **redirect mis-marked headings** — when the heading check decides a line is not a valid heading but the content is genuinely an emphasis intent, downgrade it to emphasis instead of deleting it; (2) **proactively mark key points** during question-block rewrite so the reader's attention is guided to conclusions, pitfalls, and techniques.

## Two Emphasis Mechanisms

### 1. Bold / Italic — safe everywhere

- `**text**` bold, `*text*` italic
- These are plain Markdown and work in **every** context: prose, callouts, analysis, and **around formulas**. They never break formula rendering.

### 2. HTML semantic color — pure text only

```html
<span style="color: #9370DB;">text</span>
```

- **Only wrap pure text.** The existing canonical rule "HTML content must not contain Markdown math delimiters" applies to color spans too — `$...$` inside a `<span>` does not render in Obsidian/Typora.
- If you need to emphasize text that **contains a formula**, use bold/italic, or split the formula out and wrap only the prose parts (see Formula Conflict below).

## Formula Conflict (the critical rule)

When the text you want to emphasize contains `$...$`:

- **Default — use bold or italic**, not color:

  | Wrong | Right |
  |-------|-------|
  | `<span style="color: #9370DB;">因此 $f(x)$ 取极小值</span>` ❌ formula inside span | `**因此 $f(x)$ 取极小值**` ✅ bold around formula |
  | `<span style="color: red;">注意 $\Delta < 0$</span>` ❌ | `*注意 $\Delta < 0$*` ✅ italic |

- **If color is genuinely needed and the formula is short**, split it — wrap only the prose parts, leave the formula bare:

  ```html
  <span style="color: #9370DB;">因此</span> $f(x)$ <span style="color: #9370DB;">取极小值</span>
  ```

  Only do this when the split is clean (formula sits between two prose fragments). If wrapping would fragment the sentence awkwardly, fall back to bold.

## Mis-Marked Heading Downgrade

When the heading validator (`lint_headings_and_print_noise`) flags a line as not a valid heading — e.g. a dotted numeric label, a print header, or content that is semantically emphasis rather than a section — and the content is genuinely an **emphasis intent** (a highlighted term, a boxed conclusion, a key word the original print visually emphasized):

- **Downgrade to emphasis, do not delete.** Apply bold/italic or semantic color per the rules above.
- Example: original print shows a boxed "★ 易错点" that OCR turned into `## 易错点`. The heading check rejects it (not a real section). Downgrade to `<span style="color: red;">★ 易错点</span>` as an inline emphasis marker, keeping the content.

The heading check still rules out genuine headings (chapter/section titles belong at `#`/`##`); this downgrade is only for lines that are *emphasis disguised as a heading*, not for real structure.

## Semantic Color Palette (fixed — do not freelance colors)

The agent must choose colors **only** from this palette. Free color choice produces inconsistent documents where the same concept (e.g. "易错") is red in one place and purple in another.

| Meaning | Color | Hex |
|---------|-------|-----|
| 结论 / 重点 / 关键定理 | purple | `#9370DB` |
| 易错 / 警示 / 常见陷阱 | red | `red` |
| 口诀 / 技巧 / 解题方法名 | green | `green` |
| 补充 / 备注 / 拓展 | blue | `blue` |

- **One meaning = one color, document-wide.** 结论 always purple; 易错 always red. Never mix.
- If a phrase fits two meanings, pick the primary one. A "易错结论" is primarily a 易错 → red.

## What Counts as a Key Point (anti-over-marking)

Over-marking defeats emphasis — a page full of color has no emphasis at all. The agent must mark **sparingly** by these criteria:

- **In an analysis block**: mark at most **1-2** spots — the conclusion sentence, and optionally one 易错 note or technique name. Never mark process/derivation steps.
- **In knowledge-point narrative**: mark only the **core conclusion** of each point, not the full definition. If a point has no standout conclusion, mark nothing.
- **Do not mark**: every bold word OCR already bolded, routine steps, intermediate results, definitions of basic terms.
- **When in doubt, do not mark.** An unmarked clean document is better than an over-marked noisy one. It is acceptable for a document to have few or no marks if nothing stands out.

## Quick Reference

| Context | Safe emphasis |
|---------|---------------|
| Pure text | bold, italic, OR semantic color |
| Text containing `$...$` | bold or italic only; or split and color prose parts |
| Inside a callout (`>`) | bold / italic (color span works for pure text, but keep callout content simple — prefer bold) |
| Inside HTML table cell | bold / italic; do NOT add color span around a formula cell |
| Conclusion sentence (pure text) | `<span style="color: #9370DB;">...</span>` |
| 易错 / pitfall | `<span style="color: red;">...</span>` |
| Technique / 口诀 name | `<span style="color: green;">...</span>` |
| Supplementary note | `<span style="color: blue;">...</span>` |
