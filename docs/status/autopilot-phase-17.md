# Autopilot Phase 17: B17 Persistent Vault Log Ingestion via Logstravaganza

> **Status**: [DONE]
> **Attempt**: 1
> **Preset**: Bugfix / backlog
> **Repository**: `my-skills`
> **Date**: 2026-04-19

## Scope

- Executed the queued B17 slice only: turned optional `Logstravaganza` detection into a real vault-log capture path for the generic `custom/obsidian-plugin-autodebug` doctor, cycle capture, diagnosis, and report flows.
- Added a repo-owned `Logstravaganza` discovery/ingestion helper plus a capture script so Windows/macOS cycle wrappers can emit `vault-log-capture.json` without hard-coding one machine-local path.
- Taught diagnosis/reporting to merge optional NDJSON vault logs with existing console/CDP evidence while keeping source-path and line-number provenance explicit, and added portable fixtures that validate both logger-present and no-logger behavior.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/dist/main.js`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/dist/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/dist/styles.css`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/no-vault-log/console-watch.log`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/no-vault-log/errors.log`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/no-vault-log/summary.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/with-vault-log/console-watch.log`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/with-vault-log/errors.log`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/with-vault-log/summary.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/package.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/test-vault/.obsidian/plugins/logstravaganza/data.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/test-vault/.obsidian/plugins/logstravaganza/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/test-vault/.obsidian/plugins/sample-log-plugin/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/test-vault/logs/logstravaganza/session-a.ndjson`
- `custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/test-vault-no-logger/.obsidian/plugins/sample-log-plugin/manifest.json`
- `custom/obsidian-plugin-autodebug/references/command-reference.md`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare_core.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_logstravaganza.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_logstravaganza_capture.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh`
- `docs/status/autopilot-lane-map.md`
- `docs/status/autopilot-phase-17.md`
- `docs/status/autopilot-round-roadmap.md`

## Implementation Notes

- Added `obsidian_debug_logstravaganza.mjs` as the shared vault-root discovery and NDJSON ingestion helper so doctor, cycle capture, and diagnosis stay aligned instead of growing separate path heuristics.
- Added `obsidian_debug_logstravaganza_capture.mjs` and wired both cycle wrappers to emit `vault-log-capture.json` as an optional additive artifact; capture failures degrade to CLI/CDP-only behavior instead of breaking the primary loop.
- Normalized summary-path handling inside `obsidian_debug_analyze.mjs` so portable fixture summaries can resolve repo/output/test-vault/log artifacts relative to the summary document instead of requiring committed absolute paths.
- Extended diagnosis/report structures with `vaultLogs` metadata, explicit `vault-log-captured` assertions, merged timing/signature input, and report-side provenance tables/previews so secondary file logs remain attributable.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_logstravaganza.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_logstravaganza_capture.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare_core.mjs`
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_logstravaganza_capture.mjs --test-vault-plugin-dir custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/test-vault/.obsidian/plugins/sample-log-plugin --output .tmp-skills/autopilot-b17/vault-log-capture.json` — passed; capture artifact recorded one NDJSON source with two parsed lines.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin --plugin-id sample-log-plugin --test-vault-plugin-dir custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/test-vault/.obsidian/plugins/sample-log-plugin --obsidian-command missing-obsidian --output .tmp-skills/autopilot-b17/doctor.json` — passed; doctor now surfaces usable `Logstravaganza` filesystem context even without a live Obsidian CLI.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs --summary custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/with-vault-log/summary.json --output .tmp-skills/autopilot-b17/with-logger-diagnosis.json` — passed; diagnosis imported NDJSON vault logs, preserved provenance, and derived startup timing from merged evidence.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs --summary custom/obsidian-plugin-autodebug/fixtures/logstravaganza-smoke-plugin/outputs/no-vault-log/summary.json --output .tmp-skills/autopilot-b17/no-logger-diagnosis.json` — passed; fallback behavior stays healthy when no vault logger is present.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs --diagnosis .tmp-skills/autopilot-b17/with-logger-diagnosis.json --output .tmp-skills/autopilot-b17/with-logger-report.html` — passed; report now renders the vault-log provenance section and merged preview.
- `powershell -NoProfile -Command "$errors = $null; [System.Management.Automation.Language.Parser]::ParseFile('C:\\Users\\lt\\Desktop\\Write\\custom-project\\my-skills\\custom\\obsidian-plugin-autodebug\\scripts\\obsidian_plugin_debug_cycle.ps1', [ref]$null, [ref]$errors) | Out-Null; if ($errors.Count -gt 0) { $errors | ForEach-Object { $_.ToString() }; exit 1 }"` — passed; PowerShell wrapper syntax is clean after the new capture hook.
- `node --input-type=module -` inline assertions against `.tmp-skills/autopilot-b17/doctor.json`, `.tmp-skills/autopilot-b17/vault-log-capture.json`, `.tmp-skills/autopilot-b17/with-logger-diagnosis.json`, `.tmp-skills/autopilot-b17/no-logger-diagnosis.json`, and `.tmp-skills/autopilot-b17/with-logger-report.html` — passed; validated doctor usability, NDJSON parsing, source attribution, merged timing, report rendering, and no-logger fallback.

## Validation Gaps

- Lint command was blank in the backlog metadata, so no repo-wide lint command existed beyond the targeted script syntax checks above.
- Typecheck command was blank in the backlog metadata, so no repo-wide typecheck command existed to run.
- Full test command was blank in the backlog metadata, so no repo-wide full test suite existed to run.
- Build command was blank in the backlog metadata, so no repo-wide build command existed beyond the targeted helper/report generation checks above.
- Vulture command was blank in the backlog metadata, so no dead-code observability run existed to record.
- `bash -n custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh` could not run on this Windows host because `/bin/bash` is unavailable, so the Bash wrapper change only received structural review plus parity checks against the validated PowerShell path in this round.

## Next Recommended Slice

- `B18 - Preflight lint and plugin-entry validation gates`
