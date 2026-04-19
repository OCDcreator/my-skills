# Autopilot Round Roadmap — `m1-hotspot-slice`

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

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `m2-followup-slice`.
