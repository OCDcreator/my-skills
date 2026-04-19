# Autopilot Round Roadmap — `b1-backlog-slice`

## Queue

### [DONE] B18 - Preflight lint and plugin-entry validation gates

- **Lane**: Bugfix / backlog
- **Goal**: Turn optional `eslint-plugin-obsidianmd` and ReviewBot-style plugin-entry validation into reusable preflight checks that run before build/deploy flows and can be emitted into generated CI templates.
- **Priority entrypoints**:
- `AGENTS.md`
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ecosystem_support.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_preflight_support.mjs`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/`
- `docs/status/autopilot-phase-17.md`
- **Constraints**:
  - Keep repository-owned lint scripts authoritative instead of inventing mandatory replacement commands
  - Treat plugin-entry validation as optional and avoid network, secret, or machine-local path requirements
  - Surface manifest/template residue issues early without widening scope into unrelated release automation
- **Acceptance**:
  - Doctor/runtime detection can identify runnable lint and plugin-entry preflight commands with remediation hints
  - Generated CI templates can emit optional lint and plugin-entry validation steps before build/deploy
  - Fixtures, templates, or docs demonstrate that manifest and template-residue failures can be caught pre-build

## Lane state

- This roadmap is lane-local.
- Lane `b1-backlog-slice` has no remaining `[NEXT]` or `[QUEUED]` items; the controller can advance to `b2-backlog-slice`.
- When it has no remaining `[NEXT]` or `[QUEUED]` items, the controller switches to `b2-backlog-slice`.
