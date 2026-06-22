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
- No non-cover, non-final A4 sheet may end with excessive trailing blank space. After rendering, run `py -3 scripts/validate_sheet_bottom_margin.py --html handout.html`; if any sheet's bottom blank exceeds 10% of the `.sheet-body` height, adjust pagination (e.g., allow long blockquotes or display blocks to split across pages) or tighten sheet-level margins before re-exporting. Cover sheets and the final sheet are exempt, and a sheet is also exempt when the very first content element on the following sheet is a `.phycat-blockquote` (because example/question blockquotes must be kept whole), or when a user/job explicitly requires the next lecture to start on a fresh sheet and the current sheet is marked `data-ends-before-lecture="true"`. <!-- evolved 2026-06-20; refined 2026-06-21 -->
- Rendered question/example blocks must satisfy the browser-DOM contract, not just source CSS strings: `例/例题/练习` labels inside `.phycat-blockquote` render as visible `.lead-tag-example` badges, blockquotes retain a real computed left accent rule, question option tables inside blockquotes are neutral (transparent and borderless), option table `th` and `td` share font/background/border state, and option images are large enough to read. The left-rule check must reject flattened/plain boxes such as `border: 1px solid var(--line)` or same-color borders, but must not reject legitimate `.phycat-blockquote` variants whose computed left border remains a visible accent rule. Run `py -3 scripts/validate_rendered_handout_contract.py --html handout.html` after every build, and fix any failure before screenshot/PDF review; for final KaTeX-rendered math jobs, add `--require-katex --disallow-mathjax`. <!-- evolved 2026-06-20; strengthened 2026-06-22 -->

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
10. Export fresh screenshot and PDF (`py -3 scripts/render_html_to_pdf.py --html handout.html --pdf handout.pdf --screenshot handout-screenshot.png`), then start reviewer subagents.

If step 4 or step 5 never happened, step 8 must fail. Treat that failure as correct behavior.

## Markdown-Source Mode (clean canonical markdown input)

This is the default mode for new work. Use it when the input is already a clean, well-structured markdown file, including `source-transcript.md` produced by the project-local `rewrite-doc2x-markdown` skill.

Use markdown-source mode when the input `.md`:
- has correct, intentional structure (headings, lists, tables, `$...$` math, `<figure>` blocks), and
- is **not** the raw Doc2X `page-transcript.raw.md` / `export.md` — those are OCR output and must be cleaned by `rewrite-doc2x-markdown` before this skill builds HTML/PDF.

Note: the builder treats bare adjacent `![](...)` images as OCR crops and clusters them into a ~92mm row. Wrap any intentional multi-image layout in a `<figure>` so it is preserved at its authored size.

Note: authored full-page cover assets, such as an SVG concept map on the handout homepage, are not OCR crops. Put them in a dedicated cover/sheet wrapper with job-local CSS that overrides generic transcript image clamps (`max-width`, `max-height`, etc.), then verify the rendered HTML/PDF shows the asset filling the first A4 sheet and the first real lecture/chapter heading starts on a fresh sheet. <!-- evolved 2026-06-17 -->

Workflow:
1. Copy the input into the job dir as `source-transcript.md` (it IS the canonical transcript — no `doc2x/` artifacts exist).
2. Build HTML directly. For the title, prefer **omitting** `--title` so the builder extracts it from the first `# ` heading in the markdown; pass `--title` only to override. Never derive the title from the filename. If the markdown has no `# ` heading, add one before building. <!-- evolved 2026-06-15 -->
   `py -3 scripts/build_faithful_handout_html.py --md source-transcript.md --out-html handout.html`
2a. Run `py -3 scripts/validate_math_quote_leakage.py --md source-transcript.md`. A non-zero exit means blockquote markers leaked into math segments; fix the source or the builder before rendering. <!-- evolved 2026-06-20 -->
3. Render: `py -3 scripts/render_html_to_pdf.py --html handout.html --pdf handout.pdf --screenshot handout-screenshot.png`.
   The default PDF from `render_html_to_pdf.py` is a **vector** PDF — this is the correct default. Do not build high-PPI raster PDFs (e.g. 600 PPI screenshot-stitched) unless the user explicitly asks; they are multi-GB, slow, and are not this skill's path. <!-- evolved 2026-06-15 -->
   **Scan-type raster PDFs are not recommended**: rasterizing a vector PDF re-samples all embedded images, causing visible quality loss (blocky artifacts, color shifts, blurry text). The vector PDF preserves original image resolution and text crispness. If a raster version is truly needed, the user must accept these tradeoffs. <!-- evolved 2026-06-15 -->
4. Math rendering is a hard output contract: final printable HTML/PDF must use **KaTeX HTML/font rendering** for LaTeX math by default. If the builder emits MathJax SVG, apply the safe KaTeX post-process from `references/math-rendering.md` before the final render/export. Do not leave MathJax `tex-svg` as the final renderer unless the user explicitly requests MathJax SVG or a fully self-contained offline math file and accepts the heavier formula appearance. <!-- evolved 2026-06-17 -->
5. Verify in a browser / PDF viewer: math rendered, 0 overflow (no sheet marked `data-fit-state="overflow"`), 0 contentless non-cover sheets, figures at intended size, title not duplicated. For math-bearing jobs, inspect concrete DOM/rendering counters for the hard contract: `.katex` nodes exist, MathJax scripts/containers are absent, no raw `$...$` / `\(...\)` / `\[...\]` math delimiters remain visible, no Markdown blockquote marker `>` has leaked into formula text, there are no browser page errors, no broken images, and pagination waits for `renderMathInElement(...)` plus `document.fonts.ready` before measuring. Then run `py -3 scripts/validate_rendered_handout_contract.py --html handout.html` (add `--require-katex --disallow-mathjax` after the required KaTeX finalization for math-heavy jobs) and `py -3 scripts/validate_sheet_bottom_margin.py --html handout.html` to confirm the rendered blockquote/table/image contract and no non-cover sheet ends with more than 10% trailing blank space except explicit blockquote/lecture-break exemptions. If a job-local post-process changed pagination, cover layout, or injected CSS/JS, verify the same no-error/no-overflow/no-blank-sheet/no-excessive-trailing-blank contract, the question option table contract, and no first-page cover shrinkage. <!-- evolved 2026-06-17; strengthened 2026-06-19; strengthened 2026-06-20; refined 2026-06-21 -->
6. Open `handout.html` and confirm the body contains real HTML elements (`<h1>/<h2>`, `<p>`, `<ul>/<ol>`, `<table>`) — **not raw Markdown source text**. A build that emits un-converted Markdown is broken; do not proceed to PDF or review. <!-- evolved 2026-06-15 -->
7. CSS / styling iteration: edit `handout.html` directly (or append a job-local `<style>` override). Do **not** re-run `build_faithful_handout_html.py` to change styling — the builder regenerates its CSS from scratch on every run, so a rebuild silently discards all job-local CSS fixes. Reserve rebuilds for content/source changes. <!-- evolved 2026-06-15 -->

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
- `scripts/render_html_to_pdf.py` — Playwright HTML→A4 PDF + screenshot (engine-agnostic math wait)
- `scripts/validate_math_quote_leakage.py` — detects structural blockquote `>` markers leaked into `$...$` / `$$...$$` math segments <!-- evolved 2026-06-20 -->
- `scripts/validate_rendered_handout_contract.py` — browser-DOM rendered-output gate for blockquote lead badges and computed left accent rule (including flattened-border regression coverage), neutral question option tables, readable choice images, overflow, contentless sheets, and optional final KaTeX/MathJax checks via `--require-katex --disallow-mathjax` <!-- evolved 2026-06-20; strengthened 2026-06-22 -->
- `scripts/lint_transcript_structure.py`
- `scripts/validate_job_state.py`
- `assets/kami-default-kernel.css`
- `assets/phycat-blockquote.css`
- `assets/table-consistent.css` <!-- evolved 2026-06-15 -->
- `assets/lead-tags.css` — lead-tag (解析, accent blue) and lead-tag-example (例N, peach #DE7356) badge styles <!-- evolved 2026-06-15 -->
