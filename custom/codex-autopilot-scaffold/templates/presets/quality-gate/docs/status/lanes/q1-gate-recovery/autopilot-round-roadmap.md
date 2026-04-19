# Autopilot Round Roadmap — `q1-gate-recovery`

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

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `q2-gate-cleanup`.
