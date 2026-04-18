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
| `brief.md` | Normalize user intent, defaults, questions resolved, and research gaps |
| `research.md` | Source-backed notes, links, dates, facts, case studies, and claim support |
| `outline.md` | Final section plan before full drafting |
| `article.md` | Source of truth for the written content |
| `handout.html` | Final printable HTML artifact |
| `diagrams/*.svg` | Teaching diagrams generated for the article |

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
