# Scan Pdf To Print Html Kami Default Layout Design

## Goal

Make `custom/scan-pdf-to-print-html` generate a **Kami-based A4 handout by default** instead of using its current custom inline visual system.

This pass has three linked goals:

- replace the current default page language with a stable `Kami` print-first layout kernel,
- make table content default to **horizontal center + vertical center**,
- define a **faster pass-first review workflow** based on the sequential page-review gate already used by `knowledge-to-print-html`.

The outcome should feel like one coherent print system:

- OCR and source fidelity still belong to `scan-pdf-to-print-html`,
- page tone, rhythm, tables, and hierarchy default to `Kami`,
- review no longer depends on ad-hoc manual eyeballing before hand-off.

## Current State

- `scripts/build_faithful_handout_html.py` owns the full HTML/CSS generation as one inline string block.
- The current output is already usable for A4 and source-faithful rendering, but its visual language is hand-rolled and separate from the local `Kami` design system.
- Tables currently use:
  - `th`: left-aligned,
  - `td`: top-aligned.
- Math rendering now works through `MathJax SVG`, which fixed the previous export visibility problem.
- Image borders were already removed from the default output.
- Review is partially validated by tests and artifact rendering, but there is no formal, default, page-by-page review protocol inside this skill yet.

## Scope

### In scope

- make `Kami` the default visual kernel for generated HTML,
- center table content horizontally and vertically by default,
- preserve source-fidelity behavior and current OCR assumptions,
- codify a review path that combines:
  - local preflight checks,
  - artifact rendering,
  - sequential fresh-subagent page review,
- add or update tests that lock the new default output contract.

### Out of scope

- changing Doc2X parsing behavior,
- changing OCR transcript semantics,
- rewriting source content for better pedagogy,
- making `Kami` optional in this pass,
- importing the full `Kami` component catalog into every handout page,
- changing `knowledge-to-print-html` itself.

## Design Decision

### Chosen approach

Use `Kami` as the **default style kernel**, but **snapshot the required token and layout subset into the skill itself** instead of reading the external `open-design` repo at runtime.

That means:

- `Kami` is the design source of truth,
- `scan-pdf-to-print-html` keeps its own local, reproducible default assets,
- the generator does not silently depend on another repo being present on disk.

### Why this approach

- The user wants `Kami` to be the actual default output system, not just a visual reference.
- Runtime reads from `C:\Users\lt\Desktop\Write\open-source-project\...` would make this skill fragile, environment-specific, and harder to review.
- A vendored snapshot keeps the generator deterministic and makes test expectations stable.
- The skill still remains explicitly `Kami`-based because the local token block and layout rules are derived from the `Kami` package and documented as such.

### Rejected alternatives

#### Runtime import from external `Kami` files

Rejected because:

- it makes the skill depend on a sibling repo path,
- it weakens portability,
- it complicates tests and review reproducibility,
- it makes “default behavior” depend on workstation state rather than the skill itself.

#### Keep the current generator and only borrow a few colors

Rejected because:

- that would still leave a separate visual system in place,
- the user explicitly wants `Kami` treated as the real layout/style system,
- it would not produce a consistent default “paper” identity.

## Requirements

### 1. Kami must be the default kernel

Generated HTML must default to `Kami`-style print language:

- parchment page canvas,
- ink-blue restrained accent,
- serif-led hierarchy,
- warm neutral surfaces and borders,
- soft ring / whisper elevation only,
- no cool-gray drift,
- no hard UI-dashboard styling.

The output should still read as a document, not as a product webpage.

### 2. OCR-specific structure must remain intact

The layout refresh must not remove or blur the existing OCR-specific structure:

- `sheet` page container,
- source label in header,
- source page number,
- document title,
- transcript body,
- footer page numbering.

`Kami` replaces the visual kernel, not the content contract.

### 3. Tables default to horizontal and vertical centering

All generated table header and body cells should default to:

- horizontal center alignment,
- vertical middle alignment.

This applies to:

- plain text,
- formulas,
- inline images,
- mixed table rows such as “文字语言 / 符号语言 / 图形语言”.

The first implementation should prefer deterministic consistency over smart exceptions. Long textual cells may still be centered in this pass.

### 4. Formula export reliability must be preserved

The current `MathJax SVG` export path is now part of the default contract and must not regress.

Generated HTML must continue to use the SVG-based MathJax path so formulas remain visible in:

- headless screenshots,
- PDF export,
- page-review artifacts.

### 5. Image cells must remain clean

Image rendering rules already fixed in the current generator must remain true:

- no default image frame,
- no white image card around OCR-extracted figures,
- centered placement inside the cell,
- bounded size so diagrams do not break page rhythm.

### 6. Review must optimize for first-pass success

The review path should not start with a subagent on a low-quality first draft.

The skill should enforce a three-stage gate:

1. **Main-agent preflight**
   - unit tests,
   - structure checks,
   - artifact rebuild,
   - local visual sanity checks for formulas, tables, borders, and overflow.
2. **Generated review packet**
   - page screenshots,
   - print PDF,
   - parity data when available.
3. **Sequential fresh-subagent review**
   - page 1 first,
   - fix page 1 before page 2,
   - continue only after the current page passes.

This mirrors the proven `knowledge-to-print-html` page-review discipline while keeping the OCR-specific preflight narrow and efficient.

## Proposed Implementation Surfaces

### `custom/scan-pdf-to-print-html/scripts/build_faithful_handout_html.py`

This is the primary implementation surface.

Planned changes:

- replace the current custom `:root` and page CSS with a `Kami`-derived local kernel,
- keep OCR-specific document structure generation in place,
- switch table rules to centered alignment,
- preserve MathJax SVG bootstrap,
- preserve image cleanup behavior,
- add comments only where they clarify the split between vendored `Kami` kernel and OCR-specific page rules.

### `custom/scan-pdf-to-print-html/tests/test_build_faithful_handout_html.py`

Add or update regression coverage for:

- table cell center alignment being present in generated HTML,
- `MathJax SVG` bootstrap remaining the active path,
- image border suppression remaining active,
- page split / A4 behavior remaining intact.

### `custom/scan-pdf-to-print-html/SKILL.md`

Update the skill contract so it explicitly says:

- the default page kernel is `Kami`,
- the default review path uses a sequential review gate inspired by `knowledge-to-print-html`,
- local preflight comes before subagent page review.

### Optional local asset file

If the CSS block becomes too large or too hard to maintain inline, extract the `Kami` default kernel into a local asset under the skill folder, then load it during HTML generation.

If this extraction happens, the asset must live inside the skill repo, not in the sibling `open-design` repo.

## Data Flow

### Content flow

1. Doc2X or other OCR stage produces `source-transcript.md`
2. `build_faithful_handout_html.py` converts transcript markdown into semantic HTML sections
3. the generator wraps that structure in the local `Kami`-based page kernel
4. formulas render through `MathJax SVG`
5. screenshots and PDF are generated from the resulting HTML

### Review flow

1. run generator
2. run unit and structure checks
3. rebuild real artifact
4. inspect representative output for known failure classes
5. generate page-review packet
6. review page 1 with a fresh reviewer
7. fix and revalidate page 1 until pass
8. move forward one page at a time
9. run final validation before hand-off

## Error Handling And Failure Modes

### Missing external `Kami` repo

This must not block normal generation, because the runtime path will not depend on the external repo once the local snapshot is created.

The implementation may keep provenance comments pointing back to the original `Kami` source files, but runtime should remain fully local.

### Visual drift after token import

Risk:

- a raw token paste may make OCR layouts too decorative, too spacious, or too weakly structured for transcript-heavy pages.

Mitigation:

- keep OCR-specific layout rules separate from the vendored token layer,
- treat `Kami` as the visual kernel, not as a full page-template replacement,
- verify with real OCR artifacts rather than token-only tests.

### Centered long text becoming hard to scan

Risk:

- long prose cells may read less naturally when centered.

Mitigation:

- keep the first pass deterministic and reviewable,
- if real artifacts show systematic readability issues, add a future explicit rule for “long-prose cell exceptions” instead of hidden heuristics now.

### Review loop cost growing too much

Risk:

- full subagent review on every low-quality draft wastes time.

Mitigation:

- add a strict main-agent preflight so subagent review starts from a cleaner artifact,
- keep the subagent gate page-local and sequential,
- only re-review the current page after targeted fixes.

## Testing Strategy

### Unit / generator tests

Required:

- page split output remains stable,
- A4 shell remains present,
- `MathJax SVG` remains active,
- image border stays removed,
- table alignment defaults are present in generated HTML.

### Real artifact verification

Required:

- rebuild at least one existing OCR sample artifact,
- export screenshot and PDF,
- confirm formulas are visible,
- confirm table cells visually center content,
- confirm image cells remain frameless.

### Review-gate verification

Required:

- document the review sequence in the skill,
- ensure the page-review process is explicit and repeatable,
- use fresh reviewer subagents sequentially, not parallel self-approval, when the environment allows it.

## Success Criteria

- `scan-pdf-to-print-html` produces a `Kami`-based page by default.
- The output still preserves OCR/source fidelity behavior.
- Table content is horizontally and vertically centered by default.
- Formula export remains visible in screenshots and PDFs.
- Image cells stay clean, without default frames.
- The review workflow becomes easier to pass on the first try because obvious layout failures are filtered before the sequential subagent review gate.

## Implementation Notes For The Next Step

- Prefer a **local `Kami` snapshot** over runtime cross-repo dependency.
- Keep `Kami` token rules and OCR-specific layout rules clearly separated.
- Treat review efficiency as a product feature, not just a QA afterthought.
