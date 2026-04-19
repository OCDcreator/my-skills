# Autopilot Baseline: Phase 0

> **Status**: [BASELINE]
> **Preset**: `Bugfix / Backlog`
> **Lane**: `b1-backlog-slice`
> **Repository**: `my-skills`

## Objective

- Continue the approved generic `custom/obsidian-plugin-autodebug` ecosystem backlog from completed B17 into the remaining B18 preflight validation slice, B19 repo-owned Obsidian E2E adapter slice, and a final checkpoint without hard-coding one plugin or machine-local path.

## Lane scope

- Execute B18 by turning lint and plugin-entry detection into reusable preflight gates and CI-ready guidance.

## Seeded entrypoints

- `AGENTS.md`
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ecosystem_support.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_preflight_support.mjs`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/`
- `docs/status/autopilot-phase-17.md`

## Inferred validation commands

- Lint: not inferred
- Typecheck: not inferred
- Full test: not inferred
- Build: not inferred
- Vulture: not inferred

## Notes

- This document captures the baseline for lane `b1-backlog-slice`.
- Legacy root `docs/status/autopilot-phase-*.md` files record the shipped B1-B17 history; lane-local phase docs take over from here.
- The first unattended round in this lane should write `docs/status/lanes/b1-backlog-slice/autopilot-phase-1.md`.
