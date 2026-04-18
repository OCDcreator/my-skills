# Autopilot Phase 13: B14 Sample-Plugin Scaffold And Bootstrap Mode

> **Status**: [DONE]
> **Attempt**: 7
> **Preset**: Bugfix / backlog
> **Repository**: `my-skills`
> **Date**: 2026-04-19

## Scope

- Added a new scaffold generator for `custom/obsidian-plugin-autodebug` so the framework can create a minimal debug-ready sample plugin workspace instead of assuming an existing plugin repo already exists.
- Kept the scaffold plugin-agnostic by generating a sample view/settings surface, zero-dependency local build script, local fresh-vault target, and tailored autodebug job/assertion/surface files from the shared templates.
- Updated skill and eval docs to separate the new scaffold/bootstrap flow from the existing-plugin retrofit flow that still starts from `job-specs/generic-debug-job.template.json`.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/evals/evals.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scaffold_plugin.mjs`
- `docs/status/autopilot-lane-map.md`
- `docs/status/autopilot-phase-13.md`
- `docs/status/autopilot-round-roadmap.md`

## Implementation Notes

- `obsidian_debug_scaffold_plugin.mjs` generates a minimal plugin workspace with `manifest.json`, `src/main.js`, `styles.css`, `scripts/build.mjs`, a local `test-vault/`, and a pre-populated `dist/` plus deployed vault plugin directory so bootstrap smoke runs start from a realistic fresh-vault copy target.
- The scaffold reuses existing shared templates for the job spec, JSON schema, scenario, surface profile, and assertions, then fills them with plugin-specific values such as command ids, selectors, view type, and local vault paths.
- The generated sample plugin includes a simple view plus settings tab so selector discovery, surface-open commands, and assertions have a real plugin-neutral UI surface instead of placeholder files only.
- The job scaffold keeps `runtime.cwd` and `testVaultPluginDir` immediately runnable, enables bootstrap by default, and emits both Bash and PowerShell dry-run friendly plans through the existing job runner.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scaffold_plugin.mjs` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scaffold_plugin.mjs --output-dir .tmp-skills/autopilot-b14/sample-plugin-smoke --plugin-id autopilot-sample-plugin --plugin-name "Autopilot Sample Plugin" --obsidian-command "$PWD/.tmp-skills/autopilot-b14/fake-obsidian" --output .tmp-skills/autopilot-b14/scaffold-report.json` — passed and generated the scaffolded sample workspace plus autodebug configs.
- `node --check .tmp-skills/autopilot-b14/sample-plugin-smoke/scripts/build.mjs && node --check .tmp-skills/autopilot-b14/sample-plugin-smoke/src/main.js && node .tmp-skills/autopilot-b14/sample-plugin-smoke/scripts/build.mjs --check` — passed for the generated sample workspace.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b14/sample-plugin-smoke --plugin-id autopilot-sample-plugin --test-vault-plugin-dir .tmp-skills/autopilot-b14/sample-plugin-smoke/test-vault/.obsidian/plugins/autopilot-sample-plugin --platform bash --obsidian-command "$PWD/.tmp-skills/autopilot-b14/fake-obsidian" --output .tmp-skills/autopilot-b14/doctor-before.json` — passed and warned that the scaffolded plugin was copied but not yet discovered/enabled in the fresh vault.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_bootstrap_plugin.mjs --plugin-id autopilot-sample-plugin --test-vault-plugin-dir .tmp-skills/autopilot-b14/sample-plugin-smoke/test-vault/.obsidian/plugins/autopilot-sample-plugin --obsidian-command "$PWD/.tmp-skills/autopilot-b14/fake-obsidian" --output .tmp-skills/autopilot-b14/bootstrap-report.json --reload-wait-ms 0 --restart-wait-ms 0 --enable-wait-ms 0 --discovery-timeout-ms 1500 --poll-interval-ms 100` — passed and captured the reload-plus-enable bootstrap path for the scaffolded sample.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b14/sample-plugin-smoke --plugin-id autopilot-sample-plugin --test-vault-plugin-dir .tmp-skills/autopilot-b14/sample-plugin-smoke/test-vault/.obsidian/plugins/autopilot-sample-plugin --platform bash --obsidian-command "$PWD/.tmp-skills/autopilot-b14/fake-obsidian" --output .tmp-skills/autopilot-b14/doctor-after.json` — passed and confirmed the scaffolded plugin was discoverable and enabled after bootstrap.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b14/sample-plugin-smoke/autodebug/autopilot-sample-plugin-debug-job.json --platform bash --dry-run --output .tmp-skills/autopilot-b14/job-plan-bash.json` — passed and produced the Bash scaffold plan.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b14/sample-plugin-smoke/autodebug/autopilot-sample-plugin-debug-job.json --platform windows --dry-run --output .tmp-skills/autopilot-b14/job-plan-windows.json` — passed and produced the Windows PowerShell scaffold plan.
- `node --input-type=module <<'EOF' ... EOF` — passed while asserting generated scaffold files, doctor-before warning state, bootstrap success, doctor-after discovery/enabled state, and both dry-run job plans.
- `git diff --check` — passed.

## Validation Gaps

- Lint command was blank in the round metadata, so no repo-wide lint step existed to run.
- Typecheck command was blank in the round metadata, so no repo-wide typecheck step existed to run.
- Full test command was blank in the round metadata, so no repo-wide full test step existed to run.
- Build command was blank in the round metadata, so no separate repo-wide build step existed beyond the targeted scaffold smoke checks above.
- Vulture command was blank in the round metadata, so no dead-code observability run existed to record.
- This round ran on macOS only; Windows coverage came from the generated PowerShell dry-run plan rather than a native Windows host execution.

## Next Recommended Slice

- `B15 - Optional testing-framework and CI templates`
