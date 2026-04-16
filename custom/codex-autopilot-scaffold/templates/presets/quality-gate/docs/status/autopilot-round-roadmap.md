# Autopilot Round Roadmap

## Queue

### [NEXT] Q1 - Recover the first configured gate

- **Lane**: Quality gate / recovery
- **Goal**: Fix the highest-impact failing or noisy configured validation gate with the smallest behavior-preserving change.
- **Priority entrypoints**:
[[ENTRYPOINT_BULLETS]]
- **Constraints**:
  - Stay inside the first justified hotspot
  - Do not lower coverage or remove valuable assertions
  - Do not introduce unrelated refactors
- **Acceptance**:
  - The targeted configured gate is green or measurably improved
  - The phase doc records what was recovered and what remains
  - Every configured validation command passes after the round

### [QUEUED] Q2 - Finish remaining configured gate cleanup

- **Lane**: Quality gate / cleanup
- **Goal**: Finish the next queued validation hotspot after Q1 without broadening scope.
- **Constraints**:
  - Stay inside directly related files
  - Keep the queue synchronized with actual validation output
- **Acceptance**:
  - The next queued gate or hotspot is resolved with validations green

### [QUEUED] Q3 - Checkpoint after quality-gate recovery

- **Lane**: Checkpoint
- **Goal**: Review the recovery batch, capture remaining hotspots, and decide whether unattended continuation still has a good cost/benefit ratio.
- **Constraints**:
  - Do not extend the queue automatically beyond Q3
  - Focus on documentation and metrics instead of new code work
- **Acceptance**:
  - The phase doc clearly records recovered gates, remaining issues, and the stop/continue recommendation

## Current state

- The current `[NEXT]` is `Q1 - Recover the first configured gate`.
- Successful rounds must keep the roadmap, lane map, and phase docs aligned.
