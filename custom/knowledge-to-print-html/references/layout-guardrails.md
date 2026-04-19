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
- generalized variants such as “based on user-provided notes”, “compiled from the draft”, or “organized from the outline”

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

## Card-grid anti-pattern

- Do not use dense multi-card grids as the primary teaching layout.
- A single large callout or case-study panel is fine when it teaches one important point.
- Multiple narrow boxes filled with tiny text fail even if they technically fit.
- If the page starts to feel like a dashboard of cards, rebuild it as sections, a table, a worked example, or a larger diagram-led composition.

## Section rhythm

- Do not create a new page only for a tiny heading + one short paragraph.
- Keep section openers visually strong, but do not waste half a page on them.
- Prefer fewer, fuller pages over many airy pages.
- Do not compress line-height or paragraph spacing just to make a page pass.

## Repair ladder

When a page is too sparse, too crowded, or visually broken, use this order:

1. rebalance content across neighboring pages
2. merge or split related blocks
3. enlarge or simplify the teaching visual
4. replace a card wall with a comparison table or worked example
5. only then make minor spacing adjustments that preserve readable rhythm

Do not treat smaller type, tighter leading, or collapsed paragraph spacing as the primary repair.

## Handout first

The artifact is a printable learning document. It should not feel like:

- a web homepage
- a product marketing sheet
- a dashboard
- a mood board

If a visual decision improves “style” but hurts density, continuity, or reading rhythm, reject it.
