# Autopilot Round Roadmap — `m2-followup-slice`

## Queue

### [NEXT] R2 - Follow-up maintainability / refactor slice

- **Lane**: Maintainability / ownership reduction
- **Goal**: Continue with the next bounded maintainability slice after R1 while staying within the same validation baseline.
- **Constraints**:
  - Build on the prior phase doc instead of starting a new free-form lane
  - Keep behavior unchanged outside the queued slice
- **Acceptance**:
  - Another queued slice lands with validations green

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `m3-checkpoint`.
