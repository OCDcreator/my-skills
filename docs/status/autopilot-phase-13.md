# Autopilot Phase 13: B13 Hot Reload Coordination Doctor

> **Status**: [DONE]
> **Attempt**: 5
> **Preset**: Bugfix / backlog
> **Repository**: `my-skills`
> **Date**: 2026-04-19

## Scope

- Added plugin-neutral Hot Reload detection and guidance so doctor runs can spot likely vault/repo reload interference from enabled helper plugins, watch-style scripts, and symlinked test-vault plugin entries.
- Extended the generic job spec plus both Bash/PowerShell cycle wrappers with Hot Reload coordination modes: `controlled` for deterministic explicit reloads and `coexist` for background Hot Reload-friendly capture.
- Propagated Hot Reload coordination metadata into `summary.json`, diagnosis output, and the HTML report so timing/log evidence clearly calls out when Hot Reload may have influenced the capture.
- Documented the new job-spec field and wrapper flags in the skill guide.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json`
- `custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_hot_reload_support.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh`
- `docs/status/autopilot-lane-map.md`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-13.md`

## Implementation Notes

- `obsidian_debug_hot_reload_support.mjs` centralizes vault/repo Hot Reload signal detection plus reusable guidance text for doctor output.
- `obsidian_debug_doctor.mjs` now surfaces `hot-reload-vault`, `hot-reload-repo-signals`, and `hot-reload-coordination` checks, and it can emit runnable cycle-wrapper fix commands for both coordination modes.
- `obsidian_debug_job.mjs` now forwards `reload.hotReload.mode` and `reload.hotReload.settleMs` into generated Bash/PowerShell cycle commands.
- `obsidian_plugin_debug_cycle.sh` and `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1` now support `controlled` settle-before-clear behavior and `coexist` explicit-reload skipping while recording the chosen coordination metadata in `summary.json`.
- `obsidian_debug_analyze.mjs` and `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs` now expose a Hot Reload coordination assertion/card so reports explicitly warn when timings/logs came from coexistence mode instead of a deterministic explicit reload.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_hot_reload_support.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs && node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs` — passed.
- `bash -n custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh` — passed.
- `set -euo pipefail ... node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs ... --output .tmp-skills/autopilot-b13/output/doctor.json ... node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs ... --output .tmp-skills/autopilot-b13/output/job-plan.json ... node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs ... node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs ... node --input-type=module <<'EOF' ... EOF` — passed while proving doctor Hot Reload detection/guidance, job-plan flag emission, diagnosis Hot Reload warning propagation, and report rendering against a synthetic fixture repo/vault.
- `git diff --check` — passed.

## Validation Gaps

- `pwsh` was unavailable on this macOS host, so `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1` could not be parser-checked locally in this round.
- Lint command was blank in the round metadata, so no repo-wide lint step existed to run.
- Typecheck command was blank in the round metadata, so no repo-wide typecheck step existed to run.
- Full test command was blank in the round metadata, so no repo-wide test suite existed to run.
- Build command was blank in the round metadata, so no repo-wide build step existed to run.
- Vulture command was blank in the round metadata, so no dead-code observability run existed to record.

## Next Recommended Slice

- `B14 - Sample-plugin scaffold and bootstrap mode`
