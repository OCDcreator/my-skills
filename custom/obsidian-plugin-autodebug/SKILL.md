---
name: obsidian-plugin-autodebug
description: Run a fully automated Obsidian plugin debug/development loop: environment doctor, build, deploy to a test vault, reload the plugin with the Obsidian CLI or CDP, watch source changes, reset plugin state safely, watch console/errors, capture screenshots, inspect DOM/CSS, assert expected UI health, save baselines, compare/profile runs, restore vault state, and produce diagnosis/HTML reports with reusable playbooks. Use this whenever the user says 全自动调试, 自动开发 Obsidian 插件, 开机启动慢, 首次启动慢, dev console, 控制台日志, reload plugin, screenshot, DOM check, build + deploy + reload, Test Vault, profile startup, watch on save, reset plugin state, or asks an agent to run Obsidian and diagnose plugin behavior end-to-end.
---

# Obsidian Plugin Autodebug

Use this skill to turn Obsidian plugin development into an unattended loop:

1. build the plugin,
2. deploy the generated files into a test vault,
3. reload the plugin in a running Obsidian app,
4. capture console/errors/logs,
5. inspect screenshot/DOM/CSS,
6. diagnose the slow or broken step,
7. patch and repeat.

## Relationship To `obsidian-cli`

The `obsidian-cli` skill provides the primitive app-control commands:

- `obsidian plugin:reload id=<plugin-id>`
- `obsidian dev:console limit=200`
- `obsidian dev:errors`
- `obsidian dev:screenshot path=<file>`
- `obsidian dev:dom selector=<css> all`
- `obsidian dev:css selector=<css> prop=<name>`
- `obsidian eval code="<javascript>"`

This skill is the higher-level workflow wrapper around those commands. Prefer the CLI path first because it is stable and user-friendly. If CLI polling misses timing-critical logs, fall back to direct Chrome DevTools Protocol (CDP) capture only for that diagnostic pass.

On Windows, the `obsidian` command is often the installed Obsidian app executable. On macOS, the plain app binary is **not** a full CLI replacement. If `obsidian` is not in `PATH`, use CDP-first automation and only use the app bundle path for launching:

```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian
```

The bundled scripts support both modes via an explicit command override.

## Preconditions

Before editing, quickly detect:

- Obsidian is running and `obsidian help` includes the `Developer:` commands.
- The repo is an Obsidian plugin: `manifest.json`, `package.json`, and a generated `dist/main.js` or equivalent build output.
- The plugin id from `manifest.json`.
- The test vault plugin directory, usually `<vault>/.obsidian/plugins/<plugin-id>/`.
- The repo’s own instructions for build, deploy, and validation. If an `AGENTS.md` requires a specific build/deploy order, follow it over this generic workflow.

If the repo already has a release/deploy skill or script, reuse it instead of inventing a parallel deployment path.

## Default Autodebug Loop

### 1. Establish Baseline

Run the smallest checks that prove the app-control surface is available:

```bash
obsidian version
obsidian plugins:enabled filter=community versions
obsidian plugin id=<plugin-id>
obsidian dev:debug on
obsidian dev:console limit=20
obsidian dev:errors
```

Clear stale buffers before a reload-focused run:

```bash
obsidian dev:debug on
obsidian dev:console clear
obsidian dev:errors clear
```

### 2. Build

Prefer the repo’s documented command, often:

```bash
npm run build
```

For diagnosis changes, run targeted tests first when available, then the required gate from the repo instructions. Keep lint warnings as blockers if the repo says so.

### 3. Deploy

Copy only generated runtime artifacts into the test vault plugin directory:

- `dist/main.js` → `<test-vault>/.obsidian/plugins/<plugin-id>/main.js`
- `dist/manifest.json` → `<test-vault>/.obsidian/plugins/<plugin-id>/manifest.json`
- `dist/styles.css` → `<test-vault>/.obsidian/plugins/<plugin-id>/styles.css`
- `dist/assets/` → `<test-vault>/.obsidian/plugins/<plugin-id>/assets/` when bundled assets changed

Verify deployment by hash or `BUILD_ID`. Do not reload until the copy has completed.

### 4. Reload

Use the CLI reload first:

```bash
obsidian plugin:reload id=<plugin-id>
```

If reload fails, capture `obsidian dev:errors` immediately. Only use disable/enable fallback when reload is unavailable or clearly stuck:

```bash
obsidian plugin:disable id=<plugin-id>
obsidian plugin:enable id=<plugin-id>
```

### 5. Watch Logs

Poll the captured console while the plugin starts:

```bash
obsidian dev:console limit=200
obsidian dev:errors
```

For a live-ish loop in PowerShell:

```powershell
$end = (Get-Date).AddSeconds(20)
while ((Get-Date) -lt $end) {
  obsidian dev:console limit=200
  obsidian dev:errors
  Start-Sleep -Milliseconds 1000
}
```

Save logs under a repo-local debug folder such as `.obsidian-debug/` or `tmp/`. Do not commit raw runtime logs unless the user asks.

The preferred handoff now has two layers:

- raw artifacts such as `console-watch.log`, `errors.log`, DOM, screenshot, and optional CDP trace,
- a generated `diagnosis.json` that turns those artifacts into assertions, timings, issue signatures, and next-step recommendations.

### 6. Screenshot And DOM Check

Capture what the user would see:

```bash
obsidian dev:screenshot path=.obsidian-debug/screenshot.png
obsidian dev:dom selector=".workspace-leaf.mod-active" all
obsidian dev:dom selector=".opencodian-view" all text
obsidian dev:css selector=".opencodian-view" prop=display
```

Use DOM checks for deterministic assertions:

- the plugin view exists,
- the expected root selector is visible,
- error banners are absent,
- the model selector/button/status text reached the expected state,
- accessibility-relevant text is present.

Use screenshots for visual regressions or layout glitches.

## Performance Debugging Pattern

When the user reports “first startup/open is slow,” split the timeline instead of guessing:

1. Plugin `onload` / startup total.
2. Deferred runtime warmup such as local server start.
3. View open / tab restore.
4. Conversation/message hydration.
5. Post-render UI tail.
6. Background server snapshot refreshes.

Add substep timing logs around each suspected phase. For Obsidian plugin UI, it is common for `onload` to be fast while the visible sidebar is slow because view hydration waits for a server-dependent request.

Apply this fix pattern when safe:

- keep identity/state shell writes synchronous,
- move slow server snapshots to a background refresh,
- keep stale guards before writing async results,
- log background completion separately,
- verify the visible `view-open` timing improves while the background request still completes.

The OpenCodian debugging lesson: a `view-open` path that looked like an 8s plugin startup was actually `applyLoadedConversationHydrationTail()` awaiting a context usage server snapshot while the local OpenCode server was still starting. Making the snapshot refresh fire-and-forget reduced visible open time from seconds to milliseconds while preserving later token/cost updates.

## Config-Driven Job Specs

Prefer `scripts/obsidian_debug_job.mjs` when a debug loop needs to be repeatable across Windows PowerShell and macOS/Linux Bash. A job spec describes the same phases as the direct cycle wrappers without forcing agents to hand-write long platform-specific command templates:

- `runtime`: plugin id, test vault plugin directory, working directory, Obsidian command, vault name, and output directory.
- `build` / `deploy` / `reload` / `logWatch`: build argv, deploy source, CLI or CDP reload mode, and console polling settings.
- `scenario` / `assertions` / `comparison`: optional view-opening scenario, assertion JSON, DOM selector, and baseline diagnosis comparison.
- `scenario.surfaceProfile`: optional plugin-surface metadata file that declares likely open commands, view types, settings tabs, and selector hints for generic view-open/discovery runs.
- `profile` / `report`: repeated-cycle timing summary and optional HTML report generation.
- `state`: optional vault snapshot, plugin-local reset preview/reset, and restore-after-run handling.

Start by copying `job-specs/generic-debug-job.template.json` into the plugin repository, then replace only the generic placeholders such as `your-plugin-id` and `/path/to/test-vault`. Keep repo-local absolute paths in the runtime copy, not in committed shared templates.

Dry-run the PowerShell command plan:

```powershell
node "C:\path\to\obsidian-plugin-autodebug\scripts\obsidian_debug_job.mjs" `
  --job "C:\path\to\plugin-repo\.obsidian-debug\job.json" `
  --platform windows `
  --dry-run
```

Dry-run the Bash command plan:

```bash
node /path/to/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs \
  --job /path/to/plugin-repo/.obsidian-debug/job.json \
  --platform bash \
  --dry-run
```

When the dry-run plan is safe, execute it:

```bash
node /path/to/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs \
  --job /path/to/plugin-repo/.obsidian-debug/job.json \
  --platform auto \
  --mode run
```

The direct PowerShell and Bash cycle wrappers below remain supported as fallback paths. Use them when a single ad-hoc pass is clearer than introducing a job file, or when a repository already has stricter build/deploy instructions that should stay outside the generic job runner.

## Bundled Scripts

### Windows CLI/CDP cycle

Use `scripts/obsidian_plugin_debug_cycle.ps1` for a Windows cycle:

```powershell
& "C:\path\to\obsidian-plugin-autodebug\scripts\obsidian_plugin_debug_cycle.ps1" `
  -PluginId "opencodian" `
  -TestVaultPluginDir "C:\Users\lt\Desktop\Write\testvault\.obsidian\plugins\opencodian" `
  -WatchSeconds 20 `
  -DomSelector ".opencodian-view"
```

For a named vault:

```powershell
& "C:\path\to\obsidian-plugin-autodebug\scripts\obsidian_plugin_debug_cycle.ps1" `
  -VaultName "testvault" `
  -PluginId "opencodian" `
  -TestVaultPluginDir "C:\Users\lt\Desktop\Write\testvault\.obsidian\plugins\opencodian"
```

The script writes:

- `.obsidian-debug/build.log`
- `.obsidian-debug/deploy-report.json`
- `.obsidian-debug/scenario-report.json` when a scenario runs
- `.obsidian-debug/console-watch.log`
- `.obsidian-debug/errors.log`
- `.obsidian-debug/dom.html` or `.obsidian-debug/dom.txt`
- `.obsidian-debug/screenshot.png`
- `.obsidian-debug/summary.json`
- `.obsidian-debug/diagnosis.json`

The CLI watch logs are incremental: repeated `dev:console` / `dev:errors` polling only appends the new tail instead of replaying the whole buffer every second. If no errors appear during the watch window, `errors.log` stays concise with a single “no errors captured” note.

`diagnosis.json` adds:

- assertion results such as screenshot/DOM/deploy/scenario success,
- custom assertions from a JSON file when you pass `--assertions` / `-AssertionsPath`,
- extracted timing milestones such as startup/view-open/server-ready/chat-ready,
- issue signatures from `rules/issue-signatures.json`,
- deduplicated recommendations for the next debugging pass.

Example assertions live under `assertions/`. Use `assertions/plugin-view-health.template.json` as the generic starting point for a new plugin, then replace the selector/error placeholders with your own expected UI markers. `assertions/opencodian-view-health.json` remains a concrete real-world example of the same pattern.

When a plugin does not have one obvious `commandId`, capture reusable view-open metadata in `surface-profiles/plugin-surface.template.json`. The scenario runner resolves strategies in this order: declared metadata first, then Obsidian commands/view types, then CDP DOM heuristics. `scenario-report.json` now includes a machine-readable `surfaceDiscovery` block with the selected strategy plus discovered root selectors, headings, settings surfaces, error banners, and empty states.

To compare a new run against a previous diagnosis, pass `-CompareDiagnosisPath <old diagnosis.json>` on Windows or `--compare-diagnosis <old diagnosis.json>` on macOS/Linux. The scripts then write `.obsidian-debug/comparison.json` with timing deltas, added/removed signatures, and assertion regressions/fixes.

Before a long debugging pass, run the cross-platform doctor to catch missing build outputs, a mismatched plugin id, a broken test-vault install, missing Obsidian developer commands, or an unavailable CDP target:

```bash
node scripts/obsidian_debug_doctor.mjs \
  --repo-dir /path/to/plugin-repo \
  --plugin-id opencodian \
  --test-vault-plugin-dir /path/to/testvault/.obsidian/plugins/opencodian \
  --obsidian-command obsidian \
  --cdp-port 9222 \
  --output .obsidian-debug/doctor.json
```

Treat `fail` checks as blockers. Treat `warn` checks as actionable context: for example, the macOS app binary can pass launch checks but still warn that the full Obsidian CLI developer commands are unavailable, in which case use the CDP-first flow.

You can also run a scenario before the watch/capture phase. The built-in `open-plugin-view` scenario is useful when the plugin exposes a command such as `<plugin-id>:open-view` and you want DOM/screenshot capture to target the plugin pane:

```powershell
& "C:\path\to\obsidian-plugin-autodebug\scripts\obsidian_plugin_debug_cycle.ps1" `
  -VaultName "testvault" `
  -PluginId "opencodian" `
  -TestVaultPluginDir "C:\Users\lt\Desktop\Write\testvault\.obsidian\plugins\opencodian" `
  -ScenarioCommandId "opencodian:open-view" `
  -AssertionsPath "C:\path\to\obsidian-plugin-autodebug\assertions\opencodian-view-health.json" `
  -DomSelector ".opencodian-container"
```

Add `-UseCdp` to swap the reload/watch phase to a real-time CDP trace instead of CLI polling:

```powershell
& "C:\path\to\obsidian-plugin-autodebug\scripts\obsidian_plugin_debug_cycle.ps1" `
  -PluginId "opencodian" `
  -TestVaultPluginDir "C:\Users\lt\Desktop\Write\testvault\.obsidian\plugins\opencodian" `
  -UseCdp `
  -WatchSeconds 20
```

### macOS CLI/CDP cycle

Use `scripts/obsidian_plugin_debug_cycle.sh` on macOS:

```bash
bash /path/to/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh \
  --plugin-id opencodian \
  --test-vault-plugin-dir "/Users/me/testvault/.obsidian/plugins/opencodian" \
  --obsidian-command "/Applications/Obsidian.app/Contents/MacOS/Obsidian" \
  --scenario-command-id "opencodian:open-view" \
  --assertions "/path/to/obsidian-plugin-autodebug/assertions/opencodian-view-health.json" \
  --watch-seconds 20 \
  --dom-selector ".opencodian-view"
```

To use CDP on macOS:

```bash
bash /path/to/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh \
  --plugin-id opencodian \
  --test-vault-plugin-dir "/Users/me/testvault/.obsidian/plugins/opencodian" \
  --obsidian-command "/Applications/Obsidian.app/Contents/MacOS/Obsidian" \
  --use-cdp \
  --watch-seconds 20
```

For multi-window vault setups, add `--cdp-target-title-contains testvault` so the trace attaches to the correct Obsidian window. If you also need to force-open a plugin view before screenshot/DOM capture, add `--cdp-eval-after-reload` with an app-context expression such as:

```javascript
(async () => {
  const leaf = app.workspace.getLeavesOfType('opencodian-view')[0] ?? app.workspace.getRightLeaf(false);
  await leaf.setViewState({ type: 'opencodian-view', active: true });
  return app.workspace.getLeavesOfType('opencodian-view').length;
})()
```

If the Mac does not expose an `obsidian` CLI command, restart Obsidian with CDP first:

```bash
bash /path/to/obsidian-plugin-autodebug/scripts/obsidian_mac_restart_cdp.sh \
  /Applications/Obsidian.app \
  9222
```

When `--skip-build` / `--skip-deploy` or `-SkipBuild` / `-SkipDeploy` is used, `summary.json` now reports those omitted artifacts as `null` instead of placeholder paths. This makes downstream automation easier to consume.

### Repeatable state and profiling

Use `scripts/obsidian_debug_vault_state.mjs` before experiments that mutate vault/plugin state. `--targets` is a `|`-separated list of files or directories to snapshot:

```bash
node scripts/obsidian_debug_vault_state.mjs \
  --mode snapshot \
  --snapshot-dir .obsidian-debug/vault-state \
  --targets "/path/to/vault/.obsidian/plugins/opencodian/manifest.json|/path/to/vault/.obsidian/plugins/opencodian/data.json"
```

Restore the exact prior state after the run:

```bash
node scripts/obsidian_debug_vault_state.mjs \
  --mode restore \
  --snapshot-dir .obsidian-debug/vault-state
```

For plugin-local state resets, use `scripts/obsidian_debug_reset_state.mjs`. Start with preview mode so you can inspect the resolved paths safely:

```bash
node scripts/obsidian_debug_reset_state.mjs \
  --mode preview \
  --state-plan state-plans/plugin-data-reset.json \
  --vault-root /path/to/vault \
  --plugin-id your-plugin-id
```

Then run the reset and later restore the same snapshot:

```bash
node scripts/obsidian_debug_reset_state.mjs \
  --mode reset \
  --state-plan state-plans/plugin-data-reset.json \
  --vault-root /path/to/vault \
  --plugin-id your-plugin-id \
  --snapshot-dir .obsidian-debug/plugin-state-reset

node scripts/obsidian_debug_reset_state.mjs \
  --mode restore \
  --snapshot-dir .obsidian-debug/plugin-state-reset
```

`plugin-data-reset.json` is intentionally generic and conservative. For a real plugin, copy it and add only the plugin-local files/directories you truly want to clear.

### Continuous watch mode

Use `scripts/obsidian_debug_watch.mjs` to automate the “save → build → deploy → reload → diagnose” loop. It watches one or more roots, debounces bursts of changes, and writes one run directory per trigger:

```bash
node scripts/obsidian_debug_watch.mjs \
  --watch-roots "src|styles" \
  --cwd /path/to/plugin-repo \
  --root-output .obsidian-debug/watch \
  --debounce-ms 1000 \
  --command "bash /path/to/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh --plugin-id your-plugin-id --test-vault-plugin-dir /path/to/testvault/.obsidian/plugins/your-plugin-id --output-dir {{outputDir}} --watch-seconds 8"
```

Useful watch-mode switches:

- `--max-runs 1` for CI-like or smoke-test validation,
- `--once-on-start true` to force one run before any file change,
- `--exclude ".git|node_modules|dist|.obsidian-debug"` to avoid noisy triggers,
- `--timeout-ms 30000` so unattended experiments do not watch forever.

Use `scripts/obsidian_debug_profile.mjs` when one run is too noisy to trust. The `--command` value is any shell command that runs one debug cycle. The profiler replaces `{{outputDir}}` with each run directory and `{{run}}` with the run number:

```bash
node scripts/obsidian_debug_profile.mjs \
  --runs 3 \
  --cwd /path/to/plugin-repo \
  --root-output .obsidian-debug/profile \
  --label startup-warm \
  --mode warm \
  --command "bash /path/to/obsidian-plugin-autodebug/scripts/obsidian_plugin_debug_cycle.sh --plugin-id opencodian --test-vault-plugin-dir /path/to/testvault/.obsidian/plugins/opencodian --output-dir {{outputDir}} --skip-build --skip-deploy --use-cdp --watch-seconds 8"
```

The profile summary reports average/min/max timings, status counts, signature counts, failed assertion counts, and per-run metadata. Use it to separate real regressions from normal startup variance.

Use `scripts/obsidian_debug_baseline.mjs` to save a known-good run and compare later candidates against it:

```bash
node scripts/obsidian_debug_baseline.mjs \
  --mode save \
  --baseline-root .obsidian-debug/baselines \
  --name warm-start-healthy \
  --diagnosis .obsidian-debug/profile/run-01/diagnosis.json \
  --profile .obsidian-debug/profile/profile-summary.json \
  --report .obsidian-debug/profile/report.html

node scripts/obsidian_debug_baseline.mjs \
  --mode compare \
  --baseline-root .obsidian-debug/baselines \
  --name warm-start-healthy \
  --candidate-diagnosis .obsidian-debug/profile/run-03/diagnosis.json
```

Baselines are especially useful when you are chasing performance drift: save one cold-start baseline and one warm-start baseline, then compare new runs against the correct class instead of mixing them together.

Generate a portable HTML report from the machine-readable artifacts:

```bash
node scripts/obsidian_debug_report.mjs \
  --diagnosis .obsidian-debug/profile/run-03/diagnosis.json \
  --profile .obsidian-debug/profile/profile-summary.json \
  --comparison .obsidian-debug/profile/run-03/comparison.json \
  --output .obsidian-debug/profile/report.html
```

Attach or open the HTML report when the user needs an easy review artifact; keep `diagnosis.json` as the canonical automation output.

For custom workflows, point `--scenario-path` / `-ScenarioPath` at a JSON file shaped like `scenarios/open-plugin-view.json`. The built-in scenario runner currently supports:

- `obsidian-cli` steps for vault-scoped Obsidian CLI commands,
- `surface-open` steps that resolve the best generic plugin surface-open strategy,
- `sleep` steps for deterministic settle windows between actions.

Dry-run a synthetic surface profile without touching a real Obsidian app:

```bash
node scripts/obsidian_debug_scenario_runner.mjs \
  --scenario-name open-plugin-view \
  --plugin-id sample-plugin \
  --surface-profile surface-profiles/synthetic-plugin-surface.fixture.json \
  --dry-run \
  --output .obsidian-debug/scenario-report.json
```

Then run the same `obsidian_plugin_debug_cycle.sh` command with `--use-cdp`. In that mode, the script can still:

- deploy files,
- reload the plugin through app-context JavaScript,
- save a real-time console trace,
- capture a screenshot through `Page.captureScreenshot`,
- query DOM through `document.querySelectorAll`.

Treat the script as a convenience wrapper. If the repository has stricter build/deploy rules, execute those manually and use the CLI sections of this skill for reload/log/screenshot/DOM capture.

## CDP Fallback

Use direct CDP only when the CLI buffer is insufficient for real-time analysis. Typical triggers:

- the user asks for “实时 Console”,
- CLI logs miss early startup messages,
- you need exact event ordering while reload happens,
- you need to evaluate JavaScript repeatedly during startup.

If Obsidian exposes a debugging port, list targets:

```bash
node --input-type=module -e "const t=await (await fetch('http://127.0.0.1:9222/json/list')).json(); console.log(t.map(x=>({title:x.title,url:x.url,ws:x.webSocketDebuggerUrl})))"
```

Connect to the `app://obsidian.md/index.html` target, enable `Runtime` and `Log`, then reload the plugin by evaluating:

```javascript
await app.plugins.disablePlugin('<plugin-id>');
await app.plugins.enablePlugin('<plugin-id>');
```

Save the CDP console stream to a file and cite the exact lines in the handoff.

## Diagnosis Workflow

After each run, inspect `diagnosis.json` before diving into raw logs. Use it to answer:

1. Did the required artifacts exist?
2. Was startup slow, view-open slow, or was the visible delay mostly server readiness?
3. Did any known issue signatures match?
4. Which next-step recommendation is the best next edit or instrumentation pass?

If `diagnosis.json` is inconclusive, then drop to the raw console/CDP logs and add a new signature to `rules/issue-signatures.json` so the next run catches that symptom automatically.

`diagnosis.json` can also include reusable playbooks from `rules/issue-playbooks.json`. Keep them generic: they should point to likely file areas, reusable commands, and safe next actions that apply across many plugins, not only one repository.

### Built-in CDP scripts

Use `scripts/obsidian_cdp_console_watch.mjs` to attach and watch without reloading:

```bash
node scripts/obsidian_cdp_console_watch.mjs \
  --host 127.0.0.1 \
  --port 9222 \
  --duration-seconds 15 \
  --output .obsidian-debug/cdp-console-watch.log
```

Use `scripts/obsidian_cdp_reload_and_trace.mjs` to enable debug flags, clear the console, disable/enable the plugin, and capture real-time logs:

```bash
node scripts/obsidian_cdp_reload_and_trace.mjs \
  --plugin-id opencodian \
  --host 127.0.0.1 \
  --port 9222 \
  --duration-seconds 20 \
  --output .obsidian-debug/cdp-reload-trace.log
```

This is the built-in version of the manual CDP workflow used during the OpenCodian startup investigation.

Use `scripts/obsidian_cdp_capture_ui.mjs` to save DOM HTML/text and a screenshot without relying on the Obsidian CLI:

```bash
node scripts/obsidian_cdp_capture_ui.mjs \
  --host 127.0.0.1 \
  --port 9222 \
  --selector ".workspace-leaf.mod-active" \
  --html-output .obsidian-debug/dom.html \
  --screenshot-output .obsidian-debug/screenshot.png
```

## Final Report Format

When handing back results, include:

- branch/build identity and whether it was deployed to the test vault,
- exact commands run,
- validation results,
- key before/after timings,
- log/screenshot/DOM artifact paths,
- root cause and the code path,
- remaining background long-tail work, if any,
- whether changes were committed.

Keep raw logs out of the final answer; summarize the important lines with file paths and line numbers.
