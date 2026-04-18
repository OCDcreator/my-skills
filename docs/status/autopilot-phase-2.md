# Autopilot Phase 2: B2 Generic View-Open And Selector Discovery

> **Status**: [DONE]
> **Attempt**: 2
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B2 - Generic view-open strategy chain and selector discovery`.
- Kept work inside the generic `custom/obsidian-plugin-autodebug` framework.
- Added a plugin-neutral surface discovery script that resolves view-open strategies from declared metadata, catalogued Obsidian commands, workspace view types, settings tabs, and DOM-derived selector hints.
- Updated the built-in `open-plugin-view` scenario to use a generic `surface-open` step and emit machine-readable `surfaceDiscovery` data for downstream assertions.
- Plumbed optional `scenario.surfaceProfile` support through the job spec, Windows PowerShell cycle, and Bash cycle wrappers.
- Added a reusable surface profile template plus a synthetic fixture covering root selectors, headings, settings surfaces, error banners, and empty states.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json`
- `custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json`
- `custom/obsidian-plugin-autodebug/scenarios/open-plugin-view.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scenario_runner.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_surface_discovery.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.ps1`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh`
- `custom/obsidian-plugin-autodebug/surface-profiles/plugin-surface.template.json`
- `custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-2.md`

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_surface_discovery.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scenario_runner.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs` — passed.
- `node -e "const fs=require('fs'); for (const p of ['custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json','custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json','custom/obsidian-plugin-autodebug/scenarios/open-plugin-view.json','custom/obsidian-plugin-autodebug/surface-profiles/plugin-surface.template.json','custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json']) JSON.parse(fs.readFileSync(p,'utf8')); console.log('surface/profile JSON ok');"` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_surface_discovery.mjs --surface-profile custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json --plugin-id sample-plugin --dry-run --output .tmp-autopilot/surface-discovery.json` — passed; emitted strategy chain and discovery output from the synthetic fixture.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_scenario_runner.mjs --scenario-name open-plugin-view --plugin-id sample-plugin --surface-profile custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json --dry-run --output .tmp-autopilot/scenario-report.json` — passed; emitted `surfaceDiscovery` with root selectors, headings, settings surfaces, error banners, empty states, and selected strategy.
- `node -e "const fs=require('fs'); const report=JSON.parse(fs.readFileSync('.tmp-autopilot/scenario-report.json','utf8')); if (!report.success) throw new Error('scenario dry-run failed'); if (!report.surfaceDiscovery?.rootSelectors?.length) throw new Error('root selectors missing'); if (!report.surfaceDiscovery?.headings?.length) throw new Error('headings missing'); if (!report.surfaceDiscovery?.settingsSurfaces?.length) throw new Error('settings surfaces missing'); if (!report.surfaceDiscovery?.errorBanners?.length) throw new Error('error banners missing'); if (!report.surfaceDiscovery?.emptyStates?.length) throw new Error('empty states missing'); if (report.surfaceDiscovery.selectedStrategy?.kind !== 'obsidian-command') throw new Error('selected strategy missing'); console.log('scenario discovery assertions ok');"` — passed when run after the scenario report was written. One earlier parallel invocation raced the report file and failed with `ENOENT`; the sequential rerun passed without code changes.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json --platform windows --dry-run` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json --platform bash --dry-run` — passed.
- `node -e "const fs=require('fs'); const job=JSON.parse(fs.readFileSync('custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json','utf8')); job.runtime.pluginId='sample-plugin'; job.runtime.testVaultPluginDir='C:/vault/.obsidian/plugins/sample-plugin'; job.scenario.enabled=true; job.scenario.commandId=''; job.scenario.surfaceProfile='custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json'; fs.mkdirSync('.tmp-autopilot',{recursive:true}); fs.writeFileSync('.tmp-autopilot/job-with-surface.json', JSON.stringify(job,null,2)); console.log('job fixture ok');"` — passed; generated a temporary job fixture with `scenario.surfaceProfile` enabled.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-autopilot/job-with-surface.json --platform windows --dry-run --output .tmp-autopilot/job-plan-windows.json` — passed; PowerShell plan includes `-SurfaceProfilePath`.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-autopilot/job-with-surface.json --platform bash --dry-run --output .tmp-autopilot/job-plan-bash.json` — passed; Bash plan includes `--surface-profile`.
- `node -e "const fs=require('fs'); for (const p of ['.tmp-autopilot/job-plan-windows.json','.tmp-autopilot/job-plan-bash.json']) { const plan=JSON.parse(fs.readFileSync(p,'utf8')); const args=plan.commands[0].args; if (!args.includes('custom/obsidian-plugin-autodebug/surface-profiles/synthetic-plugin-surface.fixture.json')) throw new Error('surface profile missing from '+p); } console.log('job surface-profile plumbing ok');"` — passed.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- Continue with `B3 - Rich generic assertions and performance budgets`.
