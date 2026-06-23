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

## 2026-06-20 — run against scan-pdf-to-print-html
- candidate: Rendered question/example blockquotes must hard-verify `lead-tag-example` badges, the left accent rule, neutral option-table styling distinct from non-blockquote data tables, and readable option images.
  verdict: strengthen + add_new
  reason: A real markdown-source handout regressed twice: first the question blockquote style lost the expected left accent treatment, then a global table fix incorrectly added borders/background to question option tables and shrank option images. Existing rules documented lead badges and transparent tables, but the review gate did not enforce them as browser-DOM checks and did not distinguish blockquote option tables from non-blockquote data tables.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: second-ish (strengthens C18/C23 and review-gate table/image checks)
  written:
    - `SKILL.md`: added a rendered-output hard contract for question/example blockquotes, lead badges, neutral option tables, and readable option images; updated Markdown-Source Mode validation to run the new rendered contract validator; strengthened the Builder Markdown Contract and file list.
    - `references/review-gate.md`: added `validate_rendered_handout_contract.py --html handout.html` and explicit reviewer checks for lead badges, blockquote left rule, option table neutrality, `th`/`td` parity, readable option images, and non-blockquote data-table distinction.
    - `scripts/validate_rendered_handout_contract.py`: new Playwright DOM validator scoped to `#handout-print-root`.
    - `tests/test_validate_rendered_handout_contract.py`: regression tests for accepting neutral option tables and rejecting ruled option tables/tiny images.
  snapshot: SKILL.md.bak-2026-06-20-3

## 2026-06-22 — run against scan-pdf-to-print-html
- candidate: Rendered `.phycat-blockquote` left-rule validation must reject flattened 1px/plain/same-color box borders while preserving legitimate visible accent-rule variants.
  verdict: strengthen
  reason: A real handout had `.phycat-blockquote` flattened by a later generic blockquote rule into `border: 1px solid var(--line)`, but the rendered validator only checked for a nonzero/non-none left border and falsely passed it. The rule now requires computed-style validation and paired pass/fail regression coverage so the validator catches the miss without false positives on valid accent rules.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: second-ish (strengthens the 2026-06-20 rendered blockquote contract)
  written:
    - `SKILL.md`: strengthened the hard contract, Builder Markdown Contract, and file list to require computed left-accent validation that rejects flattened/plain boxes without rejecting valid `.phycat-blockquote` variants.
    - `references/review-gate.md`: clarified that the left accent rule must be visible as a computed accent rule, not a generic 1px/plain/same-color box border.
    - `scripts/validate_rendered_handout_contract.py`: already tightened before this evolution write to measure border width/color/background/plain-box state.
    - `tests/test_validate_rendered_handout_contract.py`: already added a regression fixture for flattened 1px/plain box borders while retaining passing neutral table/blockquote coverage.
  snapshot: SKILL.md.bak-2026-06-22

## 2026-06-22 — run against scan-pdf-to-print-html
- candidate: Rendered full-page cover/special sheets must align with regular A4 sheets in screen preview, enforced by the rendered contract validator with narrow marked-cover scope.
  verdict: strengthen
  reason: A real handout used `.concept-map-sheet { margin: 0 }` while regular `.sheet` pages were centered, so the browser preview showed the cover left-aligned and page 2 centered; existing cover rules checked first-page fill and no shrinkage but did not compare the cover sheet frame against regular sheets. The validator now compares marked cover/special sheets to the first regular sheet by rendered `left` and `width` with a 2px tolerance, and regression tests ensure it catches the margin mismatch without failing ordinary no-cover handouts.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: second-ish (strengthens C20 full-page cover verification)
  written:
    - `SKILL.md`: added a hard contract and markdown-source validation language for marked cover-vs-regular sheet screen alignment.
    - `references/review-gate.md`: added the same marked-cover alignment check to the known failure classes, explicitly excluding unmarked ordinary pages and print-mode zero margins.
    - `scripts/validate_rendered_handout_contract.py`: added Playwright `getBoundingClientRect()` comparison for `.concept-map-sheet`, `[data-sheet-role="cover"]`, and `[data-cover-sheet="true"]` against the first regular `.sheet`.
    - `tests/test_validate_rendered_handout_contract.py`: added fail/pass fixtures for left-aligned cover margin and no-cover handouts.
  snapshot: SKILL.md.bak-2026-06-22-2

## 2026-06-23 — run against scan-pdf-to-print-html

Provenance note: CAPTURE ran in the main orchestrating context from visible current-session user messages; trace enrichment tagged `(extracted)`. No long-session reconstruction.

| # | Candidate | Classify | G1 | G2 | G3 | Decision | Recurrence |
|---|-----------|----------|----|----|----|----------|------------|
| C26 | Add rendered image width upper-bound gate driven by aspect-ratio bands (portrait ~20% / square ~35% / landscape 50-80% in three sub-bands); gate checks post-render only, builder mm clamp unchanged | missing | pass | new | principle | **add_new** | first |
| C27 | Add rendered adjacent-image side-by-side detection gate scoped to builder-clustered `.ocr-image-cluster` and authored `<figure>`; verify grouped images are not vertically stacked via getBoundingClientRect | missing | pass | strengthen | principle | **strengthen** | second (same substance as 2026-06-17 C24; that discard was an `ignored`-diagnosis process gap — rules existed with no executable gate; now closed) |
| C28 | Add optional Markdown image-hosting workflow step (invoke `piclist-upload` skill's `migrate-md-images.ps1` against a `source-transcript.md` copy) + HTML-local-image-only gate (`--disallow-remote-images`, OFF by default, auto-on during image-hosting step); HTML keeps local paths to avoid unstable remote reads during render/PDF | missing | pass | new | principle | **add_new** | first |

Pairwise conflict check: C26 vs C27 (width vs layout) complementary; C26 vs C28 (width vs URL) unrelated; C27 vs C28 unrelated. No conflicts. C26 internally merges the user's two width requests (#1 absolute upper-bound + #3 aspect-ratio bands) into one gate to avoid two competing width checks.

User decisions (AskUserQuestion, 2026-06-23):
- Width strategy: gate checks only, builder mm clamp unchanged → fix via job-local CSS.
- Side-by-side scope: only `.ocr-image-cluster` and `<figure>` (low false-positive).
- Image-hosting scope: scan skill adds workflow step calling `piclist-upload`; does not reimplement upload.
- Landscape bands: aspect 1-1.5→50%, 1.5-2.5→65%, >2.5→80%.
- `--disallow-remote-images` default OFF; auto-on during image-hosting workflow step.

- candidate: C26
  verdict: add_new
  reason: Existing rules only covered choice-table-image readable-minimum (SKILL.md:132) and a "no tiny crop as full-width" semantic ban (working-contract.md:72); no general rendered width gate, no aspect-ratio policy. Builder uses fixed mm clamp (34/48/64/72mm) classified by max(width,height), not aspect ratio.
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first
- candidate: C27
  verdict: strengthen
  reason: 2026-06-17 C24 discarded the same substance as "existing rules already cover it / was ignored", but those (figure-policy.md:39, review-gate.md:18, working-contract.md:42/70, page-fragment-worker.md:87) were builder instructions with NO post-render DOM check. This upgrades the rule to an executable getBoundingClientRect gate.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: second (matches C24 substance; that discard mis-diagnosed an `ignored` gap as `duplicate`)
- candidate: C28
  verdict: add_new
  reason: No image-hosting logic existed in scan skill. User confirmed `custom/piclist-upload` skill already implements upload+migration (path 4 `migrate-md-images.ps1`, handles Doc2X `?x=&y=&w=&h=` query params). Structural change routed through human_review per Step 6; user confirmed scope = workflow step + gate, scan skill does not reimplement upload. `--disallow-remote-images` default OFF to avoid blocking existing jobs that still reference Doc2X CDN crops.
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first

Dev Eval: validator-equipped skill. Candidates are `missing`-class new features with no corrected output to lint → Dev Eval N/A for semantic novelty. BUT full existing test suite run as non-regression check:
- `python3 -m pytest tests/test_validate_rendered_handout_contract.py -q` → 5 passed
- `python3 -m pytest -q --ignore=tests/test_crop_page_bodies.py` → 96 passed (test_crop_page_bodies.py collection error is a pre-existing missing-PIL dependency, unrelated to this change)
New-flag defaults verified compatible with existing fixtures (width/side-by-side gates default ON but fixtures have no violating images; remote gate default OFF).

written:
  - `SKILL.md`: added 3 Hard Contract items (image width band, side-by-side, image-hosting workflow + local-only HTML), added Markdown-Source Mode step 8 (optional image-hosting via piclist-upload), updated Files entry for validate_rendered_handout_contract.py.
  - `references/figure-policy.md`: appended "Rendered Image Width Contract" (band table) and "Rendered Adjacent-Image Side-by-Side Contract" sections.
  - `references/review-gate.md`: strengthened item 12 with rendered image contract failure classes (width band, side-by-side, local-only-when-image-hosted).
  - `scripts/validate_rendered_handout_contract.py`: added 4 CLI flags (--check-image-width-bands/--no-, --check-adjacent-side-by-side/--no-, --disallow-remote-images, --remote-image-allowlist), extended validate() signature, added 3 JS collectors (widthBandViolations, stackedPairs, remoteImageSrcs), added 3 Python checks.

snapshot: SKILL.md.bak-2026-06-23, references/figure-policy.md.bak-2026-06-23, references/review-gate.md.bak-2026-06-23, scripts/validate_rendered_handout_contract.py.bak-2026-06-23

## 2026-06-23 (session 2) — figure width/grouping rule evolution (rescan of ch03-conic-properties)

Provenance note: CAPTURE ran in the main orchestrating context from visible current-session user messages; trace enrichment tagged `(extracted)`. Most scan-side changes were already written inline during the session; this entry records them and the residual analysis.

| # | Candidate | Classify | G1 | G2 | G3 | Decision | Recurrence |
|---|-----------|----------|----|----|----|----------|------------|
| C29 | Image width target must be a SMOOTH function of aspect ratio (no hard jump at 1.1), capped by each image's own natural width (no upscaling past native res). Near-square (ar≈1) → ~30%, not 50%. | rework | pass | strengthen (redesigns C26) | principle | **strengthen** (written inline) | second (redesigns same-day C26) |
| C30 | Multi-image `<figure>`/cluster rows: EACH sibling judged independently against its OWN band (per-image), NOT by aggregate row width. A row does NOT justify enlarging each sibling to fill it. | rework | pass | strengthen | principle | **strengthen** (written inline) | second (refines C26/C27) |
| C31 | Oversubscribed rows (siblings' independent widths sum >100% of body): prefer staying ONE row over wrapping — proportional shrink to ~95% + `flex-wrap:nowrap` + EXEMPT the independent-width rule for that group. | rework | pass | new | principle | **add_new** (written inline) | first |
| C32 | C27 side-by-side gate must allow `flex-wrap:wrap` wrapping (multi-row layout) inside flex containers — wrapping to a 2nd row is normal, NOT a "stacked" failure. Only flag `display:block` single-column collapse. | rework | pass | strengthen | principle | **strengthen** (written inline) | second (refines C27) |
| C33 | Job-local balance hook should split OL/UL candidate blocks by `<li>` when the block is too tall to move whole (extends the existing split logic beyond multi-child divs). | missing | pass | strengthen | principle | **strengthen** (written inline) | first |

Session rework trace (user messages, chronologic):
1. "为什么感觉这个大小还是过大了...感觉 50 就有点太多了，这个大小在30-35之间比较合适" → C29 redesign (smooth target).
2. "如果最大宽度比图片宽，那么就按照图片宽度就行了。你来重新设计这个区间宽度" → C29 natural-width cap.
3. "合并的图的宽度，也是每个图按照各自的分配逻辑来限制宽度，而不是强行弄到和总宽差不多" → C30 per-image independent.
4. "如果超过100% 还是并成一排，但是可以豁免独立宽度规定" → C31 oversubscription exemption.
5. "47/49/52/62 页相邻图没并排" + "md 格式错误?" → root cause traced UPSTREAM to rewrite skill (rule existed, no gate) — that fix is recorded in rewrite-doc2x-markdown's evolution-log. On the scan side, C32 was the residual (allow flex-wrap multi-row).
6. "在这种技能冲突的情况下，可以权衡一下，如果图片宽度差不多，或者底部留白差不多，那就豁免" → reinforced the figure-boundary trade-off exemption (already added earlier this date) + the "near-is-exempt" tolerance on width bands.

Cross-skill note: the split-figure root cause (user messages #5) lived in rewrite-doc2x-markdown, not scan. The scan skill's C27 could not catch it because the images were never grouped. This is the recurring "rule exists, no executable gate" failure mode (cf. C24→C27 on 2026-06-17/23). The rewrite-side gate added this session closes it at the source.

Dev Eval: scan skill validator changes were exercised inline during the session — `validate_rendered_handout_contract.py` 14/14 PASS (`checked=99 violations=0`, `stackedPairs=0`), `validate_sheet_bottom_margin.py` PASS, on the final corrected handout.

Written (inline during session, recorded here):
- `scripts/validate_rendered_handout_contract.py`: C26 redesigned to smooth-target + natural-width cap; C30 per-sibling check; C31 oversubscription exemption; C32 flex-wrap allowance in C27; `capBand` returns target.
- `scripts/validate_sheet_bottom_margin.py`: figure-boundary `imgBandOk` simplified to per-image (dropped aggregate), uses same smooth-target + cap.
- `references/figure-policy.md`: redesigned width contract (smooth control points, per-image, oversubscription exemption, flex-wrap allowance).
- `SKILL.md`: width-band hard contract rewritten (smooth target, per-image, oversubscription exemption, flex-wrap).
- job-local `handout.html` (ch03-conic-properties): balance hook enhanced to split OL/UL by `<li>` (C33) — this is a job-local edit, pattern to consider folding into the builder if it recurs.

snapshot: SKILL.md.bak-2026-06-23, references/figure-policy.md.bak-2026-06-23, references/review-gate.md.bak-2026-06-23, scripts/validate_rendered_handout_contract.py.bak-2026-06-23 (created during the earlier same-day run; this session-2 run made further edits on top).

Discarded candidates (this session):
- "禁止 [!note] '已在上面保留，不重复抄录' 占位符" — Gate 1 borderline (single-document content judgment). User removed the element from this job but did not generalize it into a scan-skill rule. Not written.

## 2026-06-23 (session 3: dormant-postprocess activation)

**Session trigger:** User reported three defects when using the scan skill: (1) example blocks had no quote styling (`.phycat-blockquote`), (2) a root-level SVG was not used as the homepage cover, (3) chapter `##` headings (except the first) did not start on a fresh sheet and the previous page's blank space was not exempted. User asked why "using the skill" did not enforce these, and requested strengthening the skill.

**Root cause (the unifying finding):** All three capabilities already EXISTED in code — `postprocess_handout_for_contract.py` implemented `ensureExampleQuote()`/`mergeExampleRuns()` (example wrap), `inject_cover_metadata()`/`injectConceptCover()` (SVG cover), and `paginateHandout()` (forced pagination). But SKILL.md's Markdown-Source Mode workflow (8 steps) NEVER listed postprocess as a step, and the Files section did not register the script. So a model following the workflow ran `build_faithful_handout_html.py` and stopped — silently skipping every dormant capability. This is the same "rule exists, no executable gate / dormant code" failure mode as C24/C27 (figure grouping) traced earlier this date.

| # | Candidate | Classify | G1 | G2 | G3 | Decision | Recurrence |
|---|-----------|----------|----|----|----|----------|------------|
| C34 | Add postprocess as mandatory Markdown-Source step 3 | missing | pass | new (grep: postprocess not in workflow steps) | principle | **add_new** | first (same dormant-code class as C24/C27) |
| C35 | Register postprocess + new gate in Files section | missing | pass | strengthen | principle | **strengthen** | first |
| C36 | Widen `isLectureHeading` + add `isChapterBreakHeading` for chapter h2 pagination | rework | pass | strengthen (lecture-break framework existed, too narrow) | principle | **strengthen** | first |
| C37 | Exempt trailing-blank when next sheet starts with chapter h2 | rework | pass | strengthen (extends existing 3 exemptions) | principle | **strengthen** | first |
| C38 | New `validate_example_blockquote_coverage.py` pre-build gate | missing | pass | new | principle | **add_new** | first |

Session rework trace (user messages, chronologic):
1. "生成的HTML的例题却没有引用块，还有就是...没有使用 svg...二级标题（除了第一个外）应该从新的一页开始，而且他的上一页能够豁免空白" → three defects, traced to dormant postprocess (C34/C35) + narrow pagination (C36/C37) + missing pre-build gate (C38).
2. User decisions (via AskUserQuestion): pagination-priority + blank-exempt (C36/C37 direction); scan adds front gate AND upstream rewrite strengthened (C38 + rewrite side); SVG defaults to auto-use as cover (no code needed — inject_cover_metadata already keys on `concept-map.svg` fixed name, which user confirmed is always the cover's name).

**Written this session:**
- `scan-pdf-to-print-html/SKILL.md`: added step 2b (`validate_example_blockquote_coverage.py`), step 3 (mandatory postprocess — the core root-cause fix), renumbered 3→4...8→9; Files section now registers `postprocess_handout_for_contract.py` and `validate_example_blockquote_coverage.py`; step 6 exemption list adds chapter-h2.
- `scan-pdf-to-print-html/scripts/postprocess_handout_for_contract.py`: `isLectureHeading` regex widened (章/节/篇/单元/部分); new `isChapterBreakHeading()` (单元N, numeric outline, Module/Lesson/Chapter); pagination branch now triggers on `isLectureHeading || (h2 && isChapterBreakHeading)`.
- `scan-pdf-to-print-html/scripts/validate_sheet_bottom_margin.py`: new `nextStartsWithChapterH2` exemption (4th exemption, OR-joined with blockquote/lecture/figure).
- `scan-pdf-to-print-html/scripts/validate_example_blockquote_coverage.py`: NEW pre-build gate (line-by-line in_quote state machine, 例题/练习 + mandatory number regex, excludes 例如/举例).
- `rewrite-doc2x-markdown/references/canonical-markdown-rules.md`: new Hard rule (example/exercise labels must live in a callout; analysis stays out).
- `rewrite-doc2x-markdown/SKILL.md`: new Check 7 (run validator's `lint_bare_question_starts`).

**Concurrency event (IMPORTANT):** During this session, another process/session modified `rewrite-doc2x-markdown/scripts/validate_canonical_markdown.py` concurrently, adding `BARE_QUESTION_START_PATTERN` + `lint_bare_question_starts` + `lint_qa_ordering` interstitial-content guard. This is functionally the same lint I planned to add (4c). The concurrent implementation is sound (syntactically valid, functional, correctly scoped to `[!question]` callouts, has heading/quote guards) and was verified by running it against a fixture. I accepted it rather than adding a duplicate. Minor known edge: a bare `例题N 的解析` paragraph (analysis that happens to start with the example label) gets flagged as a missing callout wrap — acceptable in practice (analyses normally start with 解析：). User was informed.

**Snapshots (behavior-changing writes):**
- `scan-pdf-to-print-html/SKILL.md.bak-2026-06-23-2`
- `scan-pdf-to-print-html/scripts/postprocess_handout_for_contract.py.bak-2026-06-23`
- `scan-pdf-to-print-html/scripts/validate_sheet_bottom_margin.py.bak-2026-06-23`
- `rewrite-doc2x-markdown/SKILL.md.bak-2026-06-23-2`
- `rewrite-doc2x-markdown/references/canonical-markdown-rules.md.bak-2026-06-23-2`
- `rewrite-doc2x-markdown/scripts/validate_canonical_markdown.py.bak-2026-06-23-2` (pre-concurrent-change snapshot; the concurrent process's edits landed on top of the live file, not on this snapshot)

**Verification Ceiling note:** This session reduced the trust surface by converting three dormant capabilities into explicit workflow commands (step 2b, step 3) plus a pre-build gate (C38) plus a widened validator (C37). It does NOT eliminate model self-discipline dependence — if a model skips step 3 entirely, the defects recur. Dev Eval below checks non-regression only, not behavior.

**Dev Eval (non-regression, run after writes):**
- `validate_sheet_bottom_margin.py` on existing `product/2026-06-19-mst-ch04-multi-select-methods/handout.html`: caught a **bug in this session's own edit** during Dev Eval — the initial `nextFirstChild.tagName === 'H2'` check never fired because the builder wraps every block in a `<div class="flow-block">`, so the chapter `<h2>` sits inside the wrapper, not as a direct sheet-body child. Fixed by adding `firstContentChildIsH2()` helper that looks one level inside the flow-block. After the fix: Sheet 19 (94.8% blank, next=第二节 h2) and Sheet 31 (39.6%, next=第三节 h2) correctly exempted; Sheet 39 (19.5%, next=解法 continuation, not a chapter) correctly stays a violation. This is exactly the user-requested "chapter h2 → exempt previous page's blank" behavior. Pre-existing violations (Sheet 39 image-width) unchanged.
- `validate_rendered_handout_contract.py`: no new violation categories introduced (stackedPairs=0, remoteImageSrcs=[]); one pre-existing image-width-band finding on this job, unrelated to this session's changes.
- Node `--check` + functional test of the widened `isLectureHeading`/`isChapterBreakHeading` regexes: 14/14 cases pass, including the regression guard `第3讲 → true` (original behavior preserved) and all new shapes (第N章/节/篇/单元, 单元N, N.中文, Module/Lesson/Chapter N). Caught and fixed a CJK `\b` boundary bug: the original `/^第…讲\b/` silently failed on `第3讲` because `\b` does not fire after a CJK character — replaced with a delimiter/`$` group.

**This session's Dev Eval caught two real bugs in this session's own edits** (the `\b` CJK regression in postprocess, and the flow-block-wrapper gap in the validator) — strong evidence that the write-then-verify discipline works, even though the verification is lint-level not behavior-level.

## 2026-06-23 (session 4: lightweight regression evals)

**Session trigger:** User noted the skill has a high bug rate and asked for evals. Also noted a recurring pain: "重复造轮子" — many tools the model can't just reuse, it has to build its own, wasting tokens and time. Decision: build evals first (the high-bug-rate defense), defer the wheel-reinvention problem to be data-driven by eval results later.

**Reference consulted:** skill-creator (`external/anthropics-skills/skill-creator/SKILL.md`) — its core thesis is "draft → run test cases → review → improve", and "if all 3 test cases independently wrote the same helper, bundle it as a script". This session applied the *run-test-cases* half (programmatic, no subagents) and deferred the *subagent-benchmark* half to big-version checkups. Chose lightweight programmatic eval over skill-creator's full flow to avoid the token/time cost the user flagged — the full flow spawns multiple claude processes per iteration.

| # | Candidate | Classify | G1 | G2 | G3 | Decision | Recurrence |
|---|-----------|----------|----|----|----|----------|------------|
| C39 | Add lightweight regression evals for the 3 high-bug areas | missing | pass | new | principle | **add_new** | first |

**Why this isn't overfit (Gate 1 pass):** the 3 evals cover the 3 capability areas that produced this session's defects (example blockquote, SVG cover, chapter pagination) — but they generalize: any future edit to postprocess/build/validate logic in those areas trips them. The fixtures are static and minimal; the contracts asserted (no bare example `<p>`, cover sheet marking, chapter pagination) are the skill's permanent output contracts, not single-document quirks.

**Written this session (all NEW files, no existing script modified — avoids conflict with concurrent codex edits):**
- `evals/evals.json` — 3 eval cases, schema-compatible with skill-creator (`skill_name`, `evals[].id/name/fixture/expectations`).
- `evals/fixtures/examples.md` — choice example + proof example + deliberately-bare example (tests both postprocess auto-wrap AND the pre-build gate).
- `evals/fixtures/chapter-breaks.md` — three 第N章 chapters with enough body to each fill content.
- `evals/fixtures/with-cover.svg` — minimal 210×297 viewBox SVG (named concept-map.svg at runtime to trigger inject_cover_metadata).
- `evals/run_programmatic_eval.py` — runner: per eval, copy fixture to temp job dir → build → postprocess → Playwright DOM assertions. No subagents, no LLM grading. Exit code = failed assertion count.
- `SKILL.md` — new `## Regression Evals` section (when to run, how to run, coverage, relationship to skill-creator full flow, verification ceiling).

**Dev Eval (the eval validating itself — ran the suite 3 times during dev):**
- First run: eval 1 passed but with a flawed assertion ("wraps all N labels" used `>= label_count` where label_count was undercounted because the source regex missed callout-title labels). The `>=` mask hid it. Caught only when I broadened the count regex and got 4 labels vs 3 blockquotes → false FAIL.
- Root cause: "label count" ≠ "example count" (one example references its own label mid-prose), and `mergeExampleRuns` can combine adjacent examples. The count-match contract was wrong.
- Fix: rewrote the assertion to the *real* contract — "zero bare example `<p>` OUTSIDE any `.phycat-blockquote` ancestor". This is postprocess's actual job. After fix: 7/7 PASS, exit 0.
- eval 2 initial bug: dispatch passed 3 args to a 2-arg function (signature parity miss). Fixed by making `assert_cover_injection` accept `fixture_md` (unused, for parity).
- Final full run: 7/7 PASS, exit 0. Evidence per assertion prints concrete DOM state (blockquote counts, cover class/role, chapter-h2 sheet mapping).

**Concurrency note:** codex is editing this skill in parallel (SKILL.md, postprocess_handout_for_contract.py changed mid-session). The eval runner only INVOKES existing scripts via subprocess (never imports/edits them), so it is robust to codex's refactors — and if codex breaks cover injection or pagination, this eval goes red immediately. That is precisely the eval's value.

**Verification ceiling:** the eval catches code-logic regressions (regex too narrow, exemption missing, cover injection broken, pagination off). It does NOT catch model-behavior regressions (model skips step 3). The user's "high bug rate" pain is mostly code-logic regressions (silent, hidden behind apparently-correct markdown rules), so this directly targets it.

**Deferred (the "重复造轮子" pain):** not addressed this session per user decision ("暂不处理，先看 evals 数据"). Once evals accumulate failure patterns, the data will show which validate scripts overlap and could merge — that's the evidence-driven path to reducing script proliferation, rather than guessing now.

**No snapshot needed this session:** all writes were NEW files (evals/*) plus a NEW section appended to SKILL.md. No existing behavioral reference file was modified, so no `.bak` required. (SKILL.md was already snapshotted earlier today as bak-2026-06-23-2; codex's concurrent edits landed on the live file.)

## 2026-06-23 (session 5: post-codex regression caught + eval negative case)

**Session trigger:** Codex finished its parallel work on this skill. Ran the new programmatic evals (session 4) to verify codex's changes didn't break the three contracts — evals passed 7/7. Then ran the project's existing pytest suite (`tests/`) for a full regression check across both agents' merged changes. pytest caught 1 failure that evals missed.

**The regression (real, introduced by session 3's C37):**
- `tests/test_validate_sheet_bottom_margin.py::test_bottom_margin_rejects_same_blank_without_lecture_marker` FAILED.
- The test fixture has sheet 3's first content as `<h2>大招 2</h2>` (a NON-chapter-shaped h2) and sheet 2 with NO `data-ends-before-lecture` marker. The test expects the validator to REJECT sheet 2's blank (returncode 1).
- Session 3's C37 added `nextStartsWithChapterH2` exemption via `firstContentChildIsH2(nextFirstChild)`, which returned true for ANY h2 — including "大招 2". So the exemption fired incorrectly and the validator returned 0 (PASS) instead of 1 (FAIL).
- Root cause: the exemption was too broad. User's actual requirement (session 3 AskUserQuestion) was "二级标题（除第一个外）应该从新的一页开始" for CHAPTER headings, not arbitrary h2. A generic exposition h2 like "大招总结" or "补充说明" must NOT escape the trailing-blank check.

**Why evals missed it but pytest caught it (the two-layer defense working as designed):**
- Session 4's eval 3 only had POSITIVE assertions (chapter h2 → marked). It never tested the NEGATIVE case (non-chapter h2 → NOT marked). So the over-broad exemption looked correct to evals.
- pytest's unit test specifically constructed the "大招 2" edge case — exactly the kind of targeted unit-level boundary that end-to-end evals under-test.
- This is the complementary value of BOTH layers: evals catch end-to-end contract breaks (did the whole pipeline produce a cover? did examples get wrapped?), pytest catches narrow logic-precision regressions (does this specific input produce this specific boolean?).

**Fix (this session):**
- `validate_sheet_bottom_margin.py`: replaced `firstContentChildIsH2` (returns bool for any h2) with `firstContentH2` (returns the h2 element) + `isChapterShapedText` (text check, regex synced with postprocess's `isLectureHeading`+`isChapterBreakHeading`, no `\b` — CJK boundary bug from session 3). Exemption now requires the next sheet's first h2 to be chapter-SHAPED, not just any h2. Snapshot: `validate_sheet_bottom_margin.py.bak-2026-06-23-3`.
- `evals/fixtures/chapter-breaks.md`: added a non-chapter `## 大招总结` section.
- `evals/run_programmatic_eval.py` + `evals/evals.json`: added Assertion C (NEGATIVE) to eval 3 — verifies a non-chapter h2 does NOT cause a false `ends-before-lecture` mark on its predecessor. This closes the eval gap so a future re-widening of the exemption is caught by evals too, not only pytest.

**Verification (both layers green after fix):**
- pytest: 102 passed (was 101 passed / 1 failed before fix).
- evals: 8/8 PASS (was 7/7; added the negative assertion).

**Lesson (folds back into the skill-evolution Quick Gate as a recurring class):** positive-only test coverage is a known blind spot — "does the thing work when it should" is tested, "does the thing NOT fire when it shouldn't" is not. Session 4's eval design repeated this mistake. The fix (add the negative case) is general: every exemption/trigger rule needs both a positive fixture (triggers correctly) and a negative fixture (does not trigger on near-miss input). This applies to the other two evals too, but they were less exposed because their contracts are "no bare X" (already negative-shaped). Eval 3's "chapter h2 → exempt" was positive-shaped, hence the gap.

**Concurrency:** codex's changes to SKILL.md, postprocess, render_html_to_pdf, working-contract, and rewrite references all merged cleanly with session 3-4 edits. No conflict. The evals (which only subprocess-invoke scripts) verified codex's refactors preserved the three contracts. This is exactly the "guard other agents' changes while you're away" value proposition of the eval suite.

## 2026-06-23 (session 6: fixing the first reusable wheel — playwright context)

**Session trigger:** User asked "what wheels are worth fixing" — repeating tools that future work could reuse instead of rebuilding. Decision: act now, fix one wheel. This session fixed wheel #2 (Playwright handout-rendering context), the most clearly duplicated of the three candidates.

**Why this wheel first (data-driven, from session 5 inventory):**
- 3 scripts each copy-pasted the launch+wait sequence: `render_html_to_pdf.py`, `validate_rendered_handout_contract.py`, `validate_sheet_bottom_margin.py`.
- The copies had drifted: viewport 794×1123 vs 1440×1123 vs configurable; handoutReady wait strict (`=== 'true'`) vs lenient (`!dataset || === 'true'`); timeout 60s vs 120s; one listens to console errors, others don't.
- Session 5's bugs (CJK `\b`, flow-block wrapper gap) were spread across these copies — a fix in one didn't propagate. This is the textbook "duplicate code drifts" cost.

**The wheel (NEW file):** `scripts/handout_browser.py` — a single `open_handout()` context manager that parameterizes every drift axis (viewport, collect_errors, strict_ready, timeouts, settle_ms) and yields `(page, errors)` inside a `with` block that auto-closes the browser. Importable AND directly runnable as a smoke test (`python3 handout_browser.py handout.html`).

**Refactor (3 scripts now call the wheel instead of inlining):**
- `validate_sheet_bottom_margin.py`: 26 lines of launch+wait → 1 `open_handout(...)` call. Bonus: fixed a `SyntaxWarning` (invalid `\s` escape in the JS string I added in session 5's C37 — `\s` → `\\s` so Python emits `\s` for JS; behavior unchanged, warning gone, future-proof).
- `validate_rendered_handout_contract.py`: 33 lines → 1 call. Output diff against the pre-refactor snapshot = **identical** (byte-for-byte), exit code identical (1 on the test handout's pre-existing image-width violation).
- `render_html_to_pdf.py`: 18 lines + redundant import-check block → 1 call. Verified by generating a real 6.5MB PDF + 7.7MB screenshot.

**The import-path gotcha (caught by pytest, fixed inline):**
- After the refactor, `tests/test_render_html_to_pdf.py::test_playwright_render_skips_when_browser_not_available` FAILED with `ModuleNotFoundError: No module named 'handout_browser'`.
- Root cause: the test loads the script via `importlib.util.spec_from_file_location`, which does NOT add the script's directory to `sys.path`. So `from handout_browser import open_handout` inside the script couldn't find its sibling.
- Fix: each refactored script now does `sys.path.insert(0, str(Path(__file__).resolve().parent))` before the import. Standard Python pattern for "script imports a sibling module" — works regardless of launch method (direct run, subprocess, importlib). After fix: 102 passed.

**Verification (both layers green):**
- evals: 8/8 ALL EVALS PASS (the 3 contracts still hold after refactor).
- pytest: 102 passed (was 101+1 fail before the import-path fix; the fail was the refactor's own integration bug, caught and fixed in-session).

**Two layers catching different things, again:**
- evals verified the end-to-end contracts survived (cover still injected, examples still wrapped, chapters still paginate).
- pytest caught the integration-level regression (import path) that evals couldn't — evals runs scripts via subprocess (which DOES set cwd/sys.path implicitly), so it never hit the importlib path issue. This is exactly the complementary coverage pattern from session 5.

**Why this matters for the user's "重复造轮子" pain:**
- Before: any new "check the rendered HTML" script would copy-paste ~25 lines of launch+wait, inevitably drift, and spread bugs.
- After: a new script writes `with open_handout(html) as (page, errors): ...` — one line, consistent behavior, single fix point. This is the "可插拔、结构性特别强、抗多元化" the user described: a verified-stable component that future work assembles rather than rebuilds.

**Snapshots:** `render_html_to_pdf.py.bak-2026-06-23-4`, `validate_rendered_handout_contract.py.bak-2026-06-23-4`, `validate_sheet_bottom_margin.py.bak-2026-06-23-4`.

**Wheels NOT fixed this session (deferred, with rationale):**
- Wheel #1 (markdown code-segment protection, `protect_code_segments`): duplicated across 3 files, but spans TWO skills (scan + rewrite). Fixing it needs a cross-skill shared location, which is a bigger architectural decision the user wanted to defer. Data: the duplication is real but lower-frequency than the playwright wheel (new markdown-lint scripts are rarer than new DOM-check scripts).
- Wheel #3 (chapter-heading regex, `isChapterShapedText`/`isChapterBreakHeading`): duplicated in postprocess + validate_sheet_bottom_margin. Lower priority because it's only 2 copies and both were just synced in session 5. Worth folding into a shared module if a 3rd copy appears.

**SKILL.md note:** did NOT add a "reuse handout_browser" rule this session — the wheel's existence + the 3 refactored call sites already model the pattern. If future scripts start inlining launch+wait again, THAT is the signal to add a rule (data-driven, per the user's "先看数据" principle).
