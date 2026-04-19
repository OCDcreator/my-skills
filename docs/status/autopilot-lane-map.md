# Autopilot Lane Map

> **Preset**: `Bugfix / Backlog`
> **Scheduling**: Sequential lane controller
> **Note**: The active lane comes from `automation/autopilot-config.json`; this file is a static index.

## Lane directories

- `b1-backlog-slice`
  - roadmap: `docs/status/lanes/b1-backlog-slice/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/b1-backlog-slice/autopilot-phase-0.md`
  - live slice: `B18 - Preflight lint and plugin-entry validation gates`
- `b2-backlog-slice`
  - roadmap: `docs/status/lanes/b2-backlog-slice/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/b2-backlog-slice/autopilot-phase-0.md`
  - live slice: `B19 - Repo-owned Obsidian E2E adapter fixtures and CI wiring`
- `b3-checkpoint`
  - roadmap: `docs/status/lanes/b3-checkpoint/autopilot-round-roadmap.md`
  - baseline: `docs/status/lanes/b3-checkpoint/autopilot-phase-0.md`
  - live slice: `Checkpoint - Review B18 and B19 outcome`

## Suggested entrypoints

- `AGENTS.md`
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/`
- `custom/obsidian-plugin-autodebug/assertions/`
- `custom/obsidian-plugin-autodebug/rules/`
- `custom/obsidian-plugin-autodebug/state-plans/`
- `custom/obsidian-plugin-autodebug/job-specs/`
- `custom/obsidian-plugin-autodebug/fixtures/`

## Validation baseline

- Lint: not inferred
- Typecheck: not inferred
- Full test: not inferred
- Build: not inferred
- Vulture: not inferred

## Boundaries

- No broad polish or unrelated cleanup
- Legacy root `docs/status/autopilot-round-roadmap.md` and `docs/status/autopilot-phase-*.md` are archived carry-over from B1-B17; live queue truth now lives in `docs/status/lanes/*`
- No queue expansion beyond B19 unless a human edits the lane roadmap
- Keep `automation/runtime/` ignored and local-only
