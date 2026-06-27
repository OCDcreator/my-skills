---
name: scan-pdf-to-print-html
description: Use when a completed canonical `source-transcript.md` or other clean markdown must become faithful A4 HTML/PDF. Also use after `rewrite-doc2x-markdown` has finished OCR cleanup for scanned PDFs, textbooks, formulas, tables, diagrams, or question pages. Do not use as the default PDF-to-Markdown or Doc2X OCR entry point.
---

# Scan Pdf To Print Html

Produce faithful print outputs from an approved canonical Markdown transcript:

- `handout.html` and PDF: final print outputs

This is the downstream print skill. For a PDF-only or messy Doc2X/OCR Markdown task, run the project-local `rewrite-doc2x-markdown` skill first to create the canonical `source-transcript.md`; then use this skill for Kami-based HTML/PDF assembly.

Never run OCR cleanup, rewrite, summarize, teach, merge away page provenance, or silently replace the canonical transcript with export markdown inside this skill.

## Hard Contract

These apply in **every** mode:

- `source-transcript.md` is the only transcript file allowed to feed HTML.
- The main thread must never one-shot the full transcript into final HTML.
- Reviewer subagents start only after real HTML, screenshot, and PDF exist.
- Final rendered output must have no contentless non-cover A4 sheet. After pagination, inspect the actual `.sheet` inventory for zero-text/zero-media pages; if a separator-only block such as `<hr>` or an empty `.flow-block` creates a blank page, filter that ignorable block before exporting the fresh PDF. <!-- evolved 2026-06-19 -->
- No non-cover, non-final A4 sheet may end with excessive trailing blank space. After rendering, run `py -3 scripts/validate_sheet_bottom_margin.py --html handout.html`; if any sheet's bottom blank exceeds 10% of the `.sheet-body` height, adjust pagination (e.g., allow long blockquotes or display blocks to split across pages) or tighten sheet-level margins before re-exporting. Cover sheets and the final sheet are exempt, and a sheet is also exempt when the very first content element on the following sheet is a `.phycat-blockquote` (because example/question blockquotes must be kept whole), or when a user/job explicitly requires the next lecture to start on a fresh sheet and the current sheet is marked `data-ends-before-lecture="true"`, or when the trailing blank is the unavoidable cost of the image width-band rule — i.e. the next sheet's first content block is a figure whose image satisfies its band and is too tall to move up (or almost fits, within ~8% of the gap). A sheet is ALSO exempt when the next sheet starts with a heading that is a real section start (the heading has following content on that sheet): that blank is the cost of the heading beginning its own section, and pulling it up would strand it — this is the key weak-model safety valve, so do NOT tighten spacing to chase such a blank. **A boundary image INSIDE a `.phycat-blockquote` is never a movable-figure defect:** narrowing an in-quote image cannot move the protected blockquote (the rebalance refuses to pull blockquotes up), so the `validate_sheet_bottom_margin.py` figure-boundary analysis skips such images and the sheet falls through to the blockquote exemption. Without this guard the gate emits a false-positive "narrow the figure and it will move up" hint on geometry-figure examples and sends the model into an unbounded shrink/reflow loop. <!-- evolved 2026-06-25 --> **None of these exemptions excuse a stranded "orphan heading":** a sheet whose *last* content element is a heading sitting alone above a large blank is a pagination defect (the heading should have traveled with its following content to the next sheet), so `validate_sheet_bottom_margin.py` FAILs it even when the next sheet starts with a blockquote or band-compliant figure. The only orphan-heading exemption is a genuine section break (`data-ends-before-lecture="true"` or a next-sheet chapter-shaped h2), where the heading is the intended end of the section. The postprocess step prevents the defect at the source: when a block overflows to a new sheet and the sheet being left ends with a heading-only flow-block, `postprocess_handout_for_contract.py` pulls that heading forward so it begins the next sheet (chapter/lecture break headings are intentionally section ends and are NOT moved). When two hard contracts conflict at a page boundary, the rule whose target is met wins; do not fight both to the letter. **Specifically, when `validate_sheet_bottom_margin.py` says "narrow the figure to ~X% floor" and `validate_rendered_handout_contract.py` simultaneously says the SAME image is "TOO SMALL (enlarge)" at ~X%, the figure is in the conflict band: the width-band gate (fidelity) wins — do NOT shrink past the band floor to chase the trailing-blank hint. Stop after one shrink/enlarge round; if both gates still fire, that sheet is the authorized fidelity-exempt gap, not a defect to chase.** <!-- conflict-band + shrink-loop stop rule evolved 2026-06-25 --> <!-- evolved 2026-06-20; refined 2026-06-21; figure-boundary trade-off added 2026-06-23; orphan-heading guard + anti-orphan pagination added 2026-06-24; heading-boundary (weak-model safety) exemption added 2026-06-24; in-blockquote figure guard + conflict-band stop rule added 2026-06-25 -->
- Rendered question/example blocks must satisfy the browser-DOM contract, not just source CSS strings: `例/例题/练习` labels inside `.phycat-blockquote` render as visible `.lead-tag-example` badges, blockquotes retain a real computed left accent rule, question option tables inside blockquotes are neutral (transparent and borderless), option table `th` and `td` share font/background/border state, and option images are large enough to read. The left-rule check must reject flattened/plain boxes such as `border: 1px solid var(--line)` or same-color borders, but must not reject legitimate `.phycat-blockquote` variants whose computed left border remains a visible accent rule. Run `py -3 scripts/validate_rendered_handout_contract.py --html handout.html` after every build, and fix any failure before screenshot/PDF review; for final KaTeX-rendered math jobs, add `--require-katex --disallow-mathjax`. <!-- evolved 2026-06-20; strengthened 2026-06-22 -->
- Authored full-page cover/special sheets must share the same screen-preview A4 frame geometry as regular sheets. The rendered contract validator compares marked cover sheets (such as `.concept-map-sheet`, `[data-sheet-role="cover"]`, or `[data-cover-sheet="true"]`) against the first regular `.sheet` using `getBoundingClientRect()` for `left` and `width` with a small pixel tolerance; this catches a cover left-aligned by `margin: 0` while ordinary sheets are centered, without judging jobs that have no marked cover sheet or normal print-mode zero margins. <!-- evolved 2026-06-22 -->
- Rendered image width must match the image's aspect ratio, enforced by `scripts/validate_rendered_handout_contract.py` (on by default). The target width is a **smooth function of aspect ratio** (no hard jump at class boundaries) and is **capped by the image's own natural width** so a figure is never enlarged past its native pixel resolution (which would blur it). Control points (interpolated linearly between): aspect ≤0.7 → ~20%, 0.9 → ~27%, 1.0 (square) → 30%, 1.2 → 35%, 1.5 → 45%, 2.0 → 58%, 2.5 → 68%, ≥3.5 → ~78%. Effective target per image = `min(smooth_target(aspect), natural_width_%_of_body)`. Accept band is target ±7pp with a ±4pp "near-is-exempt" grace on each edge (see `references/figure-policy.md` Rendered Image Width Contract). The gate is a post-render check only — it does NOT change the builder's existing mm clamp; out-of-band images are fixed via job-local CSS, not a rebuild. Width is judged **per image, independently** — including each sibling in a multi-image `<figure>`/`.ocr-image-cluster` row (each image against its own band, NOT by aggregate row width). **Oversubscribed rows**: when the siblings' independent widths sum to >100% of body, the group stays on ONE row (proportional shrink to ~95%, `flex-wrap:nowrap`) and the independent-width rule is EXEMPTED for that group, rather than wrapping or flagging each as a violation. Images inside `.phycat-blockquote` option tables keep the existing readable-minimum gate and are exempt from this width band. Marked cover sheets (`.concept-map-sheet`, `[data-sheet-role="cover"]`, `[data-cover-sheet="true"]`) are exempt. <!-- evolved 2026-06-23; redesigned smooth target + natural cap 2026-06-23 -->
- Images the builder has already clustered into one `.ocr-image-cluster`, or that an author wrapped in one `<figure>`, must render side-by-side in the same horizontal row, not as a vertical stack. The rendered validator checks: for any two sibling `<img>` inside the same cluster/figure, if one's `getBoundingClientRect()` is entirely below the other (no horizontal overlap, top of lower ≥ bottom of upper) → FAIL. The gate does not guess which independent images "should" be clustered — it only verifies that already-grouped images stayed grouped. <!-- evolved 2026-06-23 -->
- When the user asks to image-host the Markdown artifact (not the HTML), run the `piclist-upload` skill's `migrate-md-images.ps1` against `source-transcript.md` (or a copy) AFTER `handout.html` is built, producing `source-transcript.uploaded.md`. The HTML must keep using local image paths — do not let the HTML reference remote image-host URLs, because re-reading many remote images during render/PDF export is unstable. The rendered validator's `--disallow-remote-images` flag is OFF by default (so day-to-day jobs that still reference a Doc2X CDN crop are not blocked) and is turned ON automatically as part of the image-hosting workflow step to confirm the HTML went local-only. Legitimate non-image remote refs (e.g. KaTeX CDN stylesheet/script) are not `<img src>` and are not affected. <!-- evolved 2026-06-23 -->

### OCR Hard Contract (scanned / Doc2X jobs only)

The gates below apply **only** to legacy scanned-PDF jobs that already have Doc2X artifacts in the job directory. New PDF-to-Markdown/OCR work should start in `rewrite-doc2x-markdown`, not here. Markdown-source jobs (already-clean markdown) skip these gates — see Markdown-Source Mode below.

- `doc2x/export/export.md` is reference-only, and should be localized to sibling `images/` assets whenever the Doc2X zip already contains matching local crops.
- `job.json.transcript_audit_status` starts at `pending`; HTML is blocked until it is `approved`.
- `job.json.transcript_structure_lint_status` starts at `pending`; run the transcript-structure lint before approval.
- Final HTML must come from `prepare -> page subagents -> status -> assemble`.
- Pre-OCR body crop is mandatory when safe.
- Source pages are transcript units, not forced print-page boundaries.

Read these before work:

- `references/fidelity-rules.md`
- `references/working-contract.md`
- `references/review-gate.md`
- `references/math-rendering.md` — read before building or post-processing math-heavy HTML; printable HTML/PDF math must use KaTeX by default, with MathJax SVG allowed only as an explicit user-requested exception <!-- evolved 2026-06-17 -->
- `references/cover-workflow.md` — read when the handout needs a concept-map cover; covers are generated as HTML by `a4-novak-html-cover`, rendered to `concept-map.png`, and auto-injected by the postprocess step <!-- evolved 2026-06-24 -->

## Required Workflow

Use this legacy workflow only when continuing an existing job directory that already contains Doc2X OCR artifacts. Do not use it as the default entry point for new PDF-to-Markdown work.

1. Confirm `rewrite-doc2x-markdown` has already produced or approved `source-transcript.md`, or that this is a legacy job with existing `doc2x/` artifacts.
2. Inspect `doc2x/page-transcript.raw.md`, `source-transcript.md`, and `pages/` when legacy review is needed.
3. Audit `source-transcript.md` against the raw transcript and source pages only for legacy OCR jobs that were not already approved by `rewrite-doc2x-markdown`.
4. Run `py -3 scripts/lint_transcript_structure.py --job-dir "C:\path\job"`.
5. After the user approves the transcript and the lint result, set `job.json.transcript_audit_status` to `approved`.
6. Write `layout-brief.md`.
7. Build HTML only through the orchestrator path.
7a. Run `py -3 scripts/validate_math_quote_leakage.py --md source-transcript.md` on the canonical transcript. If it reports leaked `>` markers inside math segments, fix the source (or confirm `clean_markdown()` handled them) before continuing. <!-- evolved 2026-06-20 -->
8. Run `py -3 scripts/validate_job_state.py "C:\path\job" --require-html`.
9. Run `py -3 scripts/validate_sheet_bottom_margin.py --html handout.html` to enforce the trailing-blank-space hard contract on every non-cover sheet.
10. Export fresh screenshot and PDF (`py -3 scripts/render_html_to_pdf.py --html handout.html --pdf handout.pdf --screenshot handout-screenshot.png`), then start reviewer subagents. The default PNG is already high-resolution (3× viewport ≈ A4 @ 288dpi); do not re-request a higher-res screenshot per job. <!-- evolved 2026-06-27 -->

If step 4 or step 5 never happened, step 8 must fail. Treat that failure as correct behavior.

## Markdown-Source Mode (clean canonical markdown input)

This is the default mode for new work. Use it when the input is already a clean, well-structured markdown file, including `source-transcript.md` produced by the project-local `rewrite-doc2x-markdown` skill.

Use markdown-source mode when the input `.md`:
- has correct, intentional structure (headings, lists, tables, `$...$` math, `<figure>` blocks), and
- is **not** the raw Doc2X `page-transcript.raw.md` / `export.md` — those are OCR output and must be cleaned by `rewrite-doc2x-markdown` before this skill builds HTML/PDF.

Note: the builder treats bare adjacent `![](...)` images as OCR crops and clusters them into a ~92mm row. Wrap any intentional multi-image layout in a `<figure>` so it is preserved at its authored size.

Note: authored full-page cover assets, such as a concept map on the handout homepage, are not OCR crops. **Covers are now generated as HTML** via the `a4-novak-html-cover` skill (HTML cards + SVG connector overlay + KaTeX), which renders the cover to `concept-map.png` — that PNG is what the postprocess step auto-injects as the first A4 sheet (do not hand-place an `<img>`; `postprocess_handout_for_contract.py` keys on the `concept-map.png` / `concept-map.svg` filename). The cover-candidate order is **PNG-first** so HTML-cover jobs win over any stale `.svg`. Place `concept-map.png` next to `handout.html`; do not leave a leftover `concept-map.svg` in an HTML-cover job. Verify the rendered HTML/PDF shows the cover filling the first A4 sheet, the cover sheet's screen-preview `left`/`width` aligns with regular A4 sheets, and the first real lecture/chapter heading starts on a fresh sheet. See `references/cover-workflow.md` for the end-to-end cover flow. <!-- evolved 2026-06-17; strengthened 2026-06-22; cover switched SVG→HTML-PNG 2026-06-24 -->

Workflow:
1. Copy the input into the job dir as `source-transcript.md` (it IS the canonical transcript — no `doc2x/` artifacts exist).
2. Build HTML directly. For the title, prefer **omitting** `--title` so the builder extracts it from the first `# ` heading in the markdown; pass `--title` only to override. Never derive the title from the filename. If the markdown has no `# ` heading, add one before building. <!-- evolved 2026-06-15 -->
   `py -3 scripts/build_faithful_handout_html.py --md source-transcript.md --out-html handout.html`
2a. Run `py -3 scripts/validate_math_quote_leakage.py --md source-transcript.md`. A non-zero exit means blockquote markers leaked into math segments; fix the source or the builder before rendering. <!-- evolved 2026-06-20 -->
2b. Run `py -3 scripts/validate_example_blockquote_coverage.py --md source-transcript.md`. Reports any `例/例题/练习 N` labeled paragraph that is not inside a `>` blockquote region. Fix the transcript (wrap with `>`) before building — the postprocess auto-wrap (step 3) only catches standard label shapes, so non-standard labels must be fixed at source. <!-- evolved 2026-06-23 -->
3. **Run the postprocess step — it is mandatory, not optional.** It activates three capabilities that the builder alone does NOT apply, and without it examples lose their quote styling and the concept-map cover never appears:
   `py -3 scripts/postprocess_handout_for_contract.py --html handout.html`
   - wraps every `例/例题/练习` paragraph into a `.phycat-blockquote` (without this step, example blocks render as plain paragraphs with no quote styling); if a standalone follow-up media block (`<figure>`, bare `<img>`) that was authored OUTSIDE the example gets swallowed into the quote, fix `postprocess_handout_for_contract.py` and rerun step 3 instead of hand-patching only the current HTML <!-- evolved 2026-06-25 -->
   - injects `concept-map.png` / `concept-map.svg` / `concept-map-preview.png` (if present in the job dir next to `handout.html`) as the first A4 cover sheet — this is the ONLY mechanism that turns a root-level cover file into the homepage cover, and it keys on these exact filenames. Candidate order is **PNG-first** so HTML-cover jobs (`concept-map.png` from `a4-novak-html-cover`) are preferred over any stale `concept-map.svg`. <!-- evolved 2026-06-24: png-first -->
   - enforces lecture/chapter pagination (`第N讲/章/节/篇/单元/部分`, `大招 N`, and other chapter-shaped `##` headings start a fresh sheet) and replaces MathJax with KaTeX <!-- strengthened 2026-06-25 -->
   This step is idempotent (`injectConceptCover` guards on `coverInjected`, `inject_cover_metadata` guards on `not in html`), so re-running it on an already-postprocessed HTML is safe. Skipping it silently produces examples without quote blocks and a concept-map cover that never appears — the single most common cause of "used the skill but examples have no quote / cover is missing" defects. <!-- evolved 2026-06-23; cover wording generalized 2026-06-24 -->
4. Render: `py -3 scripts/render_html_to_pdf.py --html handout.html --pdf handout.pdf --screenshot handout-screenshot.png`.
   The default PDF from `render_html_to_pdf.py` is a **vector** PDF — this is the correct default. Do not build high-PPI raster PDFs (e.g. 600 PPI screenshot-stitched) unless the user explicitly asks; they are multi-GB, slow, and are not this skill's path. <!-- evolved 2026-06-15 -->
   The default PNG screenshot is already **high-resolution** (3× viewport ≈ A4 @ 288dpi, ~2382×3369px) via `render_html_to_pdf.py`'s `--screenshot-scale` default of `3.0`; do **not** manually re-request a "higher-resolution screenshot" each job. The scale only affects the raster PNG — `page.pdf()` ignores it, so the PDF stays vector regardless. Pass `--screenshot-scale 2`/`4` only when the user explicitly wants a lighter/heavier PNG, or `1` for an old-style ~96dpi screenshot. <!-- evolved 2026-06-27 -->
   **Scan-type raster PDFs are not recommended**: rasterizing a vector PDF re-samples all embedded images, causing visible quality loss (blocky artifacts, color shifts, blurry text). The vector PDF preserves original image resolution and text crispness. If a raster version is truly needed, the user must accept these tradeoffs. <!-- evolved 2026-06-15 -->
5. Math rendering is a hard output contract: final printable HTML/PDF must use **KaTeX HTML/font rendering** for LaTeX math by default. If the builder emits MathJax SVG, apply the safe KaTeX post-process from `references/math-rendering.md` before the final render/export. Do not leave MathJax `tex-svg` as the final renderer unless the user explicitly requests MathJax SVG or a fully self-contained offline math file and accepts the heavier formula appearance. <!-- evolved 2026-06-17 -->
6. Verify in a browser / PDF viewer: math rendered, 0 overflow (no sheet marked `data-fit-state="overflow"`), 0 contentless non-cover sheets, figures at intended size, title not duplicated. For math-bearing jobs, inspect concrete DOM/rendering counters for the hard contract: `.katex` nodes exist, MathJax scripts/containers are absent, no raw `$...$` / `\(...\)` / `\[...\]` math delimiters remain visible, no Markdown blockquote marker `>` has leaked into formula text, there are no browser page errors, no broken images, and pagination waits for `renderMathInElement(...)` plus `document.fonts.ready` before measuring. Then run `py -3 scripts/validate_rendered_handout_contract.py --html handout.html` (add `--require-katex --disallow-mathjax` after the required KaTeX finalization for math-heavy jobs) and `py -3 scripts/validate_sheet_bottom_margin.py --html handout.html` to confirm the rendered blockquote/table/image contract, marked cover-vs-regular sheet alignment in screen preview, and no non-cover sheet ends with more than 10% trailing blank space except explicit blockquote/lecture-break/chapter-h2 exemptions. If a job-local post-process changed pagination, cover layout, or injected CSS/JS, verify the same no-error/no-overflow/no-blank-sheet/no-excessive-trailing-blank contract, the cover alignment contract, the question option table contract, and no first-page cover shrinkage. <!-- evolved 2026-06-17; strengthened 2026-06-19; strengthened 2026-06-20; refined 2026-06-21; strengthened 2026-06-22; chapter-h2 exemption added 2026-06-23 -->
7. Open `handout.html` and confirm the body contains real HTML elements (`<h1>/<h2>`, `<p>`, `<ul>/<ol>`, `<table>`) — **not raw Markdown source text**. A build that emits un-converted Markdown is broken; do not proceed to PDF or review. <!-- evolved 2026-06-15 -->
8. CSS / styling iteration: edit `handout.html` directly (or append a job-local `<style>` override). Do **not** re-run `build_faithful_handout_html.py` to change styling — the builder regenerates its CSS from scratch on every run, so a rebuild silently discards all job-local CSS fixes. Reserve rebuilds for content/source changes. <!-- evolved 2026-06-15 -->
   - When the defect comes from postprocess-injected pagination / quote-merge / global width-band logic (for example: a chapter-break regex, an example-run merge, or the figure-width curve), do NOT stop at hand-editing the current `handout.html`. Fix the skill script and rerun step 3; if you change the width-band curve, keep `postprocess_handout_for_contract.py` and `validate_rendered_handout_contract.py` in lockstep so the generator and gate still enforce the same curve. <!-- evolved 2026-06-25 -->
   - **When the bottom-margin gate and the width-band gate BOTH fire on the same handout, do NOT narrow figures one at a time.** A single width change reflows the whole document and re-flags a DIFFERENT sheet, so hand-editing figure widths in a loop does not converge. Instead: (a) batch-collect every flagged figure + its exact band-floor width (the floor the bottom-margin gate names in its hint) and every width-band "TOO SMALL" image in ONE pass, write them as one job-local CSS override block, then re-measure; iterate that collect→override→re-measure cycle to a fixed point. (b) If many sheets are affected, write/run a small converger script (measure all flagged figures + violations → rewrite one CSS block → re-measure → stop when stable). (c) **Stop the moment a figure would have to go below its width-band floor** to satisfy the bottom-margin hint — that figure is in the conflict band (see the trailing-blank hard contract above) and its sheet is the authorized fidelity-exempt gap, not a defect to chase. <!-- evolved 2026-06-25 -->
   - **NEVER fix an image-width / trailing-blank FAIL by editing `source-transcript.md`'s inline `max-width`/`style` attributes.** <!-- evolved 2026-06-25 --> Rendered image width is owned by `postprocess_handout_for_contract.py`'s aspect-ratio width curve (step 3), NOT by the source markdown's per-image `max-width`. A weak model that hits a width-band/bottom-margin FAIL often tries to "fix" it by lowering `max-width: 20%` → `17%` in the source and rebuilding — this is wrong on three counts: (1) postprocess's curve overrides source `max-width` anyway, so the edit is a no-op on the real width; (2) each rebuild reflows the document and re-flags a DIFFERENT sheet, so the model loops source-edits until timeout without converging (observed: a flash run edited source `max-width` 3× then timed out); (3) it corrupts the canonical transcript. The ONLY valid fixes for an image-width FAIL are: (i) a job-local `<style>` override in `handout.html` (step 8), (ii) fixing the width curve in the skill script if the curve itself is wrong (lockstep postprocess + both validators), or (iii) accepting the conflict-band exemption (the figure's sheet is an authorized fidelity gap). If `validate_sheet_bottom_margin.py` hints "narrow the figure to ~X% floor", that narrowing goes in job-local CSS, never in the source markdown.
   - **When `validate_sheet_bottom_margin.py` names a specific floor in its hint ("narrow the figure to ~X% body width (the band floor)"), narrow that figure to EXACTLY that X% — no more, no less.** <!-- evolved 2026-06-25 --> A weak model often narrows "roughly" (e.g. the hint says 47%, the model writes 51%) and stops, leaving the trailing blank unfilled and the FAIL persisting. The hint's floor is computed precisely: at that exact width the figure's scaled height + its overhead fits the trailing gap, so anything wider than the floor does NOT reclaim the blank. Read the hint's number literally and use that exact percentage in the job-local CSS `width`/`max-width` rule (`width: 47% !important;`, not `51%`). If narrowing to the named floor STILL leaves a FAIL (the figure is then in the conflict band — see above), stop; otherwise the narrowed figure must move up and the FAIL clears. Do not round up, do not "leave margin", do not stop short of the named floor.
9. (Optional, only if the user wants the Markdown artifact image-hosted) After `handout.html` and PDF are final, run the `piclist-upload` skill against a **copy** of `source-transcript.md` to migrate its image links to the image host (`pic.ltreen.tech`), producing `source-transcript.uploaded.md`. Then re-run `validate_rendered_handout_contract.py --html handout.html --disallow-remote-images` to confirm the HTML stayed on local paths. Never run this step before HTML/PDF are final, and never let it touch `handout.html` — the HTML stays local. This step is opt-in; most jobs skip it. <!-- evolved 2026-06-23 -->

Why `validate_job_state.py` does not apply here: it enforces the OCR-pipeline contract (`doc2x/`, `pages/`, audit/lint status). For markdown-source jobs there is no OCR, so those artifacts do not exist — running it produces false failures. Use the visual + builder-output checks above instead.

Everything else still holds: keep `source-transcript.md` canonical, never let an export markdown overwrite it, and start reviewer subagents only after real HTML + PDF + screenshot exist.

## Transcript Audit Rules

For new OCR/PDF jobs, transcript audit and canonical Markdown rewriting belong to `rewrite-doc2x-markdown`. Read `references/transcript-audit-rules.md` here only when continuing a legacy scan job whose transcript has not already been approved upstream.

During audit:

- Fix obvious OCR typos only when you can verify them from the source.
- If unsure, write `[TO VERIFY: ...]`.
- Preserve page markers, order, numbering, language, tables, formulas, and figure notes.
- Split merged multi-clause formulas into separate inline formulas.
- Normalize heading hierarchy. Promote title-like standalone lines to headings when the source clearly shows a heading.
- Keep the first real content heading on a page at `###`, not deeper.
- Do not jump heading levels by more than one step.
- If the first numbered heading on a page starts at `2` or `二`, treat it as a verification flag instead of silently trusting it.
- Prefer `\dfrac` for simple fractions; use `\tfrac` when numerator or denominator already contains a formula, operator, or nested fraction.
- Keep code as fenced code blocks.
- For choice examples, use one blockquote that contains the stem and the options.
- Put choice options in list form: `- A. ...`
- Normalize fill-in blanks to `__________`.
- Put solution text in its own paragraph starting with `解析：`.

## Builder Markdown Contract

The local builder now expects and enforces:

- centered fenced code blocks
- vendored `phycat`-style example blockquotes; the left accent rule is a rendered-output hard contract, so a generic `blockquote` CSS rule must never flatten `.transcript-flow .phycat-blockquote` into a plain shaded box. The rendered validator must test computed browser styles, not just CSS source strings or nonzero `border-left`: it should fail a 1px/same-color/plain-box border regression and keep a passing fixture for the intended 3px accent rule to avoid false positives. <!-- evolved 2026-06-20; strengthened 2026-06-22 -->
- two-column even choice-option layout when options are list items inside the blockquote
- special styling for paragraphs beginning with `解析：` — the builder renders the label as an inline `lead-tag` badge (accent-colored pill), not a border-left box. This avoids the blockquote-like appearance of the old `ocr-analysis` treatment <!-- evolved 2026-06-15 -->
- example/exercise labels inside normal paragraphs or blockquotes should use `lead-tag-example` peach badges when they begin with source-style labels such as `例`, `例题`, `例N`, `【例题1】`, or `【练习 1】`; do not leave them as plain bold text inside the quote. In the rendered DOM, every `.phycat-blockquote` whose visible text begins with these labels must contain a visible `.lead-tag-example`; validate with `scripts/validate_rendered_handout_contract.py`. <!-- evolved 2026-06-17; strengthened 2026-06-20 -->
- Obsidian callout markers (`[!question]`, `[!note]`, etc.) are auto-stripped from blockquotes by `clean_markdown()` <!-- evolved 2026-06-15 -->
- `table-consistent.css` is emitted **after** the print-base CSS so its transparent-background and uniform th/td rules always win the cascade <!-- evolved 2026-06-15 -->
- the builder extracts the document title from the first `# ` heading automatically; `--title` is only needed to override <!-- evolved 2026-06-15 -->
- blank normalization to `__________`
- `\frac` promotion to `\dfrac` or `\tfrac`
- Doc2X crop clustering and size clamping
- centered table cells, but only display math may be block-centered in cells
- ordered-list numbering must be preserved **verbatim from the source**: keep the original number prefix as visible text inside the `<li>` rather than relying on `<ol>` auto-numbering, because `<ol>` resets per block when other content sits between items <!-- evolved 2026-06-15 -->
- table header (`<th>`) and body (`<td>`) cells must share the same font-size, font-weight, background, and border state; the skill table template defaults to **transparent and borderless** (`border: none`). Add ruled borders or header emphasis only when the source page actually has them (fidelity), never as decoration. Question option tables nested inside `.phycat-blockquote` are not data tables: keep them transparent and borderless even when non-blockquote knowledge/data tables in the same handout use ruled cells. Do not let job-local CSS apply one global table treatment to both classes. <!-- evolved 2026-06-15; strengthened 2026-06-17; strengthened 2026-06-20 -->
- images inside question option tables must remain readable after pagination and print scaling. If a cell image is a choice diagram/graph, it must not inherit generic tiny crop limits or inline `max-width` values that make it unreadable; validate rendered dimensions with `scripts/validate_rendered_handout_contract.py` and enlarge the choice image/table layout before PDF export when it fails. <!-- evolved 2026-06-20 -->
- block elements (tables, figures) nested inside blockquotes must not carry extra bottom margin — the quote's own padding is sufficient; extra margins create visible blank space at the quote's bottom edge <!-- evolved 2026-06-15 -->
- When rendering blockquoted Markdown that contains formulas, keep `>` as a structural blockquote marker only; never let literal Markdown quote prefixes become part of `$...$`, `\(...\)`, `\[...\]`, or rendered KaTeX formula text. Legitimate mathematical `>` comparisons stay; the defect is quote-marker leakage. `clean_markdown()` strips `>` prefixes from interior lines of `$$...$$` blocks embedded in Obsidian callouts before math segments are protected. Validate with `py -3 scripts/validate_math_quote_leakage.py --md source-transcript.md`; a non-zero exit is a build blocker. <!-- evolved 2026-06-19; strengthened 2026-06-20 -->
- when a `$...$` math formula inside a Markdown table cell contains a literal `|`, escape it as `\|` in the transcript so the cell is not split into columns — see `references/transcript-audit-rules.md` <!-- evolved 2026-06-15 -->

## HTML Path

Read `references/page-fragment-worker.md` before dispatching workers.

Hard rules:

- Do not skip `status`.
- Do not approve placeholder HTML.
- Do not reintroduce raw full-width crop images or raw stacked split figures.
- Do not let `knowledge-to-print-html` replace the local Kami-based builder; it may only validate or review downstream.

## Files

- `scripts/doc2x_parse_job.py` — legacy/compatibility OCR job materializer; do not use as the default new PDF-to-Markdown entry point
- `scripts/build_handout_via_subagents.py`
- `scripts/build_faithful_handout_html.py` — Kami-kernel A4 HTML builder (used in both OCR and markdown-source modes)
- `scripts/postprocess_handout_for_contract.py` — **mandatory post-build step (Markdown-Source Mode step 3)**: in-place rewrite of the built `handout.html` that (a) wraps `例/例题/练习` paragraphs into `.phycat-blockquote` while leaving standalone follow-up media blocks outside the quote, (b) injects `concept-map.png`/`concept-map.svg`/`concept-map-preview.png` (PNG-first) as the first A4 cover sheet, (c) enforces lecture/chapter pagination, including chapter-shaped h2 such as `大招 1`, (d) replaces MathJax with KaTeX, (e) pulls an orphan ("stranded") trailing heading forward to the next sheet when its following content overflows (anti-orphan pagination; chapter/lecture break headings are intentionally section ends and stay put). Idempotent. Running the builder WITHOUT this step is the root cause of missing example quote blocks and a missing cover. <!-- evolved 2026-06-23; png-first cover 2026-06-24; anti-orphan pagination 2026-06-24; strengthened 2026-06-25 -->
- `scripts/render_html_to_pdf.py` — Playwright HTML→A4 PDF + screenshot (engine-agnostic math wait)
- `scripts/validate_math_quote_leakage.py` — detects structural blockquote `>` markers leaked into `$...$` / `$$...$$` math segments <!-- evolved 2026-06-20 -->
- `scripts/validate_example_blockquote_coverage.py` — pre-build gate (Markdown-Source Mode step 2b): reports `例/例题/练习 N` labeled paragraphs not inside a `>` blockquote region; non-zero exit = fix transcript before building <!-- evolved 2026-06-23 -->
- `scripts/validate_rendered_handout_contract.py` — browser-DOM rendered-output gate for blockquote lead badges and computed left accent rule (including flattened-border regression coverage), neutral question option tables, readable choice images, aspect-ratio-driven image width bands, cluster/figure side-by-side layout, HTML-local-image-only (`--disallow-remote-images`, off by default), overflow, contentless sheets, marked cover-vs-regular sheet screen alignment, and optional final KaTeX/MathJax checks via `--require-katex --disallow-mathjax` <!-- evolved 2026-06-20; strengthened 2026-06-22; strengthened 2026-06-23 -->
- `scripts/validate_sheet_bottom_margin.py` — trailing-blank gate; also catches **orphan headings** (a sheet ending with a lone heading above a large blank is FAILed even when the next sheet starts with a blockquote/figure, exempt only for a genuine chapter/lecture section break), and **exempts heading-boundary blanks** (next sheet starts with a heading that has following content — a real section start; this is the weak-model safety valve so correct page breaks are not "fixed" into worse ones) <!-- orphan-heading guard + heading-boundary exemption added 2026-06-24 -->
- `scripts/lint_transcript_structure.py`
- `scripts/validate_job_state.py`
- `assets/kami-default-kernel.css`
- `assets/phycat-blockquote.css`
- `assets/table-consistent.css` <!-- evolved 2026-06-15 -->
- `assets/lead-tags.css` — lead-tag (解析, accent blue) and lead-tag-example (例N, peach #DE7356) badge styles <!-- evolved 2026-06-15 -->

## Regression Evals

Lightweight programmatic regression checks under `evals/`. They build each fixture through `build_faithful_handout_html.py` + `postprocess_handout_for_contract.py`, then assert DOM contracts via Playwright — **no subagents, no LLM grading**. Run in seconds; cost is near-zero beyond the browser launch.

**When to run:** after editing ANY file under `scripts/` (builder, postprocess, validators) or changing pagination/cover/blockquote logic. This is the fastest way to know whether an edit broke example-wrapping, SVG cover injection, or chapter pagination — the three highest-bug-rate areas.

**How to run:**
`python3 evals/run_programmatic_eval.py`            (all evals; macOS uses `python3`, Windows `py -3`)
`python3 evals/run_programmatic_eval.py --only 2`   (single eval)
`python3 evals/run_programmatic_eval.py --keep-tmp` (keep temp job dirs for inspection)

Exit code = number of failed assertions (0 = all green). **Do not declare a script change done until this is green.** If an eval fails, the printed evidence names the exact DOM state so the cause is visible without debugging.

**Coverage (5 evals, declared in `evals/evals.json`, schema-compatible with skill-creator):**
1. `example-blockquote-coverage` — pre-build gate flags bare-paragraph examples; post-build leaves zero bare example `<p>` outside `.phycat-blockquote`; 解析 stays out of blockquotes; a media-only `<figure>` immediately following an example stays outside the quote. <!-- strengthened 2026-06-25 -->
2. `svg-cover-injection` — `concept-map.svg` becomes the first marked cover sheet (`.concept-map-sheet` + `data-sheet-role=cover`) with an `<img>` pointing at it.
3. `chapter-h2-pagination` — each chapter-shaped h2 (`第N章/节/...` and `大招 N`) except the first starts its own sheet; the preceding sheet is marked `data-ends-before-lecture`; a near-miss non-chapter h2 such as `大招总结` does NOT trigger the break. <!-- strengthened 2026-06-25 -->
4. `footer-page-and-breadcrumb` — every non-cover sheet shows `第 X / N 页` with N = sheet count; chapter sheets carry their chapter name in the breadcrumb; covers have no footer.
5. `orphan-heading-pagination` — when a block overflows to a new sheet, a heading that was the previous sheet's LAST content block travels with its following content (no non-final sheet ends with a heading); `validate_sheet_bottom_margin` stays clean. Mutation-detectable: disabling `pullOrphanHeadingForward` strands the heading and fails the assertion. <!-- added 2026-06-24 -->

**Relationship to skill-creator's full eval flow:** this is the daily regression gate (code-logic regressions only). For big-version checkups (does the whole skill still serve users well?), use skill-creator's subagent + benchmark flow — the fixtures and expectations here are schema-compatible so they can be reused there. <!-- evolved 2026-06-23 -->

**Verification ceiling:** this catches code-logic regressions (regex too narrow, exemption missing, cover injection broken). It does NOT catch model-behavior regressions (model skips step 3 after reading SKILL.md) — those are defended by the mandatory workflow commands. Code-logic regressions are the more common, more hidden failure mode, and this eval directly covers them.
