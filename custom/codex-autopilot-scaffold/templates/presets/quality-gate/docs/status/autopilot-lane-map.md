# Autopilot Lane Map

> **Preset**: `[[PRESET_LABEL]]`
> **Scheduling**: Sequential lane controller
> **Note**: The active lane comes from `automation/autopilot-config.json`; this file is a static index.

## Lane directories

- `q1-gate-recovery`
  - roadmap: `docs/status/lanes/q1-gate-recovery/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/q1-gate-recovery/autopilot-phase-0.md`
- `q2-gate-cleanup`
  - roadmap: `docs/status/lanes/q2-gate-cleanup/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/q2-gate-cleanup/autopilot-phase-0.md`
- `q3-checkpoint`
  - roadmap: `docs/status/lanes/q3-checkpoint/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/q3-checkpoint/autopilot-phase-0.md`

## Suggested entrypoints

[[ENTRYPOINT_BULLETS]]

## Validation baseline

[[VALIDATION_BULLETS]]

## Boundaries

- No free-form refactor batches while gates are unstable
- No blanket silencing of warnings
- Keep `automation/runtime/` untracked and machine-local
