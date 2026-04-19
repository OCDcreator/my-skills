# Diagram Guardrails

These rules apply to all teaching diagrams, flowcharts, SVG explanation graphics, and card-like teaching blocks that carry explanatory text.

## Readability comes before decoration

- Every diagram must teach a concept, not just decorate the page.
- If a diagram is too small to read comfortably when printed, it fails.
- If the diagram needs zooming to understand, it fails.

## Size expectations

- A primary teaching diagram should usually occupy a strong portion of the column or page.
- Do not shrink a dense flowchart into a small inset just to “fit everything”.
- If the diagram contains multiple boxes, arrows, and labels, enlarge it or split it.

## Text inside diagrams

- Text must stay inside its boxes.
- Compact SVG cards and medium structured frames need healthy inner padding, not just zero overflow.
- Labels must not overlap arrows or neighboring boxes.
- Avoid over-dense microtext.
- If the diagram needs many sentences, move some explanation into the body and keep only the essential labels in the SVG.

## Visual enclosure integrity

- The visual enclosure must match the meaning: if an outer frame, card, or 外框 introduces a group, every related text label, pill, icon, and child box must sit inside that frame.
- Do not let an outer frame stop above the final pill or label. This fails even when the SVG image itself stays inside the page and no DOM overflow is reported.
- In compact SVG text boxes and medium structured frames, the last line or child box must not hug the bottom edge, and the rightmost content must not sit visibly tighter than the left edge.
- Visual balance matters: a box can still fail even when the text remains technically inside, if the inner padding looks obviously uneven.
- Prefer enlarging the frame, rebalancing the grouped items, or splitting the group over hiding overflow or shrinking labels.

The same readability rule applies to CSS callouts or card-like explanation blocks:

- text must not overflow the box
- text must not become tiny just to preserve a side-by-side layout
- if the block needs too much prose, turn it into a normal section, table, or worked example instead

## When to split a diagram

Split the figure into two diagrams when any of the following happens:

- labels become too small
- text starts overflowing boxes
- the diagram needs two different teaching goals
- the diagram is being reduced just to preserve a side-by-side layout

## Figure placement

- Do not bury a key diagram as a small decorative object in a busy grid.
- Give important diagrams enough surrounding space to breathe, but not so much that the rest of the page collapses into empty whitespace.
- The figure and its caption should feel like part of the lesson flow.
