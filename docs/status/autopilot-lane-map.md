# Autopilot Lane Map

> **Preset**: `Bugfix / Backlog`
> **Current `[NEXT]`**: `B1 - Config-driven debug job spec and platform-neutral command adapters`

## Current priority

- Start with the generic job spec and Windows/macOS command-adapter foundation
- Keep each round bounded to one Obsidian plugin autodebug framework slice
- Validate with script-level smoke tests where available because this repo has no global build/test/lint

## Suggested entrypoints

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/`
- `custom/obsidian-plugin-autodebug/assertions/`
- `custom/obsidian-plugin-autodebug/rules/`
- `custom/obsidian-plugin-autodebug/state-plans/`

## Validation baseline

- Lint: not inferred
- Typecheck: not inferred
- Full test: not inferred
- Build: not inferred
- Vulture: not inferred

## Boundaries

- No broad polish or unrelated cleanup
- Preserve plugin-agnostic behavior; project-specific names belong only in examples or validation artifacts
- No queue expansion beyond the cross-platform validation checkpoint unless a human approves it
- Keep `automation/runtime/` ignored and local-only
