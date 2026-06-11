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
