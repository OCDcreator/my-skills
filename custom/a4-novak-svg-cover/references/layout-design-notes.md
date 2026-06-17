# concept-map.svg calculated layout design

Goal: keep the A4 portrait Novak/tree concept map readable in SVG, HTML, PDF, and common viewers.

Design constraints:

- Canvas stays `210mm x 297mm`, `viewBox="0 0 210 297"`.
- All visual styles are inline presentation attributes; the SVG must not depend on a `<style>` block.
- Card rectangles must not overlap and must keep at least `3mm` of separation.
- Use four equal tree columns inside the printable safe area:
  - column 1: `x=12`, `w=42`
  - column 2: `x=58`, `w=44`
  - column 3: `x=106`, `w=48`
  - column 4: `x=158`, `w=40`
- Branch headers sit on one row near the top. Leaf cards stack vertically inside each column.
- The method rail stays at the lower-left as a separate summary block.
- The visual hierarchy remains: root -> core transfer -> four branches -> leaves / method rail.
- Avoid unstable mathematical glyphs that may become tofu/boxed missing glyphs in SVG/PDF viewers:
  - `⇄`, `→`, `′`, `₀`, `₁`, `₂`, `·`, `–`
- Replace those with stable text:
  - `对应`, `到`, `f'(x0)`, `x0/x1/x2`, ASCII hyphen.

Validation:

- Run `py -3 product\2026-06-17-daoshu-qiexian-html\validate_concept_map_svg.py product\2026-06-17-daoshu-qiexian-html\concept-map.svg --min-gap-mm 3`.
- Render `concept-map-preview.png` with Playwright.
