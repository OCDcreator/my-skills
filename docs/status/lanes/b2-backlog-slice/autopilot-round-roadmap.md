# Autopilot Round Roadmap — `b2-backlog-slice`

## Queue

### [DONE] B19 - Repo-owned Obsidian E2E adapter fixtures and CI wiring

- **Lane**: Bugfix / backlog
- **Goal**: Make optional `obsidian-e2e`, `obsidian-testing-framework`, and `wdio-obsidian-service` support actionable by shipping detector-backed fixture/script patterns and CI wiring instead of documentation-only references.
- **Priority entrypoints**:
  - `custom/obsidian-plugin-autodebug/SKILL.md`
  - `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ecosystem_support.mjs`
  - `custom/obsidian-plugin-autodebug/fixtures/`
  - `docs/status/lanes/b1-backlog-slice/autopilot-round-roadmap.md`
- **Constraints**:
  - Keep every adapter optional and repo-owned; do not bundle Obsidian binaries or machine-local paths
  - Prefer existing repository scripts when present and only infer commands when the repo leaves them implicit
  - Preserve compatibility with the existing CLI/CDP-first path when no E2E adapter is installed
- **Acceptance**:
  - Doctor can distinguish declared dependencies from runnable adapter scripts and explain gaps clearly
  - Generated templates or fixtures demonstrate both Vitest-style and WebdriverIO-style Obsidian E2E lanes
  - CI wiring can target the chosen adapter without forcing one framework across all plugin repos

## Lane state

- This roadmap is lane-local.
- Lane `b2-backlog-slice` has no remaining `[NEXT]` or `[QUEUED]` items; the controller can advance to `b3-checkpoint`.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `b3-checkpoint`.
