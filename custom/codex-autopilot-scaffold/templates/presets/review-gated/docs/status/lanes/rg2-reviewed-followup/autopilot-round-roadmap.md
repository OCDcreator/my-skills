# Autopilot Round Roadmap — `rg2-reviewed-followup`

## Queue

### [NEXT] RG2 - Next review-gated delivery slice

- **Lane**: Review-gated delivery follow-up
- **Goal**: Execute the next queued slice using the same plan-review -> implement -> code-review -> validate contract.
- **Constraints**:
  - Keep scope bounded to one slice
  - Reuse the repo-local review assets instead of ad-hoc prompts
  - Preserve behavior outside the queued slice
- **Acceptance**:
  - Review verdicts are captured in the phase doc
  - The queued slice is marked `[DONE]`
  - Validation remains green

## Lane state

- This roadmap is lane-local.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `rg3-reviewed-checkpoint`.
