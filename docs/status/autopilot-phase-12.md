# Autopilot Phase 12: B12 Optional Playwright And UI Trace Adapter

> **Status**: [DONE]
> **Attempt**: 3
> **Preset**: Bugfix / backlog
> **Repository**: `my-skills`
> **Date**: 2026-04-19

## Scope

- Added an optional Playwright-backed scenario adapter to the generic `custom/obsidian-plugin-autodebug` flow without removing the existing CLI/CDP-first scenario path.
- Extended doctor, job-plan generation, and both platform cycle wrappers so a job can opt into Playwright locator steps plus trace/screenshot artifact capture through config.
- Extended diagnosis and HTML report outputs so Playwright traces/screenshots surface as first-class artifacts alongside existing console/CDP/DOM evidence.
- Added a plugin-neutral Playwright scenario template plus skill/eval documentation for the adapter.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/evals/evals.json`
- `custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json`
- `custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json`
- `custom/obsidian-plugin-autodebug/scenarios/playwright-locator-health.template.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare_core.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_playwright_support.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scenario_runner.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh`
- `docs/status/autopilot-lane-map.md`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-12.md`

## Implementation Notes

- `obsidian_debug_playwright_support.mjs` centralizes optional Playwright module detection/loading, adapter normalization, artifact path defaults, and page selection for CDP-attached Obsidian windows.
- `obsidian_debug_scenario_runner.mjs` now accepts `scenario.adapter=playwright`, supports Playwright locator/screenshot steps, and records module/trace/screenshot metadata in `scenario-report.json`.
- `obsidian_debug_doctor.mjs` now reports a `playwright-adapter` check so agents can see whether a repo-local Playwright dependency is ready before opting in.
- `obsidian_debug_job.mjs` and the Bash/PowerShell cycle wrappers now pass Playwright adapter settings through job specs instead of silently dropping them.
- `obsidian_debug_analyze.mjs`, `obsidian_debug_compare_core.mjs`, and `obsidian_debug_report.mjs` now surface Playwright trace/screenshot artifacts in diagnosis JSON and HTML reports.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_playwright_support.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scenario_runner.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare_core.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs` — passed.
- `bash -n custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b12/playwright-fixture-repo --plugin-id playwright-smoke-plugin --platform bash --obsidian-command obsidian --playwright-module playwright --output .tmp-skills/autopilot-b12/doctor.after.json` — passed with a `playwright-adapter` check using a repo-local fake Playwright module.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b12/job-playwright.after.json --platform bash --dry-run --output .tmp-skills/autopilot-b12/job-playwright-plan.after.json` — passed and emitted Playwright adapter flags in the generated Bash plan.
- `(cd .tmp-skills/autopilot-b12/playwright-fixture-repo && node ../../../custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scenario_runner.mjs --scenario-path ../playwright-smoke/scenario.json --scenario-adapter playwright --plugin-id playwright-smoke-plugin --cli-available false --surface-profile ../../../custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json --cdp-host 127.0.0.1 --cdp-port 9222 --cdp-target-title-contains Autopilot --playwright-module playwright --output ../playwright-smoke/scenario-report.json)` — passed and captured synthetic Playwright trace/screenshot artifacts.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs --summary .tmp-skills/autopilot-b12/playwright-smoke/summary.json --output .tmp-skills/autopilot-b12/playwright-smoke/diagnosis.json` — passed and promoted Playwright artifacts into diagnosis JSON.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs --diagnosis .tmp-skills/autopilot-b12/playwright-smoke/diagnosis.json --output .tmp-skills/autopilot-b12/playwright-smoke/report.html` — passed and linked Playwright artifacts in the HTML report.
- `node --input-type=module <<'EOF' ... EOF` — passed while asserting the doctor output, job plan flags, scenario-report Playwright capture, diagnosis artifact states, and report HTML labels.
- `git diff --check` — passed.

## Validation Gaps

- `pwsh` was unavailable on this macOS host, so the updated `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1` could not be parser-checked locally in this round.
- Lint command was blank in the round metadata, so no repo-wide lint step existed to run.
- Typecheck command was blank in the round metadata, so no repo-wide typecheck step existed to run.
- Full test command was blank in the round metadata, so no repo-wide test suite existed to run.
- Build command was blank in the round metadata, so no repo-wide build step existed to run.
- Vulture command was blank in the round metadata, so no dead-code observability run existed to record.

## Next Recommended Slice

- `B13 - Hot Reload coordination doctor`
