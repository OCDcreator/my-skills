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

Useful rules:

```css
section,
figure,
blockquote,
pre,
table,
.callout,
.case-study {
  break-inside: avoid;
}
```

## Typography

- Body text should remain comfortable when printed
- Contrast should remain strong without relying on backlit screens
- Avoid very thin type, very light gray text, or huge line lengths
- Headings should create rhythm without wasting half-pages

## Visuals

- Prefer SVG diagrams for sharp print output
- Ensure all images have a purpose and caption
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
- code blocks wrap or scroll safely
- important sections do not break in obviously bad places
- references section appears in the final artifact
