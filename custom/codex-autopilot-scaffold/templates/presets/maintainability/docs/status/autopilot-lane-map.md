# Autopilot Lane Map

> **Preset**: `[[PRESET_LABEL]]`
> **Current `[NEXT]`**: `R1 - First maintainability / refactor slice`

## Current priority

- Keep the queue bounded and repo-specific
- Reduce one maintainability hotspot at a time
- Keep configured validation commands green

## Suggested entrypoints

[[ENTRYPOINT_BULLETS]]

## Validation baseline

[[VALIDATION_BULLETS]]

## Boundaries

- Do not refactor outside the queued slice
- Do not turn maintainability work into a broad rewrite
- Keep `automation/runtime/` ignored and machine-local state out of committed files
