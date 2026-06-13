# Math Rendering: MathJax vs KaTeX

The builder ships with **MathJax 3 (`tex-svg`)** as the default math renderer. This file explains when to keep it and when to switch to **KaTeX**, and how to switch safely. Read this when the rendered math looks too heavy/thick, or when a job needs the most elegant possible typography.

## Default: MathJax tex-svg

`build_faithful_handout_html.py` injects MathJax with `svg: { fontCache: 'none' }` and the pagination script calls `MathJax.typesetPromise(...)` before measuring page height.

Strengths:
- Self-contained: every glyph is an SVG path, so the HTML renders identically anywhere with no font-loading dependency.
- Reliable in headless PDF export.

Weakness observed in practice:
- SVG path fills read as a **heavy/bold** type weight next to body text, especially for `\dfrac` fractions and large symbols. For dense math handouts this looks thick rather than elegant.
- Math glyphs are vector paths, so the math text is **not selectable/searchable** in the PDF.

## When to switch to KaTeX

Switch when the user asks for crisper / more elegant / "高雅" math typography, or selectable math text. KaTeX renders to HTML + web fonts (Computer Modern-style), which is visibly lighter and is the de-facto standard for elegant web math. Trade-off: it loads woff2 fonts from a CDN at render time (one extra wait, but the pagination script already awaits `document.fonts.ready` via the patch below).

## How to switch (the safe way)

KaTeX does not automatically participate in the builder's pagination — the pagination script measures page height, and it must measure **after** math is rendered. If you swap the MathJax `<script>` bootstrap for KaTeX but leave the pagination script calling `MathJax.typesetPromise`, pagination will measure raw `$...$` text and overflow. So two coupled edits are required, applied as a **job-local post-process** (do not edit the shared builder for one job):

1. Replace the MathJax bootstrap with KaTeX CSS + JS + auto-render config:
   ```html
   <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
   <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
   <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
   <script>
   window.KATEX_RENDER_OPTIONS = {
     delimiters: [
       {left: "$$", right: "$$", display: true},
       {left: "$", right: "$", display: false},
       {left: "\\(", right: "\\)", display: false},
       {left: "\\[", right: "\\]", display: true}
     ],
     ignoredTags: ["script","style","code","pre","textarea","math","option"],
     throwOnError: false, strict: false
   };
   </script>
   ```
2. Patch the pagination script's math-wait block so it calls KaTeX and waits for fonts before measuring:
   ```js
   // replace the `if (window.MathJax ...) { typesetPromise(...) }` block with:
   try {
     await new Promise((resolve) => {           // wait for auto-render to load
       const start = Date.now();
       const tick = () => {
         if (window.renderMathInElement || Date.now() - start > 15000) { resolve(); return; }
         setTimeout(tick, 30);
       };
       tick();
     });
     if (window.renderMathInElement) {
       window.renderMathInElement(root, window.KATEX_RENDER_OPTIONS);
     }
     if (document.fonts && document.fonts.ready) {
       await document.fonts.ready;              // KaTeX woff2 fonts must settle
     }
   } catch (_err) { /* keep paginating */ }
   ```

`ignoredTags` must include `math` so KaTeX does not try to re-parse the native MathML inside `<math>` table cells.

## Native MathML

Tables authored with inline `<math>...</math>` (MathML) are rendered by the browser's native MathML Core, not by MathJax or KaTeX. Both renderers leave them alone. Chromium renders MathML Core faithfully in `render_html_to_pdf.py` output. If a job reports broken table glyphs, suspect the MathML, not the LaTeX engine.
