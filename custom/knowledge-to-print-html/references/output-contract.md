# Output Contract

## Default Folder Layout

Unless the target project already has its own output convention, write to:

```text
artifacts/knowledge-handout/<slug>/
```

Inside that folder, create:

```text
artifacts/knowledge-handout/<slug>/
├── brief.md
├── research.md
├── outline.md
├── article.md
├── handout.html
├── diagrams/
│   ├── 01-*.svg
│   └── 02-*.svg
└── assets/
    └── optional supporting images
```

## File Roles

| File | Role |
|------|------|
| `brief.md` | Normalize user intent, defaults, questions resolved, research mode, and research constraints |
| `research.md` | Source-backed notes organized by core knowledge point, including links, dates, facts, case studies, and claim support |
| `outline.md` | Final section plan before full drafting |
| `article.md` | Source of truth for the written content |
| `handout.html` | Final printable HTML artifact |
| `diagrams/*.svg` | Teaching diagrams generated for the article |

## Research Working File Minimums

Record the research mode in `brief.md`:

- `comprehensive` when default external research is available
- `constrained` when the user forbids search, the environment is offline, the material is private, or the user explicitly limits sources

If the run is `constrained`, state the reason clearly in `brief.md`.

For each core knowledge point in `research.md`, capture at least:

- an authoritative explanation or mechanism description
- key boundaries, misconceptions, or distinctions
- an example, application, or counterexample
- source URLs or source identifiers
- retrieval date when the information is recent or unstable

## Article Minimum Structure

`article.md` should usually include:

1. `# Title`
2. Short promise / abstract
3. `## Why it matters`
4. `## Core mental model`
5. `## Key concepts` or `## Step-by-step explanation`
6. `## Example` or `## Case study`
7. `## Diagram` or diagram-anchored explanation block
8. `## Common pitfalls`
9. `## Takeaways`
10. `## References`

## Citation Expectations

- Keep research notes in `research.md` even if the final page uses compact references
- Every strong factual claim should be traceable back to `research.md`
- If a fact is recent or unstable, note the retrieval date in `research.md`
- Prefer source URLs over vague source labels
- Traceability belongs in `research.md` and the final `## References` section, not in the learner-facing prose
- Do not write provenance/process notes such as “based on user-provided notes”, “compiled from the draft”, or “generated from the outline” inside `article.md` or `handout.html`

## Image And Diagram Placement

- Store generated diagrams in `diagrams/`
- Use stable relative paths from `article.md` / `handout.html`
- Add captions that state why the figure exists
- Avoid inserting uncaptioned images into the final artifact

## Final Hand-off Contract

The final response after running this skill should state:

- final HTML path
- diagram folder path
- chosen visual preset
- notable print assumptions
