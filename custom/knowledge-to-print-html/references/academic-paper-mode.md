# Academic Paper Mode

Use this file when `brief.md` sets the artifact mode to `submission-paper`.

This mode is for competition essays, polished exemplar papers, official submission copies, and other paper-like artifacts where a clean argument matters more than teaching-callout density.

## Core Rule

Treat the artifact as a paper first, not as a handout with prettier typography.

That means:

- argument-led structure
- clean submission body
- inline figures/tables near the relevant claim
- disciplined citations
- restrained visual styling

## Separate The Variants Early

If the user wants both:

- annotated coaching copy
- clean formal submission copy

prefer two artifacts or two clearly separated variants.

Do not mix margin-style guidance, “why this works” explanations, audience labels, or process notes into the clean submission body.

## Outline Shape

Prefer:

1. title
2. introduction
3. 3-5 argument-led sections
4. conclusion
5. bibliography / references

Do not default to generic headings like:

- `Evidence`
- `Model`
- `Mechanism`
- `Takeaways`

unless the target format actually calls for them.

Instead, research the target convention and use headings that sound natural for that domain or competition.

## Figures And Tables

Paper-mode figures and tables should behave like evidence exhibits.

Rules:

- place them near the first argument that needs them
- number them when the genre expects numbering
- use concise paper-like captions
- add source notes when the figure summarizes published or extracted data
- avoid dumping all figures into a detached appendix unless the target convention requires it

Useful CSS pattern when using the `refined-minimal` preset:

```html
<main class="minimal-flow paper-body paper-two-column">
  <section class="paper-meta">...</section>
  <section class="paper-abstract">...</section>
  <section class="paper-keywords">...</section>
  <h2>Introduction</h2>
  <p>...</p>
  <figure class="paper-figure">...</figure>
</main>
```

These classes are designed to support:

- paper-like metadata blocks
- numbered figures and tables
- two-column body flow
- CSS-counter section numbering

## Citation Coverage

Do not let the bibliography become decorative.

Each listed source should be used through one or more of:

- body citation
- figure note
- table note
- endnote

Recommended workflow:

- maintain `citation-map.md`, or
- maintain a citation-coverage section in `research.md`

That map should answer:

- which sources support which sections
- which source feeds which figure/table
- which sources only appear in endnotes

If the bibliography is growing fast but the map is thin, stop and fix citation coverage before polishing layout.

## Official Rules

If the paper targets a specific competition, journal, or submission format:

- verify the current official rules from primary sources
- record the rules in `research.md`
- keep dates if the rules might change

Typical items to verify:

- anonymity requirements
- word-count boundaries
- whether bibliography/endnotes/figures count toward the limit
- citation style constraints
- whether footnotes or endnotes are allowed
- whether headings are expected or optional

## Visual Direction

Prefer:

- `refined-minimal`
- or an even plainer, paper-like derivative if the target format is strict

Avoid:

- hero-page composition
- decorative cover ornaments that collide with metadata
- poster-like figure treatments
- thick callout framing in the clean paper copy

When using the existing preset system, prefer adapting `refined-minimal` with paper-specific classes before inventing a brand-new visual language.

## Frequent Failure Pattern

The common trap is trying to keep all of these in one file:

- coaching explanation
- annotated exemplar
- polished submission essay
- reference dump

When that happens, the document usually overflows, the typography gets compressed, and the final artifact reads like a hybrid nobody asked for.

Split early when needed.
