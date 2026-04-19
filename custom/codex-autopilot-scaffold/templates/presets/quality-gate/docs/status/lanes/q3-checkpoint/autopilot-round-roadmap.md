# Autopilot Round Roadmap — `q3-checkpoint`

## Queue

### [NEXT] Q3 - Checkpoint after quality-gate recovery

- **Lane**: Checkpoint
- **Goal**: Review the recovery batch, capture remaining hotspots, and decide whether unattended continuation still has a good cost/benefit ratio.
- **Constraints**:
  - Do not extend the queue automatically beyond Q3
  - Focus on documentation and metrics instead of new code work
- **Acceptance**:
  - The phase doc clearly records recovered gates, remaining issues, and the stop/continue recommendation

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the overall preset is complete.
