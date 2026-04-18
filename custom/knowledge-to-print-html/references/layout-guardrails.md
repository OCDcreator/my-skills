# Layout Guardrails

These rules are for the final printable handout body, not for the agent's hand-off message.

## Never put these in the page body

The final `handout.html` must not contain workflow chrome or provenance text such as:

- print recommendations inside the teaching content area
- topic labels like `Topic: 7.3 Preparation of salts`
- “双语复习讲义” style packaging text when it adds no learning value
- notes about how the artifact was generated
- source/provenance notes such as `User-provided revision notes`
- process narration like “this handout will answer” or “this page was generated from”

These belong either in:

- the final assistant hand-off message, or
- internal working files such as `brief.md` / `research.md`

## Page density rules

The page should look like a study handout, not a sparse landing page.

- Avoid pages where content only occupies the top half and the lower half is mostly blank.
- A page should normally use most of its vertical space unless there is a deliberate full-page composition reason.
- If a page is too short, do not freeze it as a “hero page”; instead:
  - merge related blocks
  - enlarge teaching visuals
  - introduce a comparison table or worked example
  - rebalance content across neighboring pages

## Section rhythm

- Do not create a new page only for a tiny heading + one short paragraph.
- Keep section openers visually strong, but do not waste half a page on them.
- Prefer fewer, fuller pages over many airy pages.

## Handout first

The artifact is a printable learning document. It should not feel like:

- a web homepage
- a product marketing sheet
- a dashboard
- a mood board

If a visual decision improves “style” but hurts density, continuity, or reading rhythm, reject it.
