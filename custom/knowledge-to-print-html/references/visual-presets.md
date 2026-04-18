# Visual Presets

These are the default visual directions for `knowledge-to-print-html`.

The goal is not "fancy for its own sake". The page must teach clearly, print cleanly, and still feel intentionally designed.

## `editorial-atlas` (Default)

Best for:

- General knowledge explainers
- Educational handouts
- Rich tutorial pages
- Concept + case study pages

Characteristics:

- Editorial / magazine-like rhythm
- Warm neutral background
- Serif display or section headings + clean sans-serif body
- One restrained accent color
- Strong chapter openers and figure captions
- Diagrams feel precise, not playful

Use this when the user says:

- “图文并茂”
- “漂亮一点但要适合打印”
- “像一本好看的讲义”

Implementation hint:

- Start from `minimalist-ui` constraints
- Then let `frontend-design` strengthen only the cover, section headers, and special callouts

## `refined-minimal`

Best for:

- Thoughtful essays
- Higher-end print handouts
- Quiet, premium, book-like pages

Characteristics:

- More whitespace
- Fewer visual flourishes
- Strong typographic contrast
- Low-noise callouts
- Little to no decorative texture

Use this when the content is serious, abstract, or concept-heavy and should feel calm.

Implementation hint:

- Stay very close to `minimalist-ui`
- Use `frontend-design` sparingly

## `technical-briefing`

Best for:

- Technical explainers
- Systems/process breakdowns
- Engineering or operational topics

Characteristics:

- More structured layout
- Clear labels and callouts
- Slightly stronger mono / schematic cues
- Diagrams lead the page logic
- Less editorial softness, more analytical confidence

Use this when the user wants the page to feel like a polished internal whitepaper or technical briefing note.

## Selection Rules

- If the user gives no style direction, use `editorial-atlas`
- If the topic is highly technical, prefer `technical-briefing`
- If the topic is reflective, essay-like, or premium, prefer `refined-minimal`
- If the user wants a real product or brand reference, route through `design-reference-router` instead of forcing one of these presets

## Implementation Hints

- Default type system: one display family + one body family, maximum
- Default palette: warm neutrals plus one accent
- Default diagrams: SVG first
- Default layout: document rhythm first, dramatic cover second
- Avoid dark full-page backgrounds unless the user explicitly asks for them
