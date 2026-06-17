# Session Lessons: A4 Novak SVG Cover

These are the concrete lessons captured from the derivative/tangent handout job.

- A4 root must be exact: `width="210mm" height="297mm" viewBox="0 0 210 297"`.
- Do not depend on `<style>`, CSS variables, or class-only styling; some viewers fall back to black fills.
- Add explicit `fill="none"` to connector paths and hairlines.
- Avoid risky glyphs: `⇄`, `→`, `′`, `₀`, `₁`, `₂`, `·`, `–`.
- Replace with stable Chinese/ASCII such as `对应`, `到`, `f'(x0)`, `x0/x1/x2`.
- Remove generic subtitle/footer copy like `A4 portrait concept map` unless the user asks for branding.
- Four measured columns worked well on A4 portrait: keep cards inside a 10mm safe area and maintain at least 3mm between cards.
- Draw all connector paths before cards/text.
- Use light strokes and low opacity for lines; cards and label shields should visually hide line segments behind text.
- Card text should be centered as a group both horizontally and vertically.
- Browser geometry checks catch issues XML checks cannot: rendered text overflow, center drift, line-text crossings, and stroke weight.
- In handout HTML, generic transcript CSS may clamp all images. The cover needs dedicated CSS with `width/height: 210mm/297mm`, `max-width: none !important`, and a separate first sheet.
- After the cover, force every lecture/chapter heading that should begin a print page onto a fresh sheet.
