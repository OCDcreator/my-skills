---
name: a4-novak-svg-cover
description: Use when creating or fixing an A4 portrait SVG cover for a printable handout, especially Novak/tree concept maps, homepage knowledge graphs, full-page SVG covers, math/Chinese handouts, or SVGs that must survive HTML/PDF rendering without overlap, tofu glyphs, tiny scaling, black fills, line-text collisions, or off-center card text.
---

# A4 Novak SVG Cover

Create a print-safe A4 portrait SVG cover concept map for a handout. The output should be deterministic, auditable, and robust across browser HTML, PDF export, and common SVG/PDF viewers.

## Core Principle

Treat the SVG as a printable document page, not a decorative web image. Use measured millimetre geometry, inline presentation attributes, deterministic layout, and validator-backed checks.

## When This Applies

- A handout needs a first-page concept map / knowledge graph / tree map.
- The map must fill one A4 portrait page in HTML/PDF.
- The content is math-heavy, Chinese-heavy, or likely to hit font fallback issues.
- Prior SVG attempts show black fills, tiny images, overlapping cards, tofu boxes, lines over text, or uncentered labels.
- The user asks for a Novak-style / tree-shaped map rather than a circular mind map.

## Output Contract

Produce or preserve these artifacts in the job directory:

- `concept-map.svg`: final A4 portrait SVG.
- `concept-map-preview.png`: rendered preview when possible.
- `generate_concept_map_svg.py`: deterministic generator for repeatable edits.
- `validate_concept_map_svg.py`: static SVG checks.
- `check_concept_map_rendered_layout.py`: browser geometry checks when Playwright is available.
- When any visible math is present: `formulas.json` and the MathJax-rendered SVG fragments embedded in `concept-map.svg` as `g.formula-fit[data-formula-id]`.
- Optional `concept-map-layout-design.md`: human-readable layout notes.

## A4 SVG Requirements

Use this exact root shape unless the user explicitly chooses another paper size:

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">
```

Design constraints:

- Use A4 portrait dimensions: `210mm x 297mm`, `viewBox="0 0 210 297"`.
- Keep cards at least `10mm` from page edges for print safety.
- Keep card-to-card gaps at least `3mm`.
- Keep text at least `1mm` inside its owning card.
- Center every card's text group horizontally and vertically; allow at most `2mm` center delta.
- Draw connector paths before cards and text so fills naturally hide line segments beneath cards.
- Use label shields: small paper-colored rectangles behind edge labels to visually break connector lines.
- Keep connector lines light: roughly `0.42px-0.48px` stroke width and `0.58-0.66` opacity.
- Use inline presentation attributes (`fill`, `stroke`, `font-family`, etc.). Do not rely on `<style>`, CSS variables, or class-only styling.
- Add explicit `fill="none"` on paths and hairlines that should not fill.

## Typography And Formula Readability

<!-- evolved 2026-06-17 -->
- Card body text is content, not a caption: it must not be visibly smaller than the handout's normal body text or shrink into footnote-like copy. If body text looks small in the rendered preview, enlarge it first, then adjust card height, row spacing, or wording to keep the layout valid.
<!-- evolved 2026-06-17 -->
- Card titles may remain larger/bolder than body lines, but non-title explanatory lines should still be comfortably readable on an A4 print preview.
<!-- evolved 2026-06-17 -->
- When MathJax formula fragments are used, formula `max_w` / `max_h` must be tuned with the surrounding text size. Do not let formulas become the smallest visual element in the card; scale formulas and text together, then rerun formula-aware layout checks.

## Math Formula Rendering

For math-heavy concept maps, the MathJax SVG pipeline is the **default, proactively-run renderer** whenever card content contains any math (function notation like `tan/sin/cos`, Greek letters, subscripts/superscripts, fractions, roots, equations, or symbol names like `alpha`/`omega`). Do not write that math as raw SVG `<text>` and then stop — run the pipeline up front: list expressions in `formulas.json`, render with `render_mathjax_svg.mjs`, and embed each as `<g class="formula-fit" data-formula-id="...">`. Within a single map, choose one formula policy for all visible expressions; "do not mix raw SVG text math with rendered formula fragments" is not satisfied by an all-raw-text map. <!-- evolved 2026-06-18 -->

<!-- evolved 2026-06-20 -->
- This is a validator-enforced hard contract: the static validator must fail by default when visible SVG `<text>` contains formula-like content outside `g.formula-fit`, or when a `formula-fit` group lacks `data-formula-id`. Do not claim the cover is complete after using `--allow-raw-math-text`; that flag is only for an explicitly human-approved exception and must be disclosed.
<!-- evolved 2026-06-17 -->
- Preferred standalone-SVG path: keep formula sources in data files, render them at build time with MathJax SVG output, and embed them as `<g class="formula-fit" data-formula-id="...">` path/rect/vector fragments.
<!-- evolved 2026-06-17 -->
- Chinese explanatory text may remain SVG `<text>`, but expressions such as `e^x`, `ln x`, `f'(x)`, subscripts, exponents, derivatives, equations, and function notation should go through the formula pipeline.
<!-- evolved 2026-06-17 -->
- If KaTeX is requested, use it only when the output is converted to SVG/vector fragments; raw KaTeX HTML is not enough for a standalone SVG deliverable.
<!-- evolved 2026-06-17 -->
- Formula-aware validators must skip MathJax internal geometry inside `g.formula-fit` and treat formula groups as card content for padding and centering checks.
<!-- evolved 2026-06-17 -->
- After increasing text size, increase formula fragment bounds and card/row geometry together rather than shrinking MathJax output to preserve the old layout.

## Background Policy

<!-- evolved 2026-06-17 -->
- Default to one solid page background rect. Do not add decorative grids, hairlines, dot matrices, or paper texture unless the user explicitly asks for them.
<!-- evolved 2026-06-17 -->
- If the user asks for a plain background, add a guard test or grep check that rejects background grid paths/hairlines.

## Layout Pattern

For lecture handouts, prefer a measured Novak/tree layout:

1. Root title card near top.
2. Core transfer/concept card below it.
3. 3-5 branch headers in a single row.
4. Leaf cards stacked in columns under each branch.
5. Optional method rail / summary card near the bottom.
6. Optional cross-links are dashed and remain under cards/text.

Avoid circular mind maps unless explicitly requested. A4 print readability usually improves with columns and predictable hierarchy.

## Glyph Safety

Chinese/math SVGs often render through fallback fonts in PDF viewers. Avoid glyphs that frequently become tofu boxes or unexpected squares.

Do not use these in visible SVG text unless you have verified the target viewer:

| Avoid | Safer replacement |
|---|---|
| `⇄` | `对应` |
| `→` | `到` / `对应` |
| `′` | ASCII `'` in `f'(x0)` |
| `₀`, `₁`, `₂` | `x0`, `x1`, `x2` |
| `·` | space or comma |
| `–` | ASCII hyphen |

Also remove generic advertising/footer phrases unless the user asks for them, such as `A4 portrait concept map` or tool-generated slogans.

## HTML/PDF Cover Insertion

When inserting into a print handout:

1. Put the SVG in a dedicated first-page container.
2. Override generic image rules that may shrink transcript images.
3. Force the cover page to one A4 sheet.
4. Force the first real lecture/chapter heading after the cover to begin a fresh sheet.

CSS pattern:

```css
.concept-map-sheet {
  width: 210mm;
  height: 297mm;
  margin: 0;
  padding: 0;
  overflow: hidden;
}
.concept-map-front-image {
  display: block;
  width: 210mm !important;
  height: 297mm !important;
  max-width: none !important;
  max-height: none !important;
  object-fit: fill;
}
```

The `!important` overrides are deliberate: many transcript builders clamp all images to small widths for OCR crops.

## Validation Checklist

Run static and rendered checks before claiming the cover is done.

```bash
py -3 scripts/validate_concept_map_svg.py concept-map.svg --min-gap-mm 3
py -3 scripts/check_concept_map_rendered_layout.py concept-map.svg --min-edge-pad-mm 10 --min-text-pad-mm 1 --text-cross-pad-mm 0.45 --max-edge-stroke-mm 0.5 --max-card-text-center-delta-mm 2
```

Expected checks:

- A4 root size and viewBox are exact.
- No `<style>` block dependency.
- Math expressions are not left as raw SVG text; `validate_concept_map_svg.py` rejects formula-like visible `<text>` by default unless it is inside `g.formula-fit`.
- Every `g.formula-fit` group has `data-formula-id`, proving that the MathJax formula pipeline was intentionally used rather than pasted as anonymous SVG.
- Formula fragments inside `g.formula-fit` do not get counted as card rectangles.
- The background is a single solid page fill unless decorative texture was explicitly requested.
- No forbidden glyphs.
- Removed subtitle/footer phrases are absent.
- Cards do not overlap and keep the configured gap.
- Rectangles/text have inline fill/stroke attributes.
- Cards keep the edge safe area.
- Text stays within card padding.
- Text groups are centered inside cards.
- Rendered body text and MathJax formula lines are readable at A4 preview size and do not look like footnotes compared with the handout body.
- Edges are below text in DOM order.
- Edges do not visibly cross text unless hidden by a card or label shield.
- Edge strokes are not too heavy.

## Bundled Resources

- `scripts/generate_concept_map_svg.py`: concrete deterministic generator from the derivative/tangent job. Adapt the content and box coordinates, but preserve the measured layout approach.
- `scripts/validate_concept_map_svg.py`: static artifact validator, including the hard MathJax-pipeline gate for formula-like raw SVG text.
- `scripts/check_concept_map_rendered_layout.py`: Playwright geometry validator.
- `references/layout-design-notes.md`: compact notes from the successful A4 four-column layout.

## Common Mistakes

| Mistake | Fix |
|---|---|
| SVG renders as black blocks | Inline all presentation attributes; add explicit `fill="none"` to paths. |
| Cover is tiny in HTML/PDF | Override global transcript image CSS for the cover image. |
| Cards overlap after content changes | Use calculated columns and run the min-gap validator. |
| Card text looks visually high/low | Center the whole text group around the card center, not just the first line. |
| Lines obscure labels | Draw paths first; add label shields behind text. |
| Chinese/math symbols show tofu | Replace risky glyphs with stable Chinese/ASCII equivalents. |
| First lecture starts on cover page | Add a dedicated cover sheet and force lecture headings to fresh sheets. |
| Formulas appear as raw `<text>` | Put sources in `formulas.json`, render with MathJax SVG, embed `g.formula-fit[data-formula-id]`, then rerun the static validator. |

## Minimal Workflow

1. Extract the source concepts, branches, and relationships.
2. Sketch a measured A4 tree layout before writing SVG.
3. Generate SVG with a script, not hand-dragged coordinates.
4. Render a preview and inspect visually.
5. Run both validators.
6. Insert into HTML with full-page cover CSS.
7. Render PDF/screenshot and confirm the first page is filled and later headings paginate correctly.
