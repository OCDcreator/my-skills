# Autopilot Lane Map

> **Preset**: `Bugfix / Backlog`
> **Current `[NEXT]`**: `B17 - Persistent vault log ingestion via Logstravaganza`

## Current priority

- B16 is complete; ecosystem detection, docs, and CI surfacing are now covered
- Execute B17 next to turn `Logstravaganza` from a detected optional tool into a real capture/report input
- Keep B18 and B19 queued behind B17 so lint/plugin-entry and repo-owned Obsidian E2E follow in order
- Keep each round bounded to one Obsidian plugin autodebug framework slice
- Validate with script-level smoke tests where available because this repo has no global build/test/lint

## Suggested entrypoints

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
- Preserve plugin-agnostic behavior; project-specific names belong only in examples or validation artifacts
- No queue expansion beyond approved B17-B19 unless a human approves it
- Keep `automation/runtime/` ignored and local-only
