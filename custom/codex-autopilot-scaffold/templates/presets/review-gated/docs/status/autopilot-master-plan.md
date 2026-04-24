# Autopilot Master Plan

> **Preset**: `[[PRESET_LABEL]]`
> **Repository**: `[[REPO_NAME]]`
> **Controller mode**: Explicit sequential lanes from `automation/autopilot-config.json`
> **Note**: This file is a human-facing overview. The live `[NEXT]` source stays in the lane roadmap.

## Overall objective

- [[OBJECTIVE]]
- Each round must pass an implementation-plan review before coding
- Each round must pass a code review before final validation and commit
- Prefer `bootstrap-and-daemonize` over ad-hoc first-round shell gymnastics when the operator wants “首轮成功后继续后台跑”

## Lane order

- `rg1-reviewed-slice` — first review-gated delivery slice
- `rg2-reviewed-followup` — next review-gated delivery slice
- `rg3-reviewed-checkpoint` — checkpoint after the first review-gated batch

## Shared entrypoints

[[ENTRYPOINT_BULLETS]]

## Shared validation baseline

[[VALIDATION_BULLETS]]

## Review-gated assets

- `.opencode/commands/review-plan.md`
- `.opencode/commands/review-code.md`
- `automation/opencode-review.sh`
- `automation/Invoke-OpencodeReview.ps1`

## Guardrails

- Only one lane is active at a time
- The controller advances only after the current lane roadmap has no remaining `[NEXT]` or `[QUEUED]` items
- Review wrappers are allowed to take minutes; quiet polling is not a stuck signal by itself
- `status=active` is not enough to prove liveness; use `python automation/autopilot.py health` or the watch header
