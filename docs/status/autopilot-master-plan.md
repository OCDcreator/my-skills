# Autopilot Master Plan

> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Controller mode**: Explicit sequential lanes from `automation/autopilot-config.json`
> **Note**: This file is a human-facing cross-lane overview, not the live `[NEXT]` truth source.

## Overall objective

- Continue the approved generic `custom/obsidian-plugin-autodebug` ecosystem backlog from completed B17 into the remaining B18 preflight validation slice, B19 repo-owned Obsidian E2E adapter slice, and a final checkpoint without hard-coding one plugin or machine-local path.
- Keep each queued slice small, reproducible, and easy to validate
- Prefer the highest-confidence bugfix or backlog item first

## Lane order

- `b1-backlog-slice` — B18 preflight lint and plugin-entry validation gates
- `b2-backlog-slice` — B19 repo-owned Obsidian E2E adapter fixtures and CI wiring
- `b3-checkpoint` — summarize the B18/B19 batch and decide whether more backlog work should be human-scheduled

## Shared entrypoints

- `AGENTS.md`
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/`
- `custom/obsidian-plugin-autodebug/assertions/`
- `custom/obsidian-plugin-autodebug/rules/`
- `custom/obsidian-plugin-autodebug/state-plans/`
- `custom/obsidian-plugin-autodebug/job-specs/`
- `custom/obsidian-plugin-autodebug/fixtures/`

## Shared validation baseline

- Lint: not inferred
- Typecheck: not inferred
- Full test: not inferred
- Build: not inferred
- Vulture: not inferred

## Guardrails

- Only one lane is active at a time
- The controller advances to the next lane only after the current lane roadmap has no remaining `[NEXT]` or `[QUEUED]` items
- Root-level legacy phase docs (`docs/status/autopilot-phase-*.md`) remain as archive for B1-B17 and are not the live lane queue source
- Do not extend the queue automatically beyond B19 without another human approval
