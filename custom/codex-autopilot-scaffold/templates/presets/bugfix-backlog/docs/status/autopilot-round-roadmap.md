# Autopilot Round Roadmap

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

### [QUEUED] B2 - Next queued bug or backlog slice

- **Lane**: Bugfix / backlog
- **Goal**: Execute the next queued issue after B1 while keeping the same validation baseline.
- **Constraints**:
  - Reuse prior context; do not open a new freestyle lane
  - Keep changes tightly bounded
- **Acceptance**:
  - The next queued issue lands with validations green

### [QUEUED] B3 - Checkpoint after first backlog batch

- **Lane**: Checkpoint
- **Goal**: Review B1-B2, record shipped fixes, remaining queued work, and whether unattended continuation is still worthwhile.
- **Constraints**:
  - Do not extend the queue automatically beyond B3
  - Focus on documentation and backlog state instead of new code work
- **Acceptance**:
  - The phase doc captures completed slices, remaining risks, and the stop/continue recommendation

## Current state

- The current `[NEXT]` is `B1 - Highest-priority queued bug or backlog slice`.
- Successful rounds must keep the roadmap and phase docs aligned.
