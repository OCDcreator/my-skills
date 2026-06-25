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

Post-render check only — it does NOT change the builder's existing mm clamp (34/48/64/72mm). The validator computes each non-exempt image's aspect ratio from `naturalWidth/naturalHeight` and checks its rendered width against a band expressed as a fraction of the `.sheet-body` content width. <!-- redesigned 2026-06-23 -->

The target width is a **smooth function of aspect ratio** (no hard jump at class boundaries), and is **capped by the image's own natural width** so a figure is never enlarged beyond its native pixel resolution (which would blur it). This applies **per image, independently** — including each sibling in a multi-image `<figure>`/cluster. A side-by-side row does NOT justify enlarging each image to fill the row; each image keeps the width it would have alone, and the row wraps (`flex-wrap:wrap`) if the per-image widths total more than 100%. Control points (interpolated linearly between): <!-- evolved 2026-06-23 -->

| aspect (w/h) | target |
|---|---|
| ≤ 0.7 | ~20% |
| 0.9 | ~27% |
| 1.0 (square) | 30% |
| 1.2 | 35% |
| 1.5 | 45% |
| 2.0 | 58% |
| 2.5 | 68% |
| ≥ 3.5 | ~78% |

Each image's effective target = `min(smooth_target(aspect), natural_width_%_of_body)`. The accept band is target ±7 percentage points (with a ±4pp "near-is-exempt" grace on each edge enforced by the validator). Multi-image rows are judged per-sibling (each image against its own band), NOT by aggregate row width. **Oversubscribed rows**: when the siblings' independent target widths sum to more than ~92% of body width, the row is treated as "over-subscribed" — the group prefers staying on ONE row over wrapping, each sibling is proportionally shrunk to fit (~95% total), and the independent-width rule is EXEMPTED for every sibling in that group (use `flex-wrap:nowrap` on the figure so it cannot wrap). The threshold is 92% (not 100%) deliberately: the old 100% boundary trapped rows whose total sat at 96–99% — too wide to fit one row at each image's band, but not yet exempt, so a weak model ping-ponged between "enlarge for C26 → wrap → FAIL C27" and "shrink for C27 → FAIL C26". The 8pp buffer keeps the two gates' targets from being unsatisfiable at once. Rationale: near-square figures (ar≈1) read fine at ~30% — pushing them to 50% (or enlarging each row sibling to fill the row) wastes space and enlarges them past native resolution; only genuinely wide figures (ar>1.5) need a wide column. The cap prevents upscaling blurry crops. <!-- evolved 2026-06-23; threshold relaxed 92% 2026-06-25 -->

Examples: ar=1.0 → ~30% (band 23–37%); ar=1.13 → ~33%; ar=1.5 → 45%; ar=2.5 → 68%.

Exempt from this band:

- images inside `.phycat-blockquote` option tables (they keep the readable-minimum gate)
- marked cover sheets (`.concept-map-sheet`, `[data-sheet-role="cover"]`, `[data-cover-sheet="true"]`)

"Near is exempt" tolerance: the validator applies a small ±4 percentage-point grace on each band edge, so an image off by a few percent (e.g. a multi-image row where each sibling legitimately shares the band) still passes. When two hard contracts conflict, do not fight both to the letter — if one target is essentially met, let it win. <!-- evolved 2026-06-23 -->

A failed image is fixed by editing job-local CSS in `handout.html` (e.g. an inline `style="width:..."` or a job-local `<style>` override), not by rebuilding. Rationale: a tall narrow figure wastes space at wide widths, and a wide figure is illegible when clamped to a narrow column — width should follow form.

### Figure-Boundary Trade-Off vs Trailing-Blank Rule

This width band can conflict with the sheet trailing-blank rule (`validate_sheet_bottom_margin.py`, ≤10% of body). When the first content block on the *next* sheet is a figure whose image satisfies its width band AND that block is too tall to move up into the current sheet's trailing blank (or almost fits — within ~8% of the gap), the trailing blank on the current sheet is the **unavoidable cost of the image-width rule**. The bottom-margin validator exempts such a sheet rather than letting the two hard contracts fight: the rule whose target is met (image width) wins over the rule whose target cannot be met without breaking it (trailing blank). This mirrors the existing blockquote/lecture-break exemptions. <!-- evolved 2026-06-23 -->

**In-blockquote boundary images are never a movable-figure defect (evolved 2026-06-25).** When the next sheet's first block is a `.phycat-blockquote` that *contains* an image, `validate_sheet_bottom_margin.py`'s `analyzeFigureBoundary` skips it (returns null) and the sheet falls through to the blockquote exemption. Reason: narrowing an in-quote image cannot move the protected blockquote — the rebalance (`isCarryForwardProtected`) refuses to pull a blockquote up — so a "narrow the figure and it will travel into the gap" hint is a false positive that sends the model into an unbounded shrink/reflow loop. This was a real defect on a vector-geometry handout where every 例题 blockquote with a diagram landed at a page boundary.

**The conflict band and the shrink↔enlarge loop (evolved 2026-06-25).** Both gates share the same smooth-target formula, but the bottom-margin gate's `bandFloorFrac` (= `max(0.12, target-0.07) - 0.04`) and the rendered-contract gate's pass edge (= `lo - 0.04` where `lo = max(0.12, target-0.07)`) sit at the same pixel value, and rendering rounding creates a ~1pp window where the two gates emit **contradictory** single-image hints: bottom-margin says "narrow to ~X% floor", width-band says "TOO SMALL (enlarge)" at ~X%. A figure in that window is in the **conflict band** — the width-band gate (fidelity) wins. Do NOT shrink past the band floor to chase the trailing-blank hint; stop after one shrink/enlarge round, and if both gates still fire, that sheet is the authorized fidelity-exempt gap. Editing figure widths one at a time never converges here because each change reflows the document and re-flags a different sheet — batch all narrowings + enlargements into one CSS block per iteration instead (see SKILL.md Markdown-Source Mode step 8).

## Rendered Adjacent-Image Side-by-Side Contract

The layout rule above says consecutive crops "must render as one clustered row or grid, not as a vertical stack." The rendered validator now enforces this as a DOM check, closing the gap that the rule used to be a builder instruction with no post-render verification (the 2026-06-17 rule was discarded as "already covered" but only existed as prose). <!-- evolved 2026-06-23 -->

Gate scope:

- For any two sibling `<img>` inside the same `.ocr-image-cluster`, OR inside the same authored `<figure>`:
  - compute both `getBoundingClientRect()`
  - if the top of the lower image ≥ the bottom of the upper image AND there is no horizontal overlap → FAIL (vertically stacked when it should be side-by-side)

The gate does **not** decide which independent images "should" have been clustered — it only verifies that images the builder or author already grouped stayed in the same horizontal row. Builder-missed clustering (two crops that should have been one cluster but weren't) is out of scope for this gate and remains a figure-policy rule concern.
