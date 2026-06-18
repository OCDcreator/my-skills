# Evolution Log

## 2026-06-17 — run against a4-novak-svg-cover
- candidate: math-heavy SVG concept maps should render all visible mathematical expressions through one formula-to-vector pipeline instead of mixing raw text math with formula fragments.
  verdict: add_new
  reason: User correction generalized to any math-heavy standalone SVG concept map; existing rules covered glyph safety but not uniform formula rendering.
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first
- candidate: plain-background requests should reject decorative grid/hairline texture unless explicitly requested.
  verdict: add_new
  reason: User correction generalized to SVG cover visual policy; existing rules mentioned hairline fill safety but not background texture policy.
  gate: { g1: pass, g2: new, g3: principle }
  recurrence: first
- candidate: validators must be formula-aware when MathJax/KaTeX fragments are embedded as SVG groups.
  verdict: strengthen
  reason: Dev Eval exposed that the old validators treated MathJax internal rects as cards; validator logic now skips formula internals and checks formula-group layout.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: first

## 2026-06-17 — run against a4-novak-svg-cover
- candidate: card body text and MathJax formula lines in A4 SVG concept maps must remain print-readable and not shrink into footnote-like copy.
  verdict: strengthen
  reason: Existing rules covered padding, centering, and formula-fit mechanics, but not relative readability of body text and formula fragments after layout compression.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: first

## 2026-06-18 — run against a4-novak-svg-cover
- candidate: when card content contains any math, proactively run the MathJax SVG pipeline (formulas.json → render → <g class="formula-fit">) as the default; do not output raw SVG <text> math.
  verdict: strengthen
  reason: User correction "公式没用mathjax". Existing Math Formula Rendering rules said "preferred"/"should go through the pipeline" and "do not mix raw SVG text math with rendered fragments", but a literal read let an all-raw-text map pass (mix-rule satisfied vacuously; "preferred"/"should" read as optional). Elevated the lead paragraph to declare the pipeline the default, proactively-run renderer.
  gate: { g1: pass, g2: strengthen, g3: principle }
  recurrence: first
  dev_eval: pass (validate_concept_map_svg.py + check_concept_map_rendered_layout.py on corrected output)
  provenance: extracted
