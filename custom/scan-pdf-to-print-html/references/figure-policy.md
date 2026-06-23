# Figure Policy

Scanned figures are part of the source content. Treat them conservatively.

## Decision Order

1. Reuse the source figure if it is already clear enough for print.
2. Crop and clean the source figure if clarity can be improved without changing content.
3. Redraw only if the source is too blurry, noisy, or damaged to preserve the original information reliably.

## Redraw Requirements

If you redraw a figure, preserve:

- all labels
- relative geometry and layout
- line style distinctions such as solid vs dashed
- axis direction and tick intent
- table structure and visible emphasis
- arrows, angle marks, and callouts

## Prohibited Redraw Changes

- inventing missing labels
- changing the problem geometry
- changing table values or order
- replacing a function graph with a different scale or shape
- turning an evidence figure into decorative art

## Practical Rule

For math figures, "looks cleaner" is not enough reason to redraw. Redraw only when fidelity improves.

## Layout Hard Constraints

These are builder-enforced output constraints, not soft review suggestions:

- Tiny Doc2X crop figures must not render as raw full-width body images in final HTML.
- Consecutive crop-only figures that belong to one logical side-by-side source figure must render as one clustered row or grid, not as a vertical stack of unrelated block images.
- If two or more crop images are required to preserve one logical source figure, keep them adjacent all the way through transcript and fragment generation so the local builder can normalize them deterministically.

## Rendered Image Width Contract

Post-render check only — it does NOT change the builder's existing mm clamp (34/48/64/72mm). The validator computes each non-exempt image's aspect ratio from `naturalWidth/naturalHeight` and checks its rendered width against a band expressed as a fraction of the `.sheet-body` content width: <!-- evolved 2026-06-23 -->

| Class | aspect (w/h) | target | accept band |
|---|---|---|---|
| portrait | < 0.9 | 20% | 15–28% |
| near-square | 0.9–1.1 | 35% | 28–45% |
| landscape-mild | 1.1–1.5 | 50% | 45–58% |
| landscape-typical | 1.5–2.5 | 65% | 58–75% |
| landscape-wide | > 2.5 | 80% | 75–90% |

Exempt from this band:

- images inside `.phycat-blockquote` option tables (they keep the readable-minimum gate)
- marked cover sheets (`.concept-map-sheet`, `[data-sheet-role="cover"]`, `[data-cover-sheet="true"]`)

A failed image is fixed by editing job-local CSS in `handout.html` (e.g. an inline `style="width:..."` or a job-local `<style>` override), not by rebuilding. Rationale: a tall narrow figure wastes space at wide widths, and a wide figure is illegible when clamped to a narrow column — width should follow form.

## Rendered Adjacent-Image Side-by-Side Contract

The layout rule above says consecutive crops "must render as one clustered row or grid, not as a vertical stack." The rendered validator now enforces this as a DOM check, closing the gap that the rule used to be a builder instruction with no post-render verification (the 2026-06-17 rule was discarded as "already covered" but only existed as prose). <!-- evolved 2026-06-23 -->

Gate scope:

- For any two sibling `<img>` inside the same `.ocr-image-cluster`, OR inside the same authored `<figure>`:
  - compute both `getBoundingClientRect()`
  - if the top of the lower image ≥ the bottom of the upper image AND there is no horizontal overlap → FAIL (vertically stacked when it should be side-by-side)

The gate does **not** decide which independent images "should" have been clustered — it only verifies that images the builder or author already grouped stayed in the same horizontal row. Builder-missed clustering (two crops that should have been one cluster but weren't) is out of scope for this gate and remains a figure-policy rule concern.
