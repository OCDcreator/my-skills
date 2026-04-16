# Autopilot Round Roadmap

## Queue

### [NEXT] R1 - First maintainability / refactor slice

- **Lane**: Maintainability / ownership reduction
- **Goal**: Choose one high-value, low-risk maintainability slice from the suggested entrypoints and measurably reduce direct ownership, assembly surface, or validation churn without changing behavior.
- **Priority entrypoints**:
[[ENTRYPOINT_BULLETS]]
- **Constraints**:
  - Stay inside one bounded slice
  - Do not create thin wrappers that only rename pass-through ownership
  - Preserve existing runtime behavior
- **Acceptance**:
  - The chosen owner or assembly surface is measurably smaller or clearer
  - The phase doc records scope, changed files, and validation results
  - Every configured validation command passes

### [QUEUED] R2 - Follow-up maintainability / refactor slice

- **Lane**: Maintainability / ownership reduction
- **Goal**: Continue with the next bounded maintainability slice after R1 while staying within the same validation baseline.
- **Constraints**:
  - Build on the prior phase doc instead of starting a new free-form lane
  - Keep behavior unchanged outside the queued slice
- **Acceptance**:
  - Another queued slice lands with validations green

### [QUEUED] R3 - Checkpoint after first refactor batch

- **Lane**: Checkpoint
- **Goal**: Review R1-R2, document what ownership actually moved, and decide whether the preset queue should stop or be manually extended.
- **Constraints**:
  - Do not extend the queue automatically beyond R3
  - Focus on documentation and metrics, not new refactors
- **Acceptance**:
  - The phase doc captures wins, remaining hotspots, and a clear stop/continue recommendation

## Current state

- The current `[NEXT]` is `R1 - First maintainability / refactor slice`.
- Successful rounds must keep the queue synchronized with the phase docs.
