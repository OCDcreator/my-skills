# Visual Presets

These are the built-in visual directions for `knowledge-to-print-html`.

The goal is not "fancy for its own sake". Every preset must teach clearly, print cleanly, and preserve the strict layout guardrails.

Use this file to choose the direction. Use `templates/presets/README.md` to copy the matching starter `handout.html` and `style.css`.

Each preset folder also includes a committed `preview.png` screenshot for quick human visual comparison.

## Preset Contract

Across all presets:

- keep A4 `.sheet` pages as the layout unit
- keep readable paragraph rhythm even when the page is dense
- do not simulate "editorial rhythm" with a dashboard of small cards
- do not use microtext boxes to squeeze more content onto the page
- do not use dark full-page backgrounds unless the user explicitly asks for them
- keep diagrams SVG-first, print-sharp, and protected by the SVG enclosure rules
- keep the final artifact document-like, not product-page-like

## Built-In Presets

| Preset | Default use | Visual character | Template folder |
|---|---|---|---|
| `editorial-atlas` | General explainers, rich tutorial pages, concept + case study pages | Magazine-like rhythm, warm paper, restrained accent, strong captions | `templates/presets/editorial-atlas/` |
| `refined-minimal` | Abstract, serious, essay-like, premium handouts | Quiet book-like pages, high typographic contrast, low visual noise | `templates/presets/refined-minimal/` |
| `technical-briefing` | Systems, processes, engineering, operational topics | Structured labels, schematic grids, confident mono details | `templates/presets/technical-briefing/` |
| `exam-workbook` | Exam revision, worked examples, practice-heavy lessons | Clear question blocks, answer spaces, pitfalls, mark-scheme rhythm | `templates/presets/exam-workbook/` |
| `lab-notebook` | Science, experiments, observations, methods, field notes | Notebook grid, observation tables, hypothesis/result panels | `templates/presets/lab-notebook/` |
| `blueprint-briefing` | Architecture, software, protocols, mechanisms, specs | Print-safe blueprint cues, whiteprint grid, mono annotations | `templates/presets/blueprint-briefing/` |
| `concept-map` | Relationships, taxonomies, mental models, topic overviews | Diagram-led map, central thesis, connected clusters, short prose | `templates/presets/concept-map/` |
| `field-guide` | Classification, comparison, biology/history/culture primers | Specimen cards, annotated features, practical recognition cues | `templates/presets/field-guide/` |

## Selection Rules

- If the user gives no style direction, use `editorial-atlas`.
- If the user asks for "简洁", "高级", "论文感", "像书页", or a calm premium feel, use `refined-minimal`.
- If the topic is technical, process-heavy, or system-like, prefer `technical-briefing`.
- If the output is for an exam, worksheet, past-paper drill, or revision practice, use `exam-workbook`.
- If the lesson depends on experiment logic, observation, variables, or lab records, use `lab-notebook`.
- If the user asks for schematic, engineering drawing, API/protocol, or architecture feel, use `blueprint-briefing`.
- If the learner mainly needs to see relationships between ideas, use `concept-map`.
- If the learner needs to identify, classify, compare, or recognize examples in the world, use `field-guide`.
- If the user wants a real product or brand reference, route through `design-reference-router` instead of forcing one of these presets.

## Implementation Rules

1. Choose the preset before writing `handout.html`.
2. Start from the matching template folder:
   - copy `templates/presets/<preset>/handout.html`
   - copy `templates/presets/<preset>/style.css`
   - copy or inline `templates/presets/_shared/print-base.css`
3. Replace the sample content with the drafted `article.md` content.
4. Keep the template's A4 `.sheet`, print stylesheet, wrapping rules, and break-avoid rules.
5. Adapt the section mix to the content; do not force every sample block to remain.
6. Run the normal validator and sequential page-review loop after content replacement.

## External Style Sources

The presets intentionally adapt ideas from the repo's broader design skills, but they are print-safe versions, not raw web/slide themes:

- `minimalist-ui` informs `refined-minimal`.
- `frontend-design` informs the general polish standard.
- `theme-factory` informs the idea of named theme selection.
- `html-ppt` theme families inform the broader palette vocabulary.
- `design-reference-router` remains the path for explicit brand/product references.

## Preset-Specific Notes

### `editorial-atlas`

Best for general knowledge explainers.

- Use a warm neutral background and one restrained accent.
- Pair serif display headings with a clean sans-serif body.
- Prefer a chapter opener, a figure-led middle section, and one strong teaching callout.
- Keep diagrams precise, not playful.

### `refined-minimal`

Best for serious or reflective topics.

- Use more whitespace, but not sparse half-pages.
- Let hierarchy come from typography, rules, and margins rather than boxes.
- Use only one or two quiet callouts per page.
- Avoid decorative textures and heavy backgrounds.

### `technical-briefing`

Best for systems and process breakdowns.

- Use labeled sections, short paragraphs, and compact evidence tables.
- Let diagrams lead the page logic.
- Keep mono details readable and never smaller than print-safe body text.
- Use grid lines sparingly; the document should feel analytical, not busy.

### `exam-workbook`

Best for revision and practice.

- Put the worked example and the misconception check before decorative material.
- Use answer lanes, checkpoints, and mark-scheme cues.
- Keep spaces large enough for handwritten notes when printed.
- Avoid turning every paragraph into a boxed card.

### `lab-notebook`

Best for experimental or observational content.

- Use hypothesis, variables, method, observation, and interpretation panels.
- Prefer tables and labeled diagrams over prose-heavy cards.
- Keep ruled or grid texture subtle so home printing stays clean.
- Put safety or boundary notes in concise callouts.

### `blueprint-briefing`

Best for mechanisms, specs, and architecture.

- Use print-safe white background with blueprint-like linework, not a dark blueprint page.
- Use mono labels, numbered components, and specification tables.
- Keep the primary diagram large.
- Split dense schematics rather than shrinking labels.

### `concept-map`

Best for relationship-heavy lessons.

- Use a central claim and 3-5 surrounding clusters.
- Keep node labels short; move explanations into nearby prose.
- Avoid spaghetti arrows and tiny text.
- If the map needs more than one learning goal, split it across pages.

### `field-guide`

Best for classification and recognition.

- Use specimen/example blocks with "look for", "confuse with", and "why it matters" cues.
- Prefer comparison tables and annotated feature lists.
- Use color for classification sparingly.
- Keep examples concrete and captioned.
