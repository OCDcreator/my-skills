# Autopilot Phase 6: B6 Executable Playbooks, Doctor Fixes, And State Matrices

> **Status**: [DONE]
> **Attempt**: 6
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B6 - Executable playbooks, doctor --fix, and state matrices`.
- Kept work inside the generic `custom/obsidian-plugin-autodebug` framework plus the queued status docs.
- Turned issue playbook command suggestions into structured executable templates that resolve runtime context, attach safety labels, and render current-platform commands in `diagnosis.json` and the HTML report.
- Added a shared command-template helper plus a new `obsidian_debug_state_matrix.mjs` runner that previews/reset/restores plugin-local state and runs the same job across clean-state and restored-state cases with separate output directories.
- Extended `obsidian_debug_doctor.mjs` to categorize build/deploy/CLI/CDP prerequisites, emit machine-readable fix commands, and write reviewable `doctor-fixes.ps1` / `doctor-fixes.sh` scripts when `--fix` is requested.
- Added `repoDir` capture to the Windows/macOS cycle summaries so downstream playbooks and reports can render runnable commands without committed absolute paths, and fixed the job runner so missing `state.*` sections stay disabled unless explicitly configured.
- Updated the skill documentation to describe doctor `--fix`, playbook safety labels, and the clean/restored state-matrix workflow.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/rules/issue-playbooks.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_command_templates.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_state_matrix.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-6.md`

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_command_templates.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_state_matrix.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs` — passed.
- `powershell -NoProfile -Command "[void][scriptblock]::Create((Get-Content -Raw 'custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1'))"` — passed.
- `C:\Program Files\Git\bin\bash.exe -n custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh` — passed.
- A targeted `node --input-type=module -` validation harness under `.tmp-skills/autopilot-b6/` — passed; it verified doctor `--fix` report/script generation, rendered playbook safety metadata in diagnosis/report output, state-matrix `run` execution with separate clean/restored outputs, job `--output-dir` overrides, and plugin-state restoration after the clean-state pass.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- Continue with `B7 - Cross-platform validation checkpoint`.
