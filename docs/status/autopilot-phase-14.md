# Autopilot Phase 14: B15 Optional Testing-Framework And CI Templates

> **Status**: [DONE]
> **Attempt**: 8
> **Preset**: Bugfix / backlog
> **Repository**: `my-skills`
> **Date**: 2026-04-19

## Scope

- Added optional `obsidian-testing-framework` detection so the generic doctor can distinguish “installed”, “declared but not installed”, and “not configured yet” states without turning that adapter into a hard dependency.
- Added a headless quality-gate template emitter plus scaffold integration so the framework can generate Bash, PowerShell, GitHub Actions, and README templates that reuse repo-owned build/test commands and optional testing-framework scripts.
- Kept the local-versus-CI split explicit by documenting that bootstrap, desktop reload, CDP/CLI capture, screenshots, DOM snapshots, and Playwright traces remain local-only after the headless gate passes.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/evals/evals.json`
- `custom/obsidian-plugin-autodebug/fixtures/testing-framework-smoke-plugin/dist/main.js`
- `custom/obsidian-plugin-autodebug/fixtures/testing-framework-smoke-plugin/dist/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/testing-framework-smoke-plugin/dist/styles.css`
- `custom/obsidian-plugin-autodebug/fixtures/testing-framework-smoke-plugin/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/testing-framework-smoke-plugin/package.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ci_templates.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scaffold_plugin.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_testing_framework_support.mjs`
- `docs/status/autopilot-lane-map.md`
- `docs/status/autopilot-phase-14.md`
- `docs/status/autopilot-round-roadmap.md`

## Implementation Notes

- `obsidian_debug_testing_framework_support.mjs` inspects `package.json` dependency fields plus matching repo-owned scripts and attempts module resolution from the repo root so optional adapter status can be reported without forcing installation.
- `obsidian_debug_doctor.mjs` now emits `testing-framework-module`, `testing-framework-scripts`, and `ci-quality-gate-templates` checks, and records which phases are CI-suitable versus still local-only.
- `obsidian_debug_ci_templates.mjs` generates `README.md`, `quality-gate.sh`, `quality-gate.ps1`, and `github-actions-quality-gate.yml` templates that stay free of machine-local absolute paths and default to repo-owned build/test plus optional testing-framework scripts.
- `obsidian_debug_scaffold_plugin.mjs` now emits `autodebug/ci/` for scaffolded sample plugins so fresh workspaces immediately get a headless quality gate alongside the existing desktop bootstrap/debug job.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_testing_framework_support.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ci_templates.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scaffold_plugin.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs` — passed.
- `set -euo pipefail ... node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ci_templates.mjs --repo-dir custom/obsidian-plugin-autodebug/fixtures/testing-framework-smoke-plugin --job ../../job-specs/generic-debug-job.template.json --output-dir "$PWD/.tmp-skills/autopilot-b15/generated-ci" --output .tmp-skills/autopilot-b15/ci-templates-report.json ... git diff --check` — passed while:
  - generating CI templates from the new testing-framework fixture,
  - proving doctor reports `warn` for declared-but-not-installed support and `pass` for a fake installed module,
  - scaffolding a fresh sample plugin with `autodebug/ci/`,
  - running the generated `autodebug/ci/quality-gate.sh` headless gate against the scaffolded sample,
  - asserting the workflow stays free of machine-local absolute paths,
  - and confirming `git diff --check`.

## Validation Gaps

- Lint command was blank in the round metadata, so no repo-wide lint step existed to run.
- Typecheck command was blank in the round metadata, so no repo-wide typecheck step existed to run.
- Full test command was blank in the round metadata, so no repo-wide full test step existed to run.
- Build command was blank in the round metadata, so no separate repo-wide build step existed beyond the targeted script and scaffold smoke checks above.
- Vulture command was blank in the round metadata, so no dead-code observability run existed to record.
- The generated PowerShell and GitHub Actions templates were validated structurally on macOS, but not executed on a native Windows or CI runner in this round.

## Next Recommended Slice

- None. The approved B11-B15 backlog queue is exhausted; wait for a human-approved next slice before starting another round.
