# Analysis Block Re-typesetting

Detailed rules and subagent instructions for Step 2.5 of the main workflow. This reference is loaded when the document contains analysis/solution sections (解析/解/证明).

## Scope Boundary

This guide handles **mechanical paragraph splitting inside a single analysis block only** (排版) — turning Doc2X's one-massive-paragraph dump into readable logical paragraphs and fixing OCR typos within it.

The **whole question-block structure** (题干 → callout, 选项 → table, 子问 → own lines, 解析 → paragraphs, displaced-sentence repositioning) is a separate concern, handled by **Step 2.7 + `question-block-rewrite-guide.md`**. Do not conflate the two: Step 2.5 re-typesets paragraphs; Step 2.7 rewrites the block structure against the raw transcript. When a subagent is dispatched for Step 2.5 and the block it touches is part of a question block, the structural rewrite belongs to Step 2.7 — coordinate so the two steps do not duplicate or conflict.

## When to Use

- **≤ 3 examples**: do it inline (read and edit each analysis block yourself)
- **> 3 examples**: dispatch subagents (parallel, 3-5 examples per subagent)

Doc2X dumps each analysis section as one massive unbroken paragraph. Re-typeset each block into clean, readable, logically-structured paragraphs — and fix OCR typos and garbled text within the analysis.

## Re-typesetting Rules

### 1. Split at logical break points

Never leave a single paragraph with multiple reasoning steps:

- Punctuation breaks: `。` `；` `：`
- Method boundaries: `法一` / `法二` / `法三`, `方案一` / `方案二`, `①` `②` `③`
- Logic transitions: `故`, `所以`, `因此`, `又因为`, `此时`, `综上`, `于是`
- New variable introductions: `令`, `设`, `则`, `即`, `由`
- New formula blocks: each `$$...$$` display formula gets its own paragraph break before and after

### 2. Maximum paragraph length

No analysis paragraph exceeds 300 characters (formula content excluded from the count). Pure formula lines (`$$...$$` blocks, `\begin{aligned}` blocks) are exempt.

### 3. Fix OCR typos within analysis

- Correct confusable characters: `已`/`己`/`巳`, `人`/`入`, `末`/`未`, `千`/`干`, `土`/`士`
- Fix broken sentences where Doc2X merged or split words
- Normalize punctuation: Chinese `。，；：` not English `.,;:` in Chinese text
- Fix garbled or nonsensical phrases by comparing against the page image

### 4. Formula integrity verification (MANDATORY after each chunk)

After re-typesetting each analysis block or chunk, verify:

1. **Delimiter balance**: every `$...$` pair is balanced — count of `$` must be even within the chunk
2. **No formula splitting**: no `$` or `$$` delimiter was accidentally placed at a paragraph break boundary
3. **`\begin{array}` intact**: all `\begin{array}...\end{array}` blocks remain on their own lines, unchanged
4. **No unauthorized conversions**: `\begin{array}` was NOT converted to `\begin{cases}` or any other construct
5. **`$` count preserved**: total `$` count in the chunk must match before and after re-typesetting

Run these verification commands after subagents complete:
```bash
# Verify delimiter balance
rg -c '\$' source-transcript.md   # must be even number

# Verify no begin{cases} introduced
rg -c '\\begin\{cases\}' source-transcript.md   # must match raw transcript count

# Verify begin{array} count unchanged
rg -c '\\begin\{array\}' source-transcript.md
rg -c '\\begin\{array\}' doc2x/page-transcript.raw.md
# source count must be >= raw count (additional arrays may come from manual formatting)
```

## Subagent Instructions Template

For each chunk of 3-5 examples, dispatch a subagent with this prompt:

```
You are re-typesetting analysis blocks in a math transcript. For each **解析** / **解** / **证明** section in your assigned line range:

1. READ the entire analysis block carefully.
2. SPLIT long paragraphs at logical break points:
   - Punctuation: 。 ； ：
   - Method boundaries: 法一/法二/法三, 方案一/方案二, ①②③
   - Logic transitions: 故, 所以, 因此, 又因为, 此时, 综上
   - New formula introductions: 令, 设, 则, 即
   - Each resulting paragraph should be ≤ 300 characters (formulas excluded from count)
3. FIX OCR errors and garbled text:
   - Correct obvious typos: 已/己/巳, 人/入, 末/未, 千/干
   - Fix broken sentences where Doc2X merged or split words incorrectly
   - Fix punctuation: ensure Chinese commas 。，；： not English .,;:
   - DO NOT change mathematical content or formula structure
4. VERIFY formula integrity (MANDATORY — failure here is a critical error):
   a. Every `$...$` delimiter pair is balanced — count `$` before and after your edits
   b. No formula was accidentally split or merged during paragraph splitting
   c. `\begin{array}` blocks remain intact and on their own lines
   d. You did NOT convert `\begin{array}` to `\begin{cases}` or vice versa
   e. You did NOT add or remove any `$` or `$$` delimiter
5. DO NOT:
   - Change any formula content
   - Convert `\begin{array}` to `\begin{cases}` or vice versa
   - Add or remove mathematical steps
   - Summarize or condense the analysis
   - Use scripts/regex — read and edit manually

After editing, REPORT:
- Number of paragraphs before and after re-typesetting
- `$` count before and after (must match)
- Any formula integrity issues found and fixed

Output: the edited lines with clean paragraph breaks and fixed typos.
```

## Post-Assembly Verification

After all subagents complete and chunks are assembled:

1. Verify the total `\begin{array}` count in assembled file >= raw transcript count.
2. Verify the total `$` count is even (balanced delimiters).
3. Run `rg -c '> \[!question\]'` — callout count must be unchanged.
4. Check that no analysis paragraph exceeds 300 characters (excluding pure formula lines).
5. Run Step 1-GATE checks on the assembled document.
