# Evolution Log — scan-pdf-to-print-html

## 2026-06-15

| # | Candidate | Classify | G1 | G2 | G3 | Decision | Recurrence |
|---|-----------|----------|----|----|----|----------|------------|
| C1 | Verify body is real HTML, not raw md | wrong | pass | strengthen | principle | **strengthen** | first |
| C2 | Ordered-list numbering preserved verbatim | rework | pass | new | principle | **add_new** | first |
| C3 | CSS iteration: edit HTML directly, don't rebuild | rework | pass | new | principle | **add_new** | first |
| C4 | num-badge vs lead-tag distinguishability | style-pref | pass | new | preference-clear | **discard** (user: preference only) | first |
| C5 | th/td same font-size+weight+bg; transparent default | rework | pass | new | principle | **add_new** | first |
| C6 | No extra bottom margin in blockquote-nested blocks | rework | pass | new | principle | **add_new** (user: keep as rule) | first |
| C7 | Escape \| inside $...$ in table cells | wrong | pass | new | principle | **add_new** | first |
| C8 | Used Edge headless instead of render_html_to_pdf.py | missing | pass | duplicate | principle | **process flag** (rule already documented, was ignored) | first |
| C9 | Vector PDF is default; no heavy raster unless asked | rework | pass | new | principle | **add_new** | first |
| C10 | Image centering / avoid !important defeating it | rework | borderline | duplicate | preference | **discard** (covered by review-gate) | first |
| C11 | Title from # heading, never filename | wrong | pass | new | principle | **add_new** | first |

**Written:** DIFF A (SKILL.md), DIFF B (SKILL.md), DIFF C (references/transcript-audit-rules.md)
**Snapshot:** SKILL.md.bak-2026-06-15

## 2026-06-15 (session 2: composite-functions rework)

| # | Candidate | Classify | G1 | G2 | G3 | Decision | Recurrence |
|---|-----------|----------|----|----|----|----------|------------|
| C12 | Strip Obsidian `[!question]` callout markers from blockquotes | wrong | pass | new | principle | **add_new** | first |
| C13 | `default_title()` skipped `#` heading lines → wrong title extracted | wrong | pass | new | principle | **add_new** (builder code fix) | first |
| C14 | `PRINT_BASE_CSS` table rules overrode `table-consistent.css` (same specificity, later position wins) | rework | pass | new | principle | **add_new** (moved table-consistent after print-base) | first |
| C15 | Analysis paragraphs used `ocr-analysis` border-left box → looked like blockquote; user wanted `lead-tag` inline badge | rework | pass | new | preference-clear | **add_new** | first |
| C16 | Scan-type raster PDF: background color shift + text blur + image artifacts | rework | pass | new | principle | **add_new** (documented as not recommended) | first |
| C17 | Choice options: skill said list-only, user wanted table form too | rework | pass | new | preference | **add_new** (allow both) | first |
| C18 | 例N labels need same badge treatment as 解析, different color (#DE7356) | rework | pass | new | preference-clear | **add_new** | first |
| C19 | lead-tag CSS should be a template asset, not inline in PRINT_BASE_CSS | rework | pass | new | principle | **add_new** (assets/lead-tags.css) | first |

**Written:** DIFF D (scripts/build_faithful_handout_html.py), DIFF E (SKILL.md), DIFF F (references/transcript-audit-rules.md)
**Snapshot:** SKILL.md.bak-2026-06-15-session2

## 2026-06-17 (session: derivative/tangent markdown-source HTML + SVG cover review)

Provenance note: CAPTURE used user-pasted restored session memory plus visible current-session messages; original long-session assistant turns were not fully available, so `preceding_action` details are unverified unless otherwise stated.

| # | Candidate | Classify | G1 | G2 | G3 | Decision | Recurrence |
|---|-----------|----------|----|----|----|----------|------------|
| C20 | Markdown-source jobs with intentional full-page SVG/front cover need dedicated sheet CSS and heading page-break verification, not generic transcript image rules | rework | pass | new | principle | **add_new** | first |
| C21 | KaTeX job-local post-process needs explicit rendered verification: no page errors, KaTeX present, MathJax absent, no raw math-delimiter pagination failure | wrong/missing | pass | strengthen | principle | **strengthen** | first |
| C22 | Example/exercise labels inside blockquotes should be documented as `lead-tag-example`, including `例题` and `练习` forms, not only `例N` | rework | pass | strengthen | principle | **strengthen** | second-ish (related to C18) |
| C23 | Table template must be explicitly borderless in the main builder contract, not only transparent/same th-td styling | rework | pass | strengthen | principle | **strengthen** | second-ish (related to C14/C5) |
| C24 | Intentional side-by-side image pairs must use one authored `<figure>` or preserved adjacent crops | rework | pass | duplicate | principle | **discard/process flag** (existing rules already cover it) | second-ish (related to C10/figure policy) |

**Written:** DIFF G (SKILL.md), DIFF H (references/math-rendering.md).
**Snapshot:** SKILL.md.bak-2026-06-17.

## 2026-06-17 — run against scan-pdf-to-print-html
- candidate: Printable HTML/PDF formulas must use KaTeX HTML/font rendering by default; MathJax tex-svg is only an explicit user-requested exception.
  verdict: strengthen
  reason: Existing rules only documented a KaTeX switch/verification path while `math-rendering.md` still said MathJax tex-svg was the default, which caused visibly heavy PDF formulas.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: second (strengthens C21)

## 2026-06-19 — run against scan-pdf-to-print-html
- candidate: Final rendered HTML/PDF must reject contentless non-cover sheets, including separator-only `<hr>` / empty `.flow-block` pages.
  verdict: add_new
  reason: A real job produced a blank tenth page from `<div class="flow-block"><hr></div>`; existing rules checked overflow but not zero-content sheets.
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first
- candidate: Blockquoted Markdown formula rendering must prevent literal quote-marker `>` leakage into formula text while preserving legitimate inequalities.
  verdict: strengthen
  reason: Existing math and blockquote rules covered raw delimiters/callout cleanup but did not explicitly guard against Markdown quote prefixes entering rendered formulas.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: first

## 2026-06-20 — run against scan-pdf-to-print-html
- candidate: Non-cover A4 sheets must not end with excessive trailing blank space; enforce with `scripts/validate_sheet_bottom_margin.py`.
  verdict: add_new
  reason: A real job showed a non-cover sheet whose bottom third was blank because a display-math block could not split across pages; existing rules only rejected fully blank sheets, not sheets with large trailing blanks.
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first

## 2026-06-20 — refinement of C25
- candidate: Tighten trailing-blank threshold to 10%, exempt cover and final sheets, and exempt a sheet when the following sheet starts with a `.phycat-blockquote`.

## 2026-06-20 (session 2: blockquote math-marker leakage)
- candidate: Blockquote structural `>` markers must be stripped from interior lines of callout-embedded `$$...$$` blocks before math protection, and a standalone validator must catch any residual leakage.
  verdict: add_new + strengthen
  reason: A real job showed multi-line display math inside an Obsidian callout where every interior line still carried the blockquote prefix; `clean_markdown()` only stripped the `[!type]` marker, so the `>` prefixes were captured as part of the formula and rendered literally inside KaTeX. This requires both a builder-side strip in `build_faithful_handout_html.py` and a source-level detector.
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: second (strengthens C25)
  written:
    - `scripts/build_faithful_handout_html.py`: added `CALLOUT_DISPLAY_MATH_PATTERN` and `_strip_callout_display_math_prefixes()`; called inside `clean_markdown()` after Obsidian callout marker removal. Also tightened the existing callout-marker strip regex from `\s*` to `[ \t]*` so a marker at the end of a line no longer swallows the newline and merges with the next `> $$` delimiter line.
    - `scripts/validate_math_quote_leakage.py`: new CLI detector that reports any line inside a `$$...$$` block beginning with `>`.
    - `SKILL.md`: updated Builder Markdown Contract C25 rule, added validator command, inserted workflow step 7a (OCR path) and step 2a (markdown-source path), and listed the new validator in Files.
  snapshot: SKILL.md.bak-2026-06-20-2
  verdict: strengthen
  reason: User clarified that 35% was too loose to catch the third-sheet blank and that blockquotes must stay whole; only the following-sheet-start-blockquote case should be exempt.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: first
