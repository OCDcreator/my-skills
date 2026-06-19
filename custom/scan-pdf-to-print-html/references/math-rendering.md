# Math Rendering: KaTeX Required for Printable HTML

Printable HTML/PDF handouts must use **KaTeX HTML/font rendering** for LaTeX math by default. The local builder may still emit **MathJax 3 (`tex-svg`)** as its bootstrap, but that is an intermediate builder implementation detail, not an acceptable final renderer for math-bearing printable outputs.

MathJax SVG is allowed only when the user explicitly requests MathJax SVG or a fully self-contained offline math file and accepts the heavier formula appearance. Otherwise, apply the safe KaTeX post-process below before final screenshot/PDF export. <!-- evolved 2026-06-17 -->

## Required Default: KaTeX

KaTeX renders to HTML + web fonts (Computer Modern-style), which is visibly lighter and is the required default for polished math handouts. It also keeps math text closer to selectable/searchable text than SVG path glyphs.

The handout must not be delivered with MathJax `tex-svg` output unless the exception above applies.

## Why MathJax tex-svg Is Not the Default

Strengths:
- Self-contained: every glyph is an SVG path, so the HTML renders identically anywhere with no font-loading dependency.
- Reliable in headless PDF export.

Weakness observed in practice:
- SVG path fills read as a **heavy/bold** type weight next to body text, especially for `\dfrac` fractions and large symbols. For dense math handouts this looks thick rather than elegant.
- Math glyphs are vector paths, so the math text is **not selectable/searchable** in the PDF.

## How to enforce KaTeX (the safe way)

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

## Verify KaTeX before delivery

After enforcing KaTeX, render fresh HTML/PDF/screenshot before review and check the actual browser output, not just the source strings. For every math-bearing job, verify:

- no `pageerror` or console syntax error from injected CSS/JS;
- `.katex` nodes exist when the document contains LaTeX math;
- MathJax containers/scripts are absent;
- pagination measured after `renderMathInElement(...)` and `document.fonts.ready`;
- no raw `$...$`, `\(...\)`, or `\[...\]` math remains visible in the rendered body;
- no Markdown blockquote marker `>` has leaked into formula text. If a rendered formula contains `>`, compare against the source: keep legitimate inequalities, but fix quote-prefix leakage before export; <!-- evolved 2026-06-19 -->
- no sheet is marked overflow after the renderer switch.
- no non-cover `.sheet` is contentless; separator-only fragments such as `<hr>` must not be allowed to occupy an A4 page by themselves. <!-- evolved 2026-06-19 -->

Typical failure signatures: `Unexpected token` from malformed injected JavaScript, a post-process that misses the real `</style>` insertion point, or pagination measuring raw math because the old `MathJax.typesetPromise(...)` wait block was left in place. <!-- evolved 2026-06-17 -->

## Native MathML

Tables authored with inline `<math>...</math>` (MathML) are rendered by the browser's native MathML Core, not by MathJax or KaTeX. Both renderers leave them alone. Chromium renders MathML Core faithfully in `render_html_to_pdf.py` output. If a job reports broken table glyphs, suspect the MathML, not the LaTeX engine.
