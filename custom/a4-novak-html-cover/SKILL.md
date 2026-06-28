---
name: a4-novak-html-cover
description: Use when analyzing a document (lecture notes, textbook chapter, PDF/markdown) and generating a printable A4 portrait Novak/tree concept map cover as HTML. Produces a single-page handout cover with HTML cards, SVG bezier connector overlay, and KaTeX math formulas. Choose this over the SVG-cover skill whenever the cover must be edited by changing text/formulas (not coordinates), or whenever formulas must render at full fidelity without pre-rendering to SVG paths. Use whenever the user asks for a 概念图 / 知识图 / 封面 / mind map / Novak cover / 讲义首页 from a document — even if they don't say "HTML".
---

# A4 Novak HTML Cover

Analyze a document, extract its concept structure, and produce a print-safe A4 portrait Novak/tree concept map as a single self-contained HTML file. The HTML uses **HTML cards + an SVG connector overlay + KaTeX formulas** — the HTML流派 (not pure SVG), so editing a card means changing text, never recomputing coordinates.

This is the successor approach to `a4-novak-svg-cover`. It eliminates the recurring failure modes of pure-SVG covers (coordinate drift, black-fill fallback, line-over-text, formula pre-rendering) by construction.

## When This Applies

- A handout needs a first-page concept map / knowledge graph / tree map.
- The map must fill one A4 portrait page in HTML/PDF.
- The user wants a cover generated *from a document* (analyze → map).
- Content is math-heavy, Chinese-heavy, or both.
- The cover will be edited later by changing wording or formulas (this is the key reason to prefer HTML over SVG).

## Why HTML, not SVG

Pure-SVG covers fail repeatedly because every card needs hand-tuned coordinates and every formula needs pre-rendering to path data. The HTML流派 fixes this structurally:

| Edit task | Pure SVG (legacy) | HTML 流派 (this skill) |
|---|---|---|
| Change a card's text | Find `<text>`, may need new `x`/`font-size` | Change the `<div>` text |
| Change a formula | Re-render MathJax to SVG path, re-embed, recompute box | Change the `data-tex` string |
| Add a leaf card | Recompute every coordinate below it + all connector paths | Add a `<div>`, add one EDGES line |
| Line crosses text | Depends on DOM order, validator-enforced | Connector SVG sits under cards (z-index 0 < 2), cannot cross text |

## Output Contract

**Output directory rule (revised 2026-06-29):** write the cover artifacts **into the caller-specified directory**, which is normally the chapter's main job directory (the same one that holds `source-transcript.md` / `handout.html`). Do **not** create a separate `日期-任务名-cover` subdirectory when the cover is part of a handout pipeline — the downstream `postprocess_handout_for_contract.py` looks for `concept-map.png` **next to `handout.html`**, so splitting the cover into its own dir leaves `concept-map.png` duplicated and `concept-map.html` orphaned. Only create a standalone `日期-任务名-cover` directory when there is no handout job at all (the cover is the sole deliverable).

Produce, in that directory:

- `concept-map.html` — the self-contained A4 cover (cards + connector overlay + KaTeX).
- `vendor/katex/` — local KaTeX (css + js + fonts) copied from a vendored copy, so rendering is offline and reproducible.
- `concept-map.png` — **the handout-consumption artifact** (see Handout Consumption Contract below). This is a full-A4-page PNG render of the cover; it is what downstream handout assembly embeds.
- `concept-map.pdf` — print PDF (optional, for standalone preview).
- The formula validator must pass (see Validation).

## Handout Consumption Contract

This skill is the cover generator for `scan-pdf-to-print-html`. The handout builder does NOT inline the cover's HTML; it embeds the cover as an `<img>` via `postprocess_handout_for_contract.py`, which picks up the cover by filename. The contract is:

- **`concept-map.png` is required** in every cover job dir. The handout's `inject_cover_metadata` recognizes it as a cover candidate and writes it into `data-cover-href`; the rendered handout then shows this PNG as the first A4 sheet.
- **`concept-map.html` is the editable source.** To revise a cover, edit the HTML (change a card's text / a `data-tex` formula / an `EDGES` entry) and re-run `render_cover.py` to regenerate `concept-map.png`. Never hand-edit the PNG.
- **Do not leave a stale `concept-map.svg` in the cover job dir.** The handout's cover-candidate order is now `png > svg` (HTML cover preferred), but if an old `.svg` lingers and the `.png` is missing, the handout would fall back to the outdated SVG. HTML-cover jobs ship exactly: `concept-map.html` + `concept-map.png` (+ `vendor/katex/`).
- When feeding a handout job, place `concept-map.png` (and optionally the editable `concept-map.html`) next to `handout.html`. See `scan-pdf-to-print-html`'s `references/cover-workflow.md` for the end-to-end flow.

## Workflow

### 1. Analyze the document

Read the source (markdown transcript, exported doc2x markdown, or the user's description). Extract:

- **Root title** + one-line subtitle.
- **Core transfer concept** (one card that bridges root → branches).
- **3–5 branch headers** — the top-level concept categories.
- **Leaf cards** under each branch: each leaf is a sub-concept, ideally with a short note and (for math content) one formula.
- **Cross-links** — dashed relationships between branches (optional).
- **Method rail** — a bottom summary of the general procedure (optional).

Write the extracted structure to a short `layout-design.md` *before* writing HTML, so layout decisions are deliberate, not improvised while typing coordinates.

### 2. Plan the A4 tree layout

A4 portrait is `210mm × 297mm`. Prefer the measured four-column tree:

1. Root title card near the top (centered).
2. Core transfer card below it (centered).
3. 3–5 branch headers in one row.
4. Leaf cards stacked in columns under each branch.
5. Optional method rail near the bottom.
6. Optional cross-links are dashed.

Card placement is in **mm** via `left/top/width/height` inline styles. Keep cards at least 10mm from page edges and at least 3mm apart. See `references/layout-math.md` for the exact column coordinates and the safe-area reasoning.

### 3. Generate the HTML

Start from `assets/cover_template.html`. It already contains:

- The full `<style>` (colors, card types, four branch palettes).
- The engine `<script>`: **KaTeX render → `autoFitFormula` → `drawEdges`**.
- An `EDGES` config object for declarative connections.

To generate a real cover:
1. Replace the `{{PLACEHOLDER}}` text with the document's concepts.
2. Add/remove leaf card `<div>`s, each with a unique `data-node`.
3. Fill the `EDGES.tree` array with `[parent, child]` pairs and `EDGES.cross` with cross-links — using the `data-node` names. **No coordinates needed.**
4. Put formulas in `<div class="formula" data-tex="...">`. KaTeX renders them; `autoFitFormula` scales any that overflow.

Do not rewrite the engine `<script>`. The `drawEdges` + `autoFitFormula` logic is validated; only the `EDGES` config and the card DOM change.

### 4. Set up local KaTeX

Copy a vendored KaTeX into the job dir so rendering is offline:

```
vendor/katex/
  dist/katex.min.css
  dist/katex.min.js
  dist/fonts/   (woff2/ttf)
```

The HTML references `vendor/katex/dist/katex.min.css` and `.js`. A vendored copy lives in any existing cover job dir's `vendor/katex/` — copy that tree into the job's `vendor/katex/`. If no vendored copy exists, `npm install katex@0.16.11 --no-save` and copy `node_modules/katex/dist` → `vendor/katex/dist`.

### 5. Render

```bash
py -3 .zcode/skills/a4-novak-html-cover/scripts/render_cover.py product/<job>/concept-map.html
```

This calls the project's `scan-pdf-to-print-html` `render_html_to_pdf.py`, which waits for `data-handout-ready`, `fonts.ready`, then a grace period — exactly the timing the engine's `finalize()` needs.

### 6. Validate

```bash
py -3 .zcode/skills/a4-novak-html-cover/scripts/validate_cover_formulas.py product/<job>/concept-map.html
```

This reads the DOM (not pixels) and fails the cover if any formula overflows its card or sits off-center. **A cover is not done until this passes.** Fix overflows by letting `autoFitFormula` do its job (it runs automatically), or by shortening the formula / widening the card.

## Key Engine Mechanics (do not fight these)

- **`data-handout-ready`**: the engine sets `document.documentElement.dataset.handoutReady = 'true'` *only after* `drawEdges` finishes. The renderer waits for this — so if the flag never sets, the PDF hangs. Symptom → a JS error, usually a bad `data-node` name in `EDGES`.
- **Connector overlay uses mm coordinates**: the `<svg class="edges">` has `viewBox="0 0 210 297"` and `210mm × 297mm`, the same coordinate space as the cards. `drawEdges` converts `getBoundingClientRect()` px → mm, so lines always track the real card positions regardless of font metrics.
- **`autoFitFormula`** runs after KaTeX renders; it measures each `.formula` against its card's inner width and scales the font down if it overflows. This is why long formulas no longer spill — but it means formula size can vary between cards. If a formula is scaled down a lot, prefer shortening it or widening the card.
- **Cross-links** (`EDGES.cross`) connect card *sides* (`top/bottom/left/right`), so they naturally avoid passing under cards.

## Validation Checklist

Before claiming the cover is done:

- [ ] `concept-map.html`, `concept-map.png`, `concept-map.pdf` all exist in the job dir.
- [ ] `validate_cover_formulas.py` passes (no overflow, no drift).
- [ ] Visually inspect the PNG: four columns present, connectors attached, formulas rendered as typeset math (not raw `\(…\)` or tofu).
- [ ] KaTeX is local (`vendor/katex/`), not CDN — the PDF must render identically offline.
- [ ] First page fills the A4 sheet; no blank second page.

## Common Mistakes

| Symptom | Cause | Fix |
|---|---|---|
| PDF hangs / never finishes | `data-handout-ready` never set | A `data-node` in `EDGES` doesn't match any element; check browser console |
| Formulas show as raw `a_n=...` text | KaTeX didn't load | `vendor/katex/` missing or path wrong |
| Formula overflows card | `autoFitFormula` didn't run | Ensure `data-handout-ready` set after `autoFitFormula`; or formula is absurdly long |
| Lines don't connect | Wrong `data-node` names in `EDGES` | Names must match the `data-node` attribute exactly |
| Blank second page in PDF | Content height > 297mm | Trim bottom card heights / move method rail up |
| Connector lines under cards invisible | z-index wrong | `.edges` z-index 0, `.layer-cards` z-index 2 (template already correct) |

## References

- `references/layout-math.md` — exact four-column mm coordinates, safe areas, card sizing rules.
- `assets/cover_template.html` — the validated skeleton; copy and fill in.

## Contrast With the SVG Skill

`a4-novak-svg-cover` (the legacy skill) produces a pure standalone `.svg`. It remains valid when the cover must be a single portable SVG file with no JS dependency (e.g. embedded in a non-browser viewer). For every case where the cover is consumed via the HTML→PDF pipeline and will be edited, prefer this HTML skill.
