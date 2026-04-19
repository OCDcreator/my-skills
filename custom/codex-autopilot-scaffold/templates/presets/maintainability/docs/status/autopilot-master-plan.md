# Autopilot Master Plan

> **Preset**: `[[PRESET_LABEL]]`
> **Repository**: `[[REPO_NAME]]`
> **Controller mode**: Explicit sequential lanes from `automation/autopilot-config.json`
> **Note**: This file is a human-facing cross-lane overview, not the live `[NEXT]` truth source.

## Overall objective

- [[OBJECTIVE]]
- Prefer queue-driven ownership reduction over free-form cleanup
- Keep configured validation commands green after every successful round

## Lane order

- `m1-hotspot-slice` — first high-value maintainability / refactor slice
- `m2-followup-slice` — next bounded follow-up slice after M1
- `m3-checkpoint` — document what moved and whether unattended continuation still makes sense

## Shared entrypoints

[[ENTRYPOINT_BULLETS]]

## Shared validation baseline

[[VALIDATION_BULLETS]]

## Guardrails

- Only one lane is active at a time
- The controller advances to the next lane only after the current lane roadmap has no remaining `[NEXT]` or `[QUEUED]` items
- Do not extend the queue automatically beyond the preset checkpoint
- Do not change product behavior while chasing maintainability wins
