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
