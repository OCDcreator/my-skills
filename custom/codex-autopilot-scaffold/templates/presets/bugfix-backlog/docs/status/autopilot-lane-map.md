# Autopilot Lane Map

> **Preset**: `[[PRESET_LABEL]]`
> **Current `[NEXT]`**: `B1 - Highest-priority queued bug or backlog slice`

## Current priority

- Start with the most reproducible queued issue
- Keep the round bounded to one bugfix or backlog slice
- Validate with every configured command that exists

## Suggested entrypoints

[[ENTRYPOINT_BULLETS]]

## Validation baseline

[[VALIDATION_BULLETS]]

## Boundaries

- No broad polish or unrelated cleanup
- No queue expansion beyond the preset checkpoint
- Keep `automation/runtime/` ignored and local-only
