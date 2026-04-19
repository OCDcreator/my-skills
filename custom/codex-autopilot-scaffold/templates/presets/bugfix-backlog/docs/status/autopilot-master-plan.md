# Autopilot Master Plan

> **Preset**: `[[PRESET_LABEL]]`
> **Repository**: `[[REPO_NAME]]`
> **Controller mode**: Explicit sequential lanes from `automation/autopilot-config.json`
> **Note**: This file is a human-facing cross-lane overview, not the live `[NEXT]` truth source.

## Overall objective

- [[OBJECTIVE]]
- Keep each queued slice small, reproducible, and easy to validate
- Prefer the highest-confidence bugfix or backlog item first

## Lane order

- `b1-backlog-slice` — highest-priority reproducible bug or backlog slice
- `b2-backlog-slice` — the next queued slice after B1 lands
- `b3-checkpoint` — document what shipped and whether unattended continuation still makes sense

## Shared entrypoints

[[ENTRYPOINT_BULLETS]]

## Shared validation baseline

[[VALIDATION_BULLETS]]

## Guardrails

- Only one lane is active at a time
- The controller advances to the next lane only after the current lane roadmap has no remaining `[NEXT]` or `[QUEUED]` items
- Do not extend the queue automatically beyond the preset checkpoint
