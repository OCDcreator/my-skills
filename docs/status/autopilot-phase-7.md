# Autopilot Phase 7: B7 Cross-Platform Validation Checkpoint

> **Status**: [DONE]
> **Attempt**: 7
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B7 - Cross-platform validation checkpoint`.
- Kept work inside the generic `custom/obsidian-plugin-autodebug` framework plus the queued status docs.
- Validated the shipped B1-B6 automation slices against a plugin-neutral synthetic fixture under `.tmp-skills/autopilot-b7/`, covering command planning, direct wrappers, doctor/fix generation, surface discovery, scenario dry runs, state-matrix planning, baseline save/list/compare, and HTML report generation.
- Fixed one checkpoint-blocking Windows issue in `scripts/obsidian_plugin_debug_cycle.ps1`: `Invoke-ObsidianCli -AllowFailure` now temporarily relaxes `$ErrorActionPreference` while capturing native-command stderr, so smoke runs no longer abort when a probe command intentionally fails.
- Recorded the remaining checkpoint risks instead of widening scope: smoke runs that intentionally skip screenshot/DOM capture still produce blocking diagnosis failures, and native macOS execution remains unverified on this Windows host.

## Shipped Slice Checkpoint

- **B1 orchestration**: Windows and Bash job plans render successfully from the generic job spec.
- **B2 discovery**: synthetic surface discovery and the generic `open-plugin-view` scenario dry run both succeed with plugin-neutral fixtures.
- **B3 assertions/reporting**: Windows smoke runs still emit diagnosis/report artifacts, but intentionally skipped capture is currently treated as a blocking failure.
- **B4/B5 baselines/comparison**: baseline save/list/compare still work from current diagnosis/report artifacts; screenshot diff degrades to `skipped` when no screenshots are present.
- **B6 automation helpers**: doctor `--fix`, state-matrix planning, and reset preview all execute on the current codebase for both command platforms.

## Changed Files

- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-7.md`

## Smoke Results

- **Windows PowerShell**: `obsidian_debug_job.mjs --platform windows --mode run` now completes end-to-end against the synthetic fixture, writes `diagnosis.json`, and generates `report.html`.
- **Bash on Windows host**: `obsidian_plugin_debug_cycle.sh` runs successfully through Git Bash and writes diagnosis artifacts, which verifies the shipped Bash wrapper path on this machine.
- **macOS native host**: not runnable in this Windows/PowerShell environment; the checkpoint documents this as a follow-up queue item instead of claiming host parity.
- **Doctor/fix**: Windows and Bash doctor reports both execute and generate fix scripts, with expected warnings for the synthetic `node` CLI stub and absent CDP target.
- **State matrix/reset**: Windows and Bash dry-run state matrices plus reset preview execute successfully against plugin-local sample state.
- **Baseline/report flows**: baseline save/list/compare succeed from the synthetic Windows smoke artifacts; screenshot diff is intentionally `skipped` because the smoke job disabled screenshot capture.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/*.mjs` via a PowerShell loop — passed for every `.mjs` script in `custom/obsidian-plugin-autodebug/scripts/`.
- `powershell -NoProfile -Command "[void][scriptblock]::Create((Get-Content -Raw 'custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1'))"` — passed.
- `C:\Program Files\Git\bin\bash.exe -n custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh` — passed.
- `C:\Program Files\Git\bin\bash.exe -n custom/obsidian-plugin-autodebug/scripts/obsidian_mac_restart_cdp.sh` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b7/b7-smoke-job.json --platform windows --mode dry-run --output .tmp-skills/autopilot-b7/output/job-plan-windows.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b7/b7-smoke-job.json --platform bash --mode dry-run --output .tmp-skills/autopilot-b7/output/job-plan-bash.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b7/b7-smoke-job.json --platform windows --mode run --output .tmp-skills/autopilot-b7/output/job-run-windows.json` — initially failed before the PowerShell wrapper fix because `Invoke-ObsidianCli -AllowFailure` still stopped on native-command stderr; reran after the focused fix and it passed.
- `C:\Program Files\Git\bin\bash.exe custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh --plugin-id sample-plugin --test-vault-plugin-dir .tmp-skills/autopilot-b7/test-vault/.obsidian/plugins/sample-plugin --obsidian-command node --output-dir .tmp-skills/autopilot-b7/bash-cycle --watch-seconds 0 --poll-interval-ms 50 --console-limit 10 --skip-build --skip-deploy --skip-reload --skip-screenshot --skip-dom` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b7/plugin-repo --test-vault-plugin-dir .tmp-skills/autopilot-b7/test-vault/.obsidian/plugins/sample-plugin --plugin-id sample-plugin --obsidian-command node --platform windows --fix --output .tmp-skills/autopilot-b7/output/doctor-windows.json` — passed with expected synthetic CLI/CDP warnings; generated `doctor-fixes.ps1`.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b7/plugin-repo --test-vault-plugin-dir .tmp-skills/autopilot-b7/test-vault/.obsidian/plugins/sample-plugin --plugin-id sample-plugin --obsidian-command node --platform bash --fix --output .tmp-skills/autopilot-b7/output/doctor-bash.json` — passed with expected synthetic CLI/CDP warnings; generated `doctor-fixes.sh`.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_state_matrix.mjs --job .tmp-skills/autopilot-b7/b7-smoke-job.json --state-plan .tmp-skills/autopilot-b7/b7-state-plan.json --vault-root .tmp-skills/autopilot-b7/test-vault --plugin-id sample-plugin --platform windows --mode dry-run --output-root .tmp-skills/autopilot-b7/output/state-matrix-windows --output .tmp-skills/autopilot-b7/output/state-matrix-windows.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_state_matrix.mjs --job .tmp-skills/autopilot-b7/b7-smoke-job.json --state-plan .tmp-skills/autopilot-b7/b7-state-plan.json --vault-root .tmp-skills/autopilot-b7/test-vault --plugin-id sample-plugin --platform bash --mode dry-run --output-root .tmp-skills/autopilot-b7/output/state-matrix-bash --output .tmp-skills/autopilot-b7/output/state-matrix-bash.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_reset_state.mjs --mode preview --state-plan .tmp-skills/autopilot-b7/b7-state-plan.json --vault-root .tmp-skills/autopilot-b7/test-vault --plugin-id sample-plugin --snapshot-dir .tmp-skills/autopilot-b7/output/reset-preview` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_surface_discovery.mjs --surface-profile custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json --plugin-id sample-plugin --dry-run --output .tmp-skills/autopilot-b7/output/surface-discovery.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scenario_runner.mjs --scenario-name open-plugin-view --plugin-id sample-plugin --scenario-command-id sample-plugin:open-view --surface-profile custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json --dry-run --output .tmp-skills/autopilot-b7/output/scenario-dry-run.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode save --baseline-root .tmp-skills/autopilot-b7/output/baselines --name b7-smoke --diagnosis .tmp-skills/autopilot-b7/plugin-repo/.obsidian-debug/b7-smoke-windows/diagnosis.json --report .tmp-skills/autopilot-b7/plugin-repo/.obsidian-debug/b7-smoke-report.html` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode list --baseline-root .tmp-skills/autopilot-b7/output/baselines --tags "pluginId=sample-plugin|platform=windows"` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode compare --baseline-root .tmp-skills/autopilot-b7/output/baselines --name b7-smoke --candidate-diagnosis .tmp-skills/autopilot-b7/plugin-repo/.obsidian-debug/b7-smoke-windows/diagnosis.json --output .tmp-skills/autopilot-b7/output/baseline-compare.json` — passed.

## Remaining Risks

- Smoke-mode runs that intentionally disable screenshot/DOM capture still surface blocking diagnosis failures, which makes lightweight validation look broken even when wrapper execution succeeds.
- The Bash wrapper was exercised through Git Bash on Windows, not on a native macOS host; CLI/CDP quirks unique to macOS remain unverified.
- Screenshot diff stayed in `skipped` mode during this checkpoint because the synthetic smoke run deliberately disabled screenshot capture.

## Stop / Continue Recommendation

- **Recommendation**: continue the backlog lane.
- **Why**: the shipped framework is stable enough for queue continuation after the focused Windows wrapper fix, but the checkpoint uncovered a clear smoke-mode diagnosis gap and still lacks native macOS host evidence.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- Continue with `B8 - Smoke-mode diagnosis honors intentional skips`.
