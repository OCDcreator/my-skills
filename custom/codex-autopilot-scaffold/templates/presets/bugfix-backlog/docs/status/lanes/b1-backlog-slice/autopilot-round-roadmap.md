# Autopilot Round Roadmap — `b1-backlog-slice`

## Queue

### [NEXT] B1 - Highest-priority queued bug or backlog slice

- **Lane**: Bugfix / backlog
- **Goal**: Land the single highest-priority reproducible bugfix or backlog item with bounded scope and recorded validation.
- **Priority entrypoints**:
[[ENTRYPOINT_BULLETS]]
- **Constraints**:
  - Stay inside one queued issue
  - Prefer reproducible fixes and clear acceptance criteria
  - Avoid unrelated cleanup
- **Acceptance**:
  - The queued slice is complete or measurably advanced
  - The phase doc records scope, changed files, and validation results
  - Every configured validation command passes

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `b2-backlog-slice`.
