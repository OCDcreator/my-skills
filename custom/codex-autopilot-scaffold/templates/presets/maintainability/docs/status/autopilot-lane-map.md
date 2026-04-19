# Autopilot Lane Map

> **Preset**: `[[PRESET_LABEL]]`
> **Scheduling**: Sequential lane controller
> **Note**: The active lane comes from `automation/autopilot-config.json`; this file is a static index.

## Lane directories

- `m1-hotspot-slice`
  - roadmap: `docs/status/lanes/m1-hotspot-slice/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/m1-hotspot-slice/autopilot-phase-0.md`
- `m2-followup-slice`
  - roadmap: `docs/status/lanes/m2-followup-slice/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/m2-followup-slice/autopilot-phase-0.md`
- `m3-checkpoint`
  - roadmap: `docs/status/lanes/m3-checkpoint/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/m3-checkpoint/autopilot-phase-0.md`

## Suggested entrypoints

[[ENTRYPOINT_BULLETS]]

## Validation baseline

[[VALIDATION_BULLETS]]

## Boundaries

- Do not refactor outside the queued slice
- Do not turn maintainability work into a broad rewrite
- Keep `automation/runtime/` ignored and machine-local state out of committed files
