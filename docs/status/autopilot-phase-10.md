# Autopilot Phase 10: B10 Fresh-Vault Bootstrap And Node/WebSocket Doctor

> **Status**: [DONE]
> **Attempt**: 10
> **Preset**: Bugfix / backlog
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Implemented zero-touch fresh-vault bootstrap for newly copied Obsidian community plugins.
- Added a Node runtime WebSocket doctor check so CDP scripts fail with a clear prerequisite message instead of crashing on `new WebSocket(...)`.
- Made the doctor vault-aware with `--vault-name`, restricted-mode checks, plugin-discovery checks, plugin-enabled checks, and a generated bootstrap remediation command.
- Wired bootstrap into the Windows PowerShell cycle wrapper, macOS/Linux Bash wrapper, and config-driven job runner.
- Fixed two compatibility issues found during live validation: omitted `profile.enabled` no longer enables profiling by accident, and Windows deploy hashing no longer depends on `Get-FileHash`.

## Changed Files

- `README.md`
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/evals/evals.json`
- `custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json`
- `custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_cdp_common.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_bootstrap_plugin.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-10.md`

## Implementation Notes

- `obsidian_debug_bootstrap_plugin.mjs` disables restricted mode, checks the target vault plugin catalog, reloads the vault if the copied plugin is not yet discovered, restarts only if reload polling still fails, and enables the plugin once discovered.
- `obsidian_debug_doctor.mjs` now reports `node-websocket-global`, `restricted-mode`, `plugin-discovered`, and `plugin-enabled` checks. With `--fix`, the generated script can deploy missing artifacts and then call bootstrap.
- `obsidian_cdp_common.mjs` now exposes `ensureGlobalWebSocket()` so CDP users get an actionable Node runtime message when WebSocket support is missing.
- The job spec now has a `bootstrap` section; direct wrappers support `-SkipBootstrap` / `--skip-bootstrap` and timing knobs for polling/reload/restart/enable waits.

## Windows Smoke Results

- **Doctor fresh state**: `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b10/windows-doctor-plugin-repo --plugin-id native-smoke-b10-doctor-win --test-vault-plugin-dir C:/Users/lt/Desktop/Write/testvault/.obsidian/plugins/native-smoke-b10-doctor-win --vault-name testvault --obsidian-command obsidian --platform windows --fix --output .tmp-skills/autopilot-b10/windows-doctor-before.json` reported the expected missing vault install plus `plugin-discovered` / `plugin-enabled` warnings and generated `doctor-fixes.ps1`.
- **Generated fix script**: `powershell -NoProfile -ExecutionPolicy Bypass -File .tmp-skills/autopilot-b10/doctor-fixes.ps1` copied the fixture, ran bootstrap, reloaded `testvault`, discovered `native-smoke-b10-doctor-win`, and enabled it without manual intervention.
- **Doctor after fix**: `windows-doctor-after.json` had all runtime/build/deploy/CLI checks passing; only CDP was a warning because local Windows Obsidian was not exposing port `9222`.
- **Job/cycle fresh state**: `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b10/windows-job.json --platform windows --mode run --output .tmp-skills/autopilot-b10/windows-job-plan.json` deployed `native-smoke-b10-job-win`, auto-bootstrapped discovery, enabled the plugin, reloaded it through the CLI, captured console logs, and wrote `bootstrap-report.json`.

## macOS Smoke Results

- **Host**: Mac Mini `192.168.31.215`, Obsidian `1.12.7`, Node.js `25.6.1`, `obsidian` CLI at `/usr/local/bin/obsidian`.
- **CDP launch**: `bash custom/obsidian-plugin-autodebug/scripts/obsidian_mac_restart_cdp.sh /Applications/Obsidian.app 9222 25` exposed the `testvault` CDP target.
- **Doctor fresh state**: native doctor reported the expected missing fresh install, passed `node-websocket-global`, passed CDP target discovery, and generated `doctor-fixes.sh`.
- **Generated fix script**: `bash .tmp-b10/doctor-fixes.sh` copied `native-smoke-b10-doctor-mac`, ran bootstrap, reloaded the vault, discovered the plugin, and enabled it.
- **Doctor after fix**: all runtime/build/deploy/CLI/CDP checks passed for `native-smoke-b10-doctor-mac`.
- **Job/cycle fresh state**: `obsidian_debug_job.mjs --platform bash --mode run` deployed `native-smoke-b10-job-mac2`, auto-bootstrapped discovery, reloaded over CDP, and produced passing bootstrap/CDP/onload assertions. The final diagnosis was `warning` only because the shared Mac `testvault` also emitted unrelated `opencodian` stale-session `404` logs; assertion summary had no blocking failures.

## Validation Results

- `node --check custom\obsidian-plugin-autodebug\scripts\obsidian_cdp_common.mjs` — passed.
- `node --check custom\obsidian-plugin-autodebug\scripts\obsidian_debug_bootstrap_plugin.mjs` — passed.
- `node --check custom\obsidian-plugin-autodebug\scripts\obsidian_debug_doctor.mjs` — passed.
- `node --check custom\obsidian-plugin-autodebug\scripts\obsidian_debug_job.mjs` — passed.
- `node --check custom\obsidian-plugin-autodebug\scripts\obsidian_debug_analyze.mjs` — passed.
- PowerShell parser validation for `obsidian_plugin_debug_cycle.ps1` — passed.
- Git Bash `bash -n` validation for `obsidian_plugin_debug_cycle.sh` — passed.
- Simulated missing `globalThis.WebSocket` guard — passed with an explicit “unavailable” message.
- `git diff --check` — passed.

## Remaining Risks

- The Windows local Obsidian session did not expose CDP port `9222`, so Windows CDP smoke stayed a doctor warning; the Windows CLI bootstrap path still passed end-to-end.
- The Mac `testvault` is shared with OpenCodian and still emits unrelated stale-session `404` logs during CDP traces. The bootstrap/reload assertions pass, but diagnosis status can be `warning` when those unrelated signatures are present.
