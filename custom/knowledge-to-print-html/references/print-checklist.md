# Print Checklist

Use this checklist before saying the artifact is ready.

## Page Setup

- Default paper size is `A4`
- Add a print stylesheet and `@page` rule
- Use practical margins for browser printing
- Do not rely on sticky headers, floating sidebars, or viewport-height hero tricks

Suggested baseline:

```css
@page {
  size: A4;
  margin: 14mm 12mm 16mm 12mm;
}
```

## Layout Safety

- Avoid `position: fixed` in the final printable layout
- Avoid multi-column sections unless they print reliably
- Prevent bad splits on figures, callouts, tables, lists, and code blocks
- Keep section openers from leaving only one orphan line on a new page
- Avoid dense micro-card grids as the main content structure
- Protect every text container from inner overflow: long words, URLs, formulas, table entries, labels, and bilingual terms must wrap or break inside their own box

Useful rules:

```css
html {
  overflow-wrap: break-word;
  word-break: normal;
  hyphens: auto;
}

section,
figure,
blockquote,
pre,
table,
.callout,
.case-study {
  break-inside: avoid;
  max-width: 100%;
}

td,
th,
pre,
code,
.callout,
.case-study,
.panel,
.insight,
.memory-strip,
.definition-list > *,
.two-col > *,
.three-col > * {
  overflow-wrap: anywhere;
  word-break: break-word;
}

pre,
code {
  white-space: pre-wrap;
}
```

## Typography

- Body text should remain comfortable when printed
- Contrast should remain strong without relying on backlit screens
- Avoid very thin type, very light gray text, or huge line lengths
- Headings should create rhythm without wasting half-pages
- Do not “solve” layout pressure by shrinking body type or crushing line-height / paragraph spacing

## Visuals

- Prefer SVG diagrams for sharp print output
- Ensure all images have a purpose and caption
- Check SVG visual enclosure: every outer frame / 外框 must contain the labels, pills, icons, and child boxes it groups
- Check compact SVG cards for inner padding and visual balance: the final line must not hug the bottom edge, and left/right spacing must not look obviously uneven
- Avoid dense background textures that make home printing muddy
- If a cover treatment is dramatic, keep the reading pages calmer

## Browser Print Settings

Recommend to the user:

- Paper size: A4
- Scale: 100%
- Background graphics: On
- Headers and footers: Off

## Verification Pass

Before hand-off, confirm:

- `handout.html` opens locally
- no broken image or SVG paths
- long tables do not overflow the printable area
- text inside panels, callouts, table cells, code blocks, tags, and grid items does not overflow or clip inside its own container
- SVG outer frame/card boundaries actually wrap the content they visually claim to contain
- compact SVG text boxes keep healthy inner padding instead of technically fitting while hugging one edge
- code blocks wrap or scroll safely
- important sections do not break in obviously bad places
- references section appears in the final artifact
- the page is not dominated by a dashboard-like card wall
- the reading rhythm still feels comfortable at print size
- learner-facing body text contains no provenance/process notes
