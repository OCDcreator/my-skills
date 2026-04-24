# Autopilot Round Roadmap — `rg1-reviewed-slice`

## Queue

### [NEXT] RG1 - First review-gated delivery slice

- **Lane**: Review-gated delivery
- **Goal**: Complete one high-value queued slice with a written plan, a plan review, implementation, a code review, and full validation before commit.
- **Priority entrypoints**:
[[ENTRYPOINT_BULLETS]]
- **Constraints**:
  - Stay inside one bounded slice
  - Record plan/code review verdicts in the phase doc
  - Do not commit until validation and code review both pass
- **Acceptance**:
  - `implementation-plan.md`, `plan-review.txt`, and `code-review.txt` exist in the round directory
  - The phase doc records both review verdicts and validation results
  - Every configured validation command passes

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `rg2-reviewed-followup`.
