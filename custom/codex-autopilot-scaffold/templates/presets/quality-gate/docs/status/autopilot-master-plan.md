# Autopilot Master Plan

> **Preset**: `[[PRESET_LABEL]]`
> **Repository**: `[[REPO_NAME]]`
> **Controller mode**: Explicit sequential lanes from `automation/autopilot-config.json`
> **Note**: This file is a human-facing cross-lane overview, not the live `[NEXT]` truth source.

## Overall objective

- [[OBJECTIVE]]
- Recover configured gates before expanding into broader refactors
- Keep queue items small and validation-focused

## Lane order

- `q1-gate-recovery` — recover the first configured gate
- `q2-gate-cleanup` — finish the next bounded validation cleanup slice
- `q3-checkpoint` — record recovered gates and whether unattended continuation still makes sense

## Shared entrypoints

[[ENTRYPOINT_BULLETS]]

## Shared validation baseline

[[VALIDATION_BULLETS]]

## Guardrails

- Only one lane is active at a time
- The controller advances to the next lane only after the current lane roadmap has no remaining `[NEXT]` or `[QUEUED]` items
- Do not extend the queue automatically beyond the preset checkpoint
