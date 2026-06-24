# A4 Four-Column Novak Layout — Measured Coordinates

The default tree layout on A4 portrait (`210mm × 297mm`). Use these coordinates as the starting point; adjust per document.

## Safe Area

- Page: `210 × 297 mm`, `viewBox="0 0 210 297"`.
- Printable safe area: keep all cards ≥ 10mm from every edge → content lives in `x ∈ [10, 200]`, `y ∈ [10, 287]`.
- Card-to-card gap: ≥ 3mm (validator-enforced in the SVG skill; keep it here too for visual cleanliness).
- Text stays ≥ 1mm inside its owning card (automatic via flex padding).

## Vertical Bands

| Band | y range (mm) | Content |
|---|---|---|
| Title | 12 – 29 | Root card |
| Core | 40 – 62 | Core transfer card |
| Branch row | 78 – 96 | 3–5 branch headers |
| Leaf zone | 112 – 218 | Stacked leaf cards per column |
| Method rail | 245 – 276 | Optional bottom summary |

Label shields for the core→branch connectors sit at `y ≈ 70` (in the gap between core and branches).

## Four-Column Geometry (default)

Four equal-ish columns inside the safe area. Column widths chosen so a 3-line formula + note fits.

| Column | x (mm) | width (mm) | center (mm) | branch color |
|---|---|---|---|---|
| Blue   | 12  | 42 | 33  | `--blue` |
| Orange | 58  | 44 | 80  | `--orange` |
| Green  | 106 | 48 | 130 | `--green` |
| Violet | 158 | 40 | 178 | `--violet` |

Leaf cards in each column stack vertically. Standard leaf card height is `20mm`; if a leaf needs a formula *and* a long note, raise it to `28mm`. Stack leaves with ≥ 6mm gaps so the connector lines have room to breathe.

Example blue-column leaf stack (width 42, starting y=112):

| data-node | y (mm) | height | content |
|---|---|---|---|
| leaf-b1 | 112 | 20 | title + formula + note |
| leaf-b2 | 138 | 20 | title + formula + note |
| leaf-b3 | 164 | 20 | title + formula + note |
| leaf-b4 | 190 | 20 | title + note (no formula) |

## Card Sizing Rules

- **Title card**: centered, `width=126, height=17`. Title `font-size: 5.8mm`, subtitle `2.8mm`.
- **Core card**: centered, `width=122, height=22`. Title `4.2mm`, notes `2.55mm`.
- **Branch cards**: `height=18`. Title `3.65mm`, note `2.45mm`.
- **Leaf cards**: `height=20` default (28 if dense). Title `3.8mm`, formula `3.1mm` (auto-scaled), note `2.35mm`.
- **Method rail**: full width minus margins, `height=31`. Title `3.35mm`, steps `2.35mm`.

These font sizes are tuned so body text is not smaller than a footnote at A4 preview — enlarging text first, then adjusting card height, is the correct reaction when a card looks cramped.

## Connector Behavior

Connectors are drawn by `drawEdges()` reading live DOM positions, so the exact pixel path adapts to however the cards actually rendered. But the *logical* structure is:

- `root → core` (stronger stroke)
- `core → each branch`
- `core → method rail` (long central line)
- `branch → first leaf → next leaf → ...` (vertical chain per column)
- cross-links: side-to-side, dashed

You only declare these in the `EDGES` config; coordinates are never typed by hand.
