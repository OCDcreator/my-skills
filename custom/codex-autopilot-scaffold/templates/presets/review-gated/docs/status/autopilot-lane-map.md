# Autopilot Lane Map

> **Preset**: `[[PRESET_LABEL]]`
> **Scheduling**: Sequential lane controller
> **Note**: The active lane comes from `automation/autopilot-config.json`; this file is a static index.

## Lane directories

- `rg1-reviewed-slice`
  - roadmap: `docs/status/lanes/rg1-reviewed-slice/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/rg1-reviewed-slice/autopilot-phase-0.md`
- `rg2-reviewed-followup`
  - roadmap: `docs/status/lanes/rg2-reviewed-followup/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/rg2-reviewed-followup/autopilot-phase-0.md`
- `rg3-reviewed-checkpoint`
  - roadmap: `docs/status/lanes/rg3-reviewed-checkpoint/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/rg3-reviewed-checkpoint/autopilot-phase-0.md`

## Suggested entrypoints

[[ENTRYPOINT_BULLETS]]

## Validation baseline

[[VALIDATION_BULLETS]]

## Boundaries

- Keep `.opencode/commands/` committed so repo-local review commands travel with the scaffold
- Keep `automation/runtime/` ignored and machine-local state out of committed files
- Do not bypass review-gated steps unless the queue item explicitly says the review asset is unavailable and the round must stop
