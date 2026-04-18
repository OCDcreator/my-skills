# Autopilot Phase 8: B8 Smoke-Mode Diagnosis Honors Intentional Skips

> **Status**: [DONE]
> **Attempt**: 8
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B8 - Smoke-mode diagnosis honors intentional skips`.
- Kept work inside the generic `custom/obsidian-plugin-autodebug` diagnosis/report/comparison pipeline plus the queued status docs.
- Fixed the root cause instead of masking the symptom: the Windows and Bash cycle wrappers now persist explicit smoke-capture intent in `summary.json`, so downstream analysis can distinguish intentional skip states from truly missing screenshot/DOM/trace artifacts.
- Extended diagnosis/report/comparison handling just enough for this slice: `diagnosis.json` now emits machine-readable `artifactStates`, built-in capture assertions downgrade to `skipped` when the wrapper explicitly marked the capture as intentional, HTML reports show skipped-vs-missing status, and screenshot comparison reasons now call out intentional skips instead of generic missing-artifact wording.
- Preserved blocking behavior for real regressions: when capture was requested but the artifact is still absent, the diagnosis path continues to mark it as a failure.

## Changed Files

- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare_core.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-8.md`

## Smoke Results

- **Windows PowerShell smoke job**: rerunning `obsidian_debug_job.mjs --platform windows --mode run` against the existing synthetic B7 smoke fixture now produces a `pass` diagnosis with four skipped assertions (`trace-captured`, `screenshot-captured`, `dom-root-present`, `deploy-artifacts-match`) instead of blocking failures.
- **Bash smoke wrapper on the Windows host**: rerunning `obsidian_plugin_debug_cycle.sh` with `--watch-seconds 0 --skip-screenshot --skip-dom` now also produces a `pass` diagnosis with the same intentional-skip classification.
- **Synthetic diagnosis/report/comparison harness**: a focused verification script under `.tmp-skills/verify-smoke-skip.mjs` now proves the whole B8 path end-to-end: synthetic smoke metadata yields skipped artifact assertions, baseline save/compare preserve `artifactStates`, screenshot compare reasons report `baseline-and-candidate-screenshots-intentionally-skipped`, and the HTML report surfaces “Intentionally skipped” instead of plain “Missing”.

## Validation Results

- `node .tmp-skills/verify-smoke-skip.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare_core.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs` — passed.
- `powershell -NoProfile -Command "[void][scriptblock]::Create((Get-Content -Raw 'custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1'))"` — passed.
- `C:\Program Files\Git\bin\bash.exe -n custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b7/b7-smoke-job.json --platform windows --mode run --output .tmp-skills/autopilot-b8/job-run-windows.json` — passed; the regenerated Windows smoke diagnosis now reports `status: pass` with intentional skip metadata.
- `C:\Program Files\Git\bin\bash.exe custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh --plugin-id sample-plugin --test-vault-plugin-dir .tmp-skills/autopilot-b7/test-vault/.obsidian/plugins/sample-plugin --obsidian-command node --output-dir .tmp-skills/autopilot-b8/bash-cycle --watch-seconds 0 --poll-interval-ms 50 --console-limit 10 --skip-build --skip-deploy --skip-reload --skip-screenshot --skip-dom` — passed; the Bash smoke diagnosis now reports `status: pass` with intentional skip metadata.

## Remaining Risks

- Native macOS host execution is still unverified; this round only exercised Windows PowerShell plus Bash-on-Windows smoke paths.
- Historical smoke artifacts written before this round do not retroactively gain `capturePlan` / `artifactStates`; rerun those jobs if you need the new skipped-vs-missing distinction on old fixtures.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- Continue with `B9 - Native macOS smoke host validation`.
