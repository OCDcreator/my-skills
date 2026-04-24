# Autopilot Round Roadmap — `rg3-reviewed-checkpoint`

## Queue

### [NEXT] RG3 - Checkpoint after first review-gated batch

- **Lane**: Review-gated checkpoint
- **Goal**: Summarize what the first review-gated batch changed, whether review assets and health/watch signals were reliable, and whether unattended continuation still makes sense.
- **Constraints**:
  - Avoid broad product changes in the checkpoint
  - Focus on queue status, reviewer signal quality, and blockers
- **Acceptance**:
  - The phase doc explains what was shipped, what reviewers caught, and whether health/watch matched reality
  - Remaining `[QUEUED]` work is clear

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller can mark the overall objective complete.
