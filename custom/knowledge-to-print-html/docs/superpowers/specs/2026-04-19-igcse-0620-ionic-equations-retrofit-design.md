# IGCSE 0620 Ionic Equations Retrofit Design

## Goal

Bring the legacy handout project at `artifacts/knowledge-handout/igcse-0620-ionic-equations/` up to the current `knowledge-to-print-html` contract without rewriting it from scratch. The retrofit must preserve the existing teaching structure, reconstruct the missing preserved-input layer, improve weak print-teaching spots on the page, and complete the strict sequential page-review gate with fresh subagents.

## Current State

- The artifact already contains `brief.md`, `research.md`, `outline.md`, `article.md`, `handout.html`, SVG diagrams, validation output, and a review packet.
- The artifact does **not** contain `raw-input.md`, even though the current contract requires preserving the original user material before normalization.
- The existing `brief.md` captures topic, audience, print constraints, and source choices, but it does not explicitly record the current `research mode` field required by the hardened skill.
- The existing validation output proves the handout can render to A4 and export PDF, but the old project predates the stricter “fresh subagent page review” hand-off discipline.
- Visual inspection of the current page screenshots shows the document is already strong overall, but page 2 and page 4 carry the main layout risk: both teaching diagrams are slightly narrow relative to the surrounding teaching blocks, matching the current heuristic warnings.

## Requirements

### 1. Retrofit the working-file contract

- Add `raw-input.md` to the artifact folder.
- The reconstructed `raw-input.md` must preserve surviving material in a form that is clearly marked as reconstructed from downstream files rather than falsely presented as the exact missing historical source document.
- Update `brief.md` so it explicitly records:
  - `research mode`,
  - why the run is effectively reconstructed from surviving project files,
  - what is known versus inferred about the missing original input.

### 2. Preserve the artifact’s teaching scope

- Keep the current topic: Cambridge IGCSE Chemistry 0620 ionic equations / ionic tests revision.
- Keep the current five-page A4 handout target.
- Preserve the current bilingual teaching pattern: Chinese explanation with key English chemistry terms.
- Preserve the current content spine unless a correction is required for accuracy or page-review quality.

### 3. Improve the weak print-teaching spots

- Focus optimization on page 2 and page 4, where the teaching diagrams are somewhat narrow relative to the available page area.
- Prefer structural rebalancing over type-size compression:
  - enlarge or simplify the teaching diagrams,
  - rebalance neighboring callouts or examples,
  - reduce dashboard-like fragmentation where it weakens the page.
- Do not restyle the whole document unless necessary; changes should be local and purposeful.

### 4. Re-run the modern print-validation pipeline

- Re-run `scripts/validate_print_layout.py` against the artifact’s `handout.html`.
- Re-run `scripts/review_print_pages.py` so the review packet, parity metadata, PDF screenshots, and prompts match the updated handout.
- Keep the output in the artifact’s existing `screens/py-latest/` structure unless the validator rotates it automatically.

### 5. Complete the strict sequential review gate

- Use a fresh subagent for page review.
- Review page 1 first, then page 2, and so on through page 5.
- If any page fails, modify the handout, regenerate validation output and review packet, and restart at the current page before continuing.
- Do not self-approve any page.

### 6. Respect workspace boundaries

- Only touch files inside `artifacts/knowledge-handout/igcse-0620-ionic-equations/` unless a narrow supporting adjustment is strictly required for the retrofit workflow.
- Do not fold this task into unrelated in-progress repo changes such as `SKILL.md`, `evals/*`, or `references/*`.

## Design

### Reconstructed input layer

The missing original source document will be replaced by a transparent reconstruction layer instead of a fake “original” document. `raw-input.md` will be written as a preserved-input proxy built from the surviving `brief.md`, `research.md`, and article framing. It will keep the user-style knowledge list, scope notes, and correction intent in a raw-note shape, while explicitly stating that the original upstream note file was not preserved.

This preserves the hardened workflow’s key benefit: downstream files can still point to a stable preserved-input artifact, and future runs can see what source material shape the handout was rebuilt from.

### Brief normalization update

`brief.md` will be updated rather than replaced. The file will keep its useful topic/audience/scope structure, but add a dedicated research-mode section and a short reconstruction note so the retrofit is honest about provenance while still complying with the current contract.

### Layout refinement strategy

The handout will remain five pages. The main edits will concentrate on page 2 and page 4:

- increase diagram teaching weight so the figures read comfortably at print scale,
- tighten or merge surrounding support blocks when they compete with the figure,
- keep the pages feeling like a study handout rather than a dashboard grid,
- preserve A4 density without shrinking body text.

If other pages show issues during sequential review, only page-local fixes required by the subagent feedback will be applied.

### Validation and review loop

After content/layout edits:

1. run `python scripts/validate_print_layout.py --html artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html`
2. run `python scripts/review_print_pages.py --html artifacts/knowledge-handout/igcse-0620-ionic-equations/handout.html`
3. read the new `page-review-manifest.json`
4. dispatch one fresh subagent per page in order
5. if a page fails, edit the handout and regenerate validation output before continuing
6. after page 5 passes, run one final full-document validation pass

## Risks and Mitigations

- **Missing original notes may blur provenance**  
  Mitigation: explicitly label `raw-input.md` as reconstructed preserved input and document the limitation in `brief.md`.

- **Local polish may accidentally cause page drift elsewhere**  
  Mitigation: keep edits focused, rerun the validator after every substantive page change, and rely on sequential page review rather than visual guesswork.

- **Subagent review may surface additional issues beyond page 2 and 4**  
  Mitigation: accept page-local fixes if they improve hierarchy, density, or print fidelity, but do not broaden the task into a full redesign.

- **Workspace already contains unrelated modified files**  
  Mitigation: avoid editing them and report the boundary clearly in the hand-off.

## Success Criteria

- `artifacts/knowledge-handout/igcse-0620-ionic-equations/raw-input.md` exists and transparently reconstructs the missing preserved-input layer.
- `brief.md` explicitly records the run’s research mode and reconstruction boundary.
- The handout remains a five-page A4 artifact with improved teaching readability on the weak pages.
- The validator passes and regenerates PDF, page screenshots, parity data, and review packet files for the updated handout.
- Fresh subagents review pages 1 through 5 sequentially, with no self-approval by the main agent.
- The final hand-off can point to a modernized artifact folder that satisfies the hardened workflow expectations despite the missing original source note.
