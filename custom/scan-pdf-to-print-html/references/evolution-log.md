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
