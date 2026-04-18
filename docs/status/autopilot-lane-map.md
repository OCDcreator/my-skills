# Autopilot Lane Map

> **Preset**: `Bugfix / Backlog`
> **Current `[NEXT]`**: `B14 - Sample-plugin scaffold and bootstrap mode`

## Current priority

- Start with sample-plugin scaffold/bootstrap work so the framework can generate a minimal debug-ready plugin workspace after the runtime, Playwright, and Hot Reload coordination slices
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
- No queue expansion beyond approved B14-B15 unless a human approves it
- Keep `automation/runtime/` ignored and local-only
