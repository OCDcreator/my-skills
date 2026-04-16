# Autopilot Lane Map

> **Preset**: `[[PRESET_LABEL]]`
> **Current `[NEXT]`**: `Q1 - Recover the first configured gate`

## Current priority

- Recover the highest-impact configured validation issue first
- Keep changes tightly bounded to the queued hotspot
- Record missing validation commands instead of guessing them

## Suggested entrypoints

[[ENTRYPOINT_BULLETS]]

## Validation baseline

[[VALIDATION_BULLETS]]

## Boundaries

- No free-form refactor batches while gates are unstable
- No blanket silencing of warnings
- Keep `automation/runtime/` untracked and machine-local
