# Autopilot Round Roadmap — `b2-backlog-slice`

## Queue

### [NEXT] B2 - Next queued bug or backlog slice

- **Lane**: Bugfix / backlog
- **Goal**: Execute the next queued issue after B1 while keeping the same validation baseline.
- **Constraints**:
  - Reuse prior context; do not open a new freestyle lane
  - Keep changes tightly bounded
- **Acceptance**:
  - The next queued issue lands with validations green

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `b3-checkpoint`.
