# Autopilot Lane Map

> **Preset**: `[[PRESET_LABEL]]`
> **Scheduling**: Sequential lane controller
> **Note**: The active lane comes from `automation/autopilot-config.json`; this file is a static index.

## Lane directories

- `b1-backlog-slice`
  - roadmap: `docs/status/lanes/b1-backlog-slice/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/b1-backlog-slice/autopilot-phase-0.md`
- `b2-backlog-slice`
  - roadmap: `docs/status/lanes/b2-backlog-slice/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/b2-backlog-slice/autopilot-phase-0.md`
- `b3-checkpoint`
  - roadmap: `docs/status/lanes/b3-checkpoint/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/b3-checkpoint/autopilot-phase-0.md`

## Suggested entrypoints

[[ENTRYPOINT_BULLETS]]

## Validation baseline

[[VALIDATION_BULLETS]]

## Boundaries

- No broad polish or unrelated cleanup
- No queue expansion beyond the preset checkpoint unless a human edits the lane roadmap
- Keep `automation/runtime/` ignored and local-only
