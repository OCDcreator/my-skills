# Autopilot Round Roadmap — `q2-gate-cleanup`

## Queue

### [NEXT] Q2 - Finish remaining configured gate cleanup

- **Lane**: Quality gate / cleanup
- **Goal**: Finish the next queued validation hotspot after Q1 without broadening scope.
- **Constraints**:
  - Stay inside directly related files
  - Keep the queue synchronized with actual validation output
- **Acceptance**:
  - The next queued gate or hotspot is resolved with validations green

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `q3-checkpoint`.
