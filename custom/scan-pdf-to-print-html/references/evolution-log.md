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
