# Proofreading Checklist

After auto-fix is applied but before structural formatting rewrite, run through this checklist. Each item requires active verification against the source page images.

Work through one page at a time. Mark each check as you complete it.

## Per-Page Checks

For each page in the document:

### Image Comparison
Compare the page image against the auto-fixed transcript. Look for:

- [ ] **Missing lines**: Doc2X sometimes drops entire lines at page bottom, especially formula lines, table rows, or figure captions. Scan the page image top-to-bottom and match each visible line to the transcript.

- [ ] **Missing characters**: Check that all mathematical symbols, subscripts, superscripts, and special characters are present. Common drops: `_` (subscript), `^` (superscript), `'` (prime), `\bar{...}`.

- [ ] **Heading misidentification**: Verify that page titles and section headings in the image are rendered as `#`/`##`/`###` headings in the transcript, not as plain paragraphs.

- [ ] **Formula clumping**: Check that multi-line or multi-part formulas are not merged into a single unreadable blob. Look for places where the image shows clearly separate formula lines that became one in the transcript.

- [ ] **Illegal characters inside formulas**: Scan inside `$...$` and `$$...$$` blocks for stray characters like `#`, `$`, `%`, or doubled delimiters (`$$$`).

### Text Quality

- [ ] **Chinese typos**: Check common confusable pairs:
  - `己` vs `已` vs `巳`
  - `末` vs `未`
  - `千` vs `干`
  - `人` vs `入`
  - `白` vs `日`
  - `十` vs `干`
  - `土` vs `士`
  - `午` vs `牛`

- [ ] **English/math typos**: Check for OCR confusions:
  - `l` (letter) vs `1` (number) vs `|` (pipe)
  - `O` vs `0`
  - `S` vs `5`
  - `B` vs `8`
  - `rn` → `m` (letter combination)
  - `cl` → `d` (letter combination)

- [ ] **Spacing damage**: Doc2X sometimes inserts or removes spaces around punctuation. Verify:
  - Chinese punctuation has no leading space: `正确。` not `正确 。`
  - English words have correct spacing

- [ ] **Punctuation normalization**: Doc2X may mix fullwidth/halfwidth punctuation. Normalize:
  - Chinese periods: `。` not `.`
  - Chinese commas: `，` not `,`
  - Chinese quotation marks: `""` not `""` (in Chinese context)

### Structure

- [ ] **Heading level**: The first content heading on each page should be at most `###`. Do not go deeper than `####` directly under `## Page N`.

- [ ] **Heading jump**: No heading level should jump by more than 1. Example: `##` → `####` is invalid; intermediate `###` is required.

- [ ] **Blockquote integrity**: Every `>` block that belongs together must not have a bare blank line between its lines. A blank line inside a blockquote must be `>` on its own line.

- [ ] **Choice option grouping**: All choice options (A. B. C. D.) for one question must be inside the same blockquote as the question stem.

- [ ] **Image references**: Every figure in the page image should have a corresponding image reference in the transcript. Check for missing images.

- [ ] **Table integrity**: Every table in the page image should be represented as a table in the transcript. Check for collapsed or missing tables.

## Cross-Page Checks

After all pages are individually checked:

- [ ] **Cross-page callouts**: If a callout (`> [!question]`) spans multiple pages, verify it is not split. The entire callout should be in one contiguous block.

- [ ] **Cross-page tables**: If a table spans pages, verify all rows are present and the column count is consistent.

- [ ] **Cross-page formulas**: If a display formula (`$$...$$`) spans pages in the source, verify it was not truncated at the page boundary.

- [ ] **Cross-page heading consistency**: Verify that section headings across consecutive pages maintain consistent levels. If Page 5 has `### 1.2 线面垂直`, Page 6 should not suddenly start with `####` unless it's a sub-section.

## [TO VERIFY] Markers

- [ ] Count all `[TO VERIFY: ...]` markers across the document.
- [ ] For each marker, check if the page image can resolve the uncertainty. If yes, fix and remove the marker.
- [ ] List remaining unresolved markers with their page numbers.

## Final Pass

- [ ] Read the full transcript top-to-bottom without looking at images. Does it read as a coherent document?
- [ ] Check for any lines that are garbled or clearly wrong (e.g., "asdf", "###ERROR###", binary-looking strings).
- [ ] Verify the top-level title is meaningful and describes the document content.
- [ ] Run `validate_canonical_markdown.py --check-proofreading` and fix all reported issues.
