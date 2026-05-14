# Obsidian Plugin Autodebug Command Reference

Read this file only when you need concrete script commands, flags, or handoff examples. For the authoritative option list, run the relevant script with `--help`; every runnable `.mjs` helper should exit 0 for `--help`.

## Desktop Control Preconditions

- The built-in wrappers now try to auto-launch/focus Obsidian and the target vault before relying on `obsidian help`, `obsidian dev:*`, or `obsidian plugin:*`.
- If `obsidian help` says it cannot find Obsidian, treat that as a missing app-control precondition, not a plugin build failure; run the launch helper first instead of debugging plugin code immediately.
- CDP helpers require Obsidian to be started with a reachable debug port, normally `127.0.0.1:9222`.
- In CDP mode, the launch helper now performs one restart fallback on Windows or macOS if launch/focus recovery still fails to expose the debug port.
- In multi-window setups, pass `--target-title-contains <vault-name>` or the equivalent job-spec setting to avoid attaching to the wrong vault window.

## Primary Entrypoints

| Need | Script | Typical command |
| --- | --- | --- |
| Launch/focus Obsidian first | `scripts/obsidian_debug_launch_app.mjs` | `node scripts/obsidian_debug_launch_app.mjs --mode cli --vault-name "<vault>" --output .obsidian-debug/app-launch.json` |
| Restart for CDP on Windows | `scripts/obsidian_windows_restart_cdp.ps1` | `powershell -File scripts/obsidian_windows_restart_cdp.ps1 -AppPath "C:\Program Files\Obsidian\Obsidian.exe" -Port 9222` |
| Restart for CDP on macOS | `scripts/obsidian_mac_restart_cdp.sh` | `bash scripts/obsidian_mac_restart_cdp.sh /Applications/Obsidian.app 9222` |
| Check environment | `scripts/obsidian_debug_doctor.mjs` | `node scripts/obsidian_debug_doctor.mjs --repo-dir <repo> --plugin-id <id> --test-vault-plugin-dir <vault>/.obsidian/plugins/<id> --output .obsidian-debug/doctor.json --fix` |
| Scaffold sample plugin | `scripts/obsidian_debug_scaffold_plugin.mjs` | `node scripts/obsidian_debug_scaffold_plugin.mjs --output-dir <sample> --plugin-id sample-plugin --plugin-name "Sample Plugin"` |
| Generate backend routing | `scripts/obsidian_debug_control_backend_support.mjs` | `node scripts/obsidian_debug_control_backend_support.mjs --doctor .obsidian-debug/doctor.json --output .obsidian-debug/control-backends.json` |
| Run config-driven loop | `scripts/obsidian_debug_job.mjs` | `node scripts/obsidian_debug_job.mjs --job .obsidian-debug/job.json --platform auto --mode run` |
| Run JS behavior assertion | `scripts/obsidian_eval_file.mjs` | `node scripts/obsidian_eval_file.mjs --vault-name "<vault>" --file .obsidian-debug/assertion.js --clear-before --capture-after --output .obsidian-debug/assertion-result.json` |
| Generate visual review pack | `scripts/obsidian_debug_visual_review.mjs` | `node scripts/obsidian_debug_visual_review.mjs --diagnosis .obsidian-debug/diagnosis.json --output .obsidian-debug/visual-review.json --html-output .obsidian-debug/visual-review.html` |
| Windows ad-hoc cycle | `scripts/obsidian_plugin_debug_cycle.ps1` | `powershell -File scripts/obsidian_plugin_debug_cycle.ps1 -PluginId <id> -TestVaultPluginDir <dir>` |
| Bash/macOS ad-hoc cycle | `scripts/obsidian_plugin_debug_cycle.sh` | `bash scripts/obsidian_plugin_debug_cycle.sh --plugin-id <id> --test-vault-plugin-dir <dir>` |

Prefer `obsidian_debug_job.mjs` for repeatable work and the shell wrappers for one-off local smoke passes.
Both shell wrappers call the launch helper automatically unless you opt out with `--skip-app-launch`.

## Job Specs

Start from `job-specs/generic-debug-job.template.json` for an existing plugin. Fill only repo-local values in the copied job file:

- `runtime`: plugin id, repo cwd, test-vault plugin directory, vault name, Obsidian command, output directory.
- `runtime.appLaunch`: optional auto-launch policy (`enabled`, `mode`, `appPath`, `vaultUri`, `vaultPath`, `waitMs`, `pollIntervalMs`).
- `build` / `deploy` / `bootstrap` / `reload` / `logWatch`: package-manager-aware build, generated artifact copy, fresh-vault discovery, CLI/CDP reload, console polling.
- `scenario` / `assertions`: view-opening strategy, surface profile, assertion JSON, DOM selector.
- `comparison` / `profile` / `report`: baseline comparison, repeated-run profiling, HTML report generation.
- `state`: optional vault snapshot, plugin-local state reset, and restore-after-run behavior.

Dry-run before execution:

```bash
node scripts/obsidian_debug_job.mjs --job .obsidian-debug/job.json --platform windows --dry-run
node scripts/obsidian_debug_job.mjs --job .obsidian-debug/job.json --platform bash --dry-run
```

## CLI-First Local Loop

Use this when `obsidian help` works and includes developer commands:

```bash
obsidian dev:debug on
obsidian dev:console clear
obsidian dev:errors clear
obsidian plugin:reload id=<plugin-id>
obsidian dev:console limit=200
obsidian dev:errors
obsidian dev:screenshot path=.obsidian-debug/screenshot.png
obsidian dev:dom selector=".workspace-leaf.mod-active" all
```

If the plugin is new to the vault, run bootstrap immediately after deploy and before the reload/log-watch pass. The job runner and cycle wrappers do this automatically unless bootstrap is skipped.

If Obsidian is closed, run the launch helper first:

```bash
node scripts/obsidian_debug_launch_app.mjs --mode cli --vault-name "<vault>" --output .obsidian-debug/app-launch.json
```

## Stale Runtime Versus Fresh Artifact

Use this when deploy verification says the new artifact is present, but `plugin:reload` leaves the visible UI on old text, old CSS, or old behavior.

Diagnosis sequence:

1. Prove deploy freshness by grepping the deployed artifact, not the repo artifact.
2. Prove runtime staleness from DOM/computed style.
3. Reload the whole vault, then recapture.
4. If still stale, disable/enable the plugin, then recapture.
5. Only after those steps fail, suspect build output, copy target, plugin id, or cache logic.

```bash
grep -n "<new-build-id-or-string>" "<vault>/.obsidian/plugins/<plugin-id>/main.js"
grep -n "<new-css-selector-or-token>" "<vault>/.obsidian/plugins/<plugin-id>/styles.css"

obsidian dev:console clear
obsidian plugin:reload id=<plugin-id>
obsidian dev:dom selector="<stable-plugin-root>" all
obsidian dev:css selector="<selector>" prop="<property>"

obsidian reload vault="<vault>"
obsidian dev:dom selector="<stable-plugin-root>" all
obsidian dev:css selector="<selector>" prop="<property>"
```

If vault reload fixes the UI while artifact grep was already fresh, report the root cause as stale Obsidian runtime state or stale plugin webview/CSS injection, not as a failed deploy. Preserve the before/after grep and DOM/CSS captures in `.obsidian-debug/`.

Disable/enable fallback:

```bash
obsidian plugin:disable id=<plugin-id>
obsidian plugin:enable id=<plugin-id>
obsidian dev:dom selector="<stable-plugin-root>" all
```

## CDP Fallback

Use direct CDP when CLI polling misses early logs, exact event ordering matters, or the user asks for real-time console capture.

```bash
node scripts/obsidian_cdp_console_watch.mjs --duration-seconds 15 --output .obsidian-debug/cdp-console-watch.log
node scripts/obsidian_cdp_reload_and_trace.mjs --plugin-id <id> --duration-seconds 20 --output .obsidian-debug/cdp-reload-trace.log
node scripts/obsidian_cdp_capture_ui.mjs --selector ".workspace-leaf.mod-active" --html-output .obsidian-debug/dom.html --screenshot-output .obsidian-debug/screenshot.png
```

On macOS, if no full Obsidian CLI is available, launch Obsidian with a debug port first:

```bash
bash scripts/obsidian_mac_restart_cdp.sh /Applications/Obsidian.app 9222
```

If your agent runtime already exposes `obsidian-devtools-mcp` or a DevTools MCP target bound to the Obsidian Electron window, you can drive that instead of the bundled CDP scripts. Keep the built-in scripts as the portable fallback.

Auto-launch can open the app, but it may not retroactively add a debug port to an already-running Obsidian instance. The launch helper now retries with one explicit restart fallback on Windows or macOS before it gives up.

Synthetic Windows smoke for the restart path:

```bash
node scripts/obsidian_debug_cdp_restart_fallback_smoke.mjs
```

This compiles a temporary fake Obsidian executable with `csc.exe`, verifies that `scripts/obsidian_debug_launch_app.mjs` records `cdpRestartFallback.attempted|ok|readyAfterRestart`, and then cleans up the synthetic process. It is meant for regression-proofing the fallback path without restarting a real Obsidian session.

Synthetic Windows smoke for stale agent/session `PATH` recovery:

```bash
node scripts/obsidian_debug_windows_cli_resolution_smoke.mjs
```

This strips the current process `PATH` of Obsidian entries, then verifies that the launch helper and doctor still recover the CLI from the Windows user/machine `Path` scopes.

## Optional Agentic Surface Probes

Use these only when needed; default loop remains CLI/CDP-first.

```bash
# Generate static AI/MCP/REST safety/control-surface evidence
node scripts/obsidian_debug_agentic_support.mjs \
  --repo-dir <repo> \
  --rest-base-url "http://127.0.0.1:<obsidian-cli-rest-port>" \
  --rest-api-key "$OBSIDIAN_CLI_REST_API_KEY" \
  --output .obsidian-debug/agentic-support.json

# Surface the same evidence as doctor checks
node scripts/obsidian_debug_doctor.mjs \
  --repo-dir <repo> \
  --plugin-id <id> \
  --agentic-rest-base-url "http://127.0.0.1:<obsidian-cli-rest-port>" \
  --agentic-rest-api-key "$OBSIDIAN_CLI_REST_API_KEY" \
  --output .obsidian-debug/doctor.json

# Probe Obsidian CLI REST health (placeholder host/key; never commit real secrets)
curl -sS "http://127.0.0.1:<obsidian-cli-rest-port>/health"
curl -sS "http://127.0.0.1:<obsidian-cli-rest-port>/tools" \
  -H "Authorization: Bearer $OBSIDIAN_CLI_REST_API_KEY"

# Probe MCP servers with Inspector (example)
npx @modelcontextprotocol/inspector

# Validate CDP target list when DevTools MCP/CDP attach is unclear
curl -sS "http://127.0.0.1:<cdp-port>/json/list"
```

Read `references/agentic-control-surfaces.md` before choosing among CLI, CDP, DevTools MCP, Playwright MCP, Vault MCP, or MCP Inspector.
Do not treat Vault MCP/Nexus-style vault servers as proof that plugin reload/log capture is available.
The doctor emits optional `agentic-control-surfaces`, `ai-plugin-secret-storage`, `ai-plugin-network-boundary`, and `mcp-rest-security` checks when these signals are available.
Regression smoke: `node scripts/obsidian_debug_agentic_security_smoke.mjs`.

Generate the backend routing manifest after doctor/diagnosis when another agent needs an explicit switchboard:

```bash
node scripts/obsidian_debug_control_backend_support.mjs \
  --doctor .obsidian-debug/doctor.json \
  --diagnosis .obsidian-debug/diagnosis.json \
  --output .obsidian-debug/control-backends.json
```

`control-backends.json` maps capabilities such as `reloadPlugin`, `captureDom`, `captureScreenshot`, `runScenario`, `locatorActions`, and `visualReview` to `obsidian-cli`, `bundled-cdp`, `obsidian-cli-rest`, `chrome-devtools-mcp`, `playwright-script`, or `playwright-mcp`. Local scripts directly execute CLI/CDP/Playwright-script backends; MCP/REST backends are routing descriptors until the current agent runtime exposes callable tools.

For the local `playwright-script` backend, resolution is module-first and CLI-second:

1. repo-local Playwright module (`playwright`, `playwright-core`, `@playwright/test`);
2. explicit `--playwright-cli-command <cmd>`;
3. `playwright-cli` on `PATH`;
4. local `npx --no-install playwright-cli`;
5. automatic bootstrap via `npm exec --yes --package=@playwright/cli@latest -- playwright-cli` unless `--playwright-no-bootstrap` is set.

On Windows, the launcher automatically uses `npm.cmd` / `npx.cmd` through `cmd.exe /c`.

## Scenario And UI Assertions

- Use `scenarios/open-plugin-view.json` when a plugin has a known open-view command or view type.
- Use `surface-profiles/plugin-surface.template.json` when the plugin surface needs discovery hints.
- Start generic assertions from `assertions/plugin-view-health.template.json` and replace placeholder selectors/text with plugin-specific expectations.
- If scenario execution fails with `ECONNREFUSED 127.0.0.1:9222`, recover CDP with `scripts/obsidian_debug_launch_app.mjs --mode cdp ...` before rerunning the scenario, or disable scenario and use `obsidian eval` assertions for a CLI-only proof.
- Use `scripts/obsidian_debug_scenario_runner.mjs --dry-run` with `surface-profiles/synthetic-plugin-surface.fixture.json` to validate strategy selection without touching Obsidian.
- Use `--control-backend obsidian-cli|bundled-cdp|playwright-script` as a backend alias for local scenario runs. DevTools MCP and Playwright MCP are external agent-native backends, so route them through the MCP client rather than this local runner.
- Use `--playwright-cli-command <cmd>` when the repo has no Playwright dependency but a known `playwright-cli` entrypoint exists.
- Use `--playwright-no-bootstrap` when the environment must not auto-install `@playwright/cli`.

If Playwright setup fails, the scenario runner still writes `scenario-report.json` and exits `1`, so automation can inspect a structured error instead of parsing a raw stack trace.

For stateful UI behavior, write a small `.obsidian-debug/<case>.js` file and run:

```bash
node scripts/obsidian_eval_file.mjs \
  --vault-name "<vault>" \
  --file .obsidian-debug/<case>.js \
  --clear-before \
  --capture-after \
  --output .obsidian-debug/<case>-result.json
```

Important: `obsidian eval` does not support `file=<path>`. It only accepts inline `code=<javascript>`. Always use `scripts/obsidian_eval_file.mjs` for JS files so the wrapper reads the file and passes it as `code=...` without shell-quoting failures.

Have the script open the plugin surface, interact with the real DOM, throw on failure or return JSON with `ok: false`, and restore any settings it mutates. `obsidian_eval_file.mjs` captures the raw eval output, parses a final `=> {...}` JSON result when present, and exits non-zero when that JSON says `ok: false`. With `--clear-before`, it runs `dev:console clear` and `dev:errors clear` before the eval. With `--capture-after`, it stores final `dev:console limit=<n>` and `dev:errors` output under `captures` in the result JSON; use `--capture-limit <n>` to change the console limit. Prefer this for composer input, autocomplete menus, settings toggles, and cached runtime catalogs where screenshots or static DOM text cannot prove the behavior.

Treat stdout from reload, settings restore, and service restart steps as phase evidence, not automatically as final failure. The wrapper separates `phases` (clear/setup), eval `stdout`, and `captures`. Judge final residue from `captures.errors.stdout` and `captures.console.stdout` after cleanup/restore completes, while still preserving transient phase stdout for diagnosis.

When `--capture-after` is present, use the final `captures` object as the residual health signal. Console lines from service restarts, restore hooks, or intermediate reloads in `stdout` prove the path ran, but they are not final residue unless they also appear in the post-run captures.

Stateful assertion cleanup contract:

```js
(async function assertSettingsSurface() {
  const plugin = app.plugins.plugins["<plugin-id>"];
  const snapshot = structuredClone(plugin.settings ?? plugin.data ?? {});
  const result = { ok: false, restored: false, checks: [] };

  try {
    // Open the real surface, click real controls, and assert durable UI state.
    // Push small check records into result.checks as each assertion passes.
    result.ok = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
    result.ok = false;
  } finally {
    try {
      plugin.settings = structuredClone(snapshot);
      if (typeof plugin.saveSettings === "function") {
        await plugin.saveSettings();
      } else if (typeof plugin.saveData === "function") {
        await plugin.saveData(snapshot);
      }
      result.restored = true;
    } catch (restoreError) {
      result.restored = false;
      result.restoreError = restoreError instanceof Error ? restoreError.message : String(restoreError);
    }
    result.ok = result.ok && result.restored;
    console.log(`=> ${JSON.stringify(result)}`);
  }
})();
```

For tabbed or multi-level settings surfaces, use this reusable shape:

1. Locate the owner-level settings container first, not just an inner panel.
2. Click the primary tab, then wait for an active-tab marker plus a durable content-shell selector.
3. Click the secondary tab only after the primary owner is mounted.
4. Trigger refresh/load buttons only after the intended tab is active.
5. Assert the final control state and any captured service result.
6. Restore settings/config in `finally` and return `{ "ok": true, "restored": true, "checks": [...] }`.

If the assertion becomes useful across repeated work on one plugin, promote it from `.obsidian-debug/` into `projects/<project>/scripts/` or the target repo's debug folder. Project-profile scripts are reusable, but they must still be loaded by explicit path after confirming the target plugin matches that profile.

Example for an OpenCodian run after confirming the target plugin id is `opencodian`:

```bash
node scripts/obsidian_eval_file.mjs \
  --vault-name "<vault>" \
  --file projects/opencodian/scripts/agent-mention-layout-assertion.js \
  --output .obsidian-debug/agent-mention-layout-result.json
```

### Runtime Locale And I18n Assertions

Do not prove locale-sensitive UI by assigning `plugin.settings.locale` alone. Many plugins normalize locale through an i18n service, cached translator, settings coordinator, or render-time store.

Preferred assertion order:

1. Snapshot current settings and runtime locale fields.
2. Change locale through the real settings UI when feasible.
3. If using JS, save settings through the plugin's own API and then reload plugin or vault.
4. Assert both runtime translation state and rendered UI text.
5. Restore settings in `finally`, then use `--capture-after` to judge final console/errors.

Minimal JS shape:

```js
(async function assertLocaleRuntime() {
  const plugin = app.plugins.plugins["<plugin-id>"];
  const snapshot = structuredClone(plugin.settings ?? {});
  const result = { ok: false, restored: false, checks: [] };

  try {
    plugin.settings.locale = "en";
    if (typeof plugin.saveSettings === "function") await plugin.saveSettings();
    if (app.plugins.disablePlugin && app.plugins.enablePlugin) {
      await app.plugins.disablePlugin("<plugin-id>");
      await app.plugins.enablePlugin("<plugin-id>");
    }

    const activePlugin = app.plugins.plugins["<plugin-id>"] ?? plugin;
    const runtimeLocale =
      activePlugin.i18n?.getLocale?.() ??
      activePlugin.locale?.getCurrent?.() ??
      activePlugin.settings?.locale;
    result.checks.push({ name: "runtime-locale", value: runtimeLocale });

    const text = document.body.innerText;
    result.checks.push({ name: "rendered-text", matched: text.includes("<expected-en-text>") });
    result.ok = runtimeLocale === "en" && text.includes("<expected-en-text>");
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  } finally {
    try {
      const activePlugin = app.plugins.plugins["<plugin-id>"] ?? plugin;
      activePlugin.settings = structuredClone(snapshot);
      if (typeof activePlugin.saveSettings === "function") await activePlugin.saveSettings();
      result.restored = true;
    } catch (restoreError) {
      result.restoreError = restoreError instanceof Error ? restoreError.message : String(restoreError);
    }
    result.ok = result.ok && result.restored;
    console.log(`=> ${JSON.stringify(result)}`);
  }
})();
```

If plugin reload still leaves old strings and artifact grep is fresh, run the stale-runtime flow above before changing i18n code.

### CSS Regression Assertions With Synthetic Fixtures

For visual states that are pure CSS, avoid depending on real plugin data, remote directories, server readiness, or async catalog hydration. Inject or open a stable fixture element, apply the expected classes/attributes, and assert computed style.

```js
(async function assertCssState() {
  const result = { ok: false, checks: [] };
  const host = document.createElement("div");
  host.className = "<plugin-root-class>";
  host.innerHTML = `<button class="<target-class>" data-state="active">Fixture</button>`;
  document.body.appendChild(host);

  try {
    const node = host.querySelector(".<target-class>");
    const style = getComputedStyle(node);
    result.checks.push({ name: "background", value: style.backgroundColor });
    result.checks.push({ name: "color", value: style.color });
    result.ok = style.backgroundColor === "<expected-rgb>" && style.color === "<expected-rgb>";
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
    result.ok = false;
  } finally {
    host.remove();
    console.log(`=> ${JSON.stringify(result)}`);
  }
})();
```

Use a real-surface assertion when CSS depends on layout context, theme variables, or Obsidian workspace ancestry. Even then, assert computed style first and use screenshots as review evidence, not the only proof.

## Analysis And Reports

Cycle wrappers write `summary.json` and then call the analyzer. For custom pipelines:

```bash
node scripts/obsidian_debug_analyze.mjs --summary .obsidian-debug/summary.json --assertions assertions/plugin-view-health.template.json --output .obsidian-debug/diagnosis.json
node scripts/obsidian_debug_compare.mjs --baseline <old-diagnosis.json> --candidate .obsidian-debug/diagnosis.json --output .obsidian-debug/comparison.json
node scripts/obsidian_debug_visual_review.mjs --diagnosis .obsidian-debug/diagnosis.json --comparison .obsidian-debug/comparison.json --output .obsidian-debug/visual-review.json --html-output .obsidian-debug/visual-review.html
node scripts/obsidian_debug_report.mjs --diagnosis .obsidian-debug/diagnosis.json --comparison .obsidian-debug/comparison.json --output .obsidian-debug/report.html
```

Read `diagnosis.json` before raw logs. It summarizes artifact presence, assertion failures, timing metrics, known issue signatures, and next-step recommendations.
Use `visual-review.html` for screenshot-based human review of blank panes, clipping, visible errors, contrast, and obvious layout regressions. It cannot replace reliable manual GUI validation for hover/focus/drag behavior, timing-sensitive animations, or official review acceptance.
When `Logstravaganza` is available, the cycle wrappers also emit `vault-log-capture.json`; the diagnosis/report layer merges those NDJSON events with CLI/CDP evidence while keeping source paths and line numbers visible.

## After-Action Improvement Triage

After each real run, classify any reusable lesson before the final response:

| Class | Put it here | Examples |
| --- | --- | --- |
| Generic autodebug workflow/tooling | This skill | wrapper scripts, CDP fallback guidance, generic assertion behavior, stale documentation fixes |
| Reusable target-plugin assets | `projects/<project>/` in this skill, or the target plugin repo | plugin commands, root selectors, project assertions, stateful behavior scripts, domain-specific log signatures/playbooks |
| Target plugin notes | Target plugin repo | architecture context, ownership notes, project docs, local debug conventions |
| One-run machine state | Run report only | temporary CDP restart, dirty vault state, transient app focus, local-only path quirks |

If this skill changes, validate it:

```bash
python3 /Users/dht/.codex/skills/.system/skill-creator/scripts/quick_validate.py <path-to-obsidian-plugin-autodebug>
```

Do not add plugin-named assertions, business-domain signatures, or project DOM selectors to this skill’s bundled defaults. Store those in `projects/<project>/` or the target project that produced them and reference them with `--assertions`, `--signatures`, or `--playbooks`.

Default `rules/issue-signatures.json` and `rules/issue-playbooks.json` are plugin-neutral. If a target plugin needs domain-specific signatures, keep them in that plugin repo or in a matching project profile, then pass them explicitly:

```bash
node scripts/obsidian_debug_analyze.mjs \
  --summary .obsidian-debug/summary.json \
  --signatures projects/<project>/rules/issue-signatures.json \
  --playbooks projects/<project>/rules/issue-playbooks.json \
  --output .obsidian-debug/diagnosis.json
```

## Agent Handoff Manifest

Use `agent-tools.json` for model-to-model continuation. Keep commands secret-free and path-only.

```bash
# Standalone generation
node scripts/obsidian_debug_agent_tools.mjs \
  --summary .obsidian-debug/summary.json \
  --diagnosis .obsidian-debug/diagnosis.json \
  --doctor .obsidian-debug/doctor.json \
  --output .obsidian-debug/agent-tools.json
```

Expected usage:

- Produce `agent-tools.json` after diagnosis/report generation.
- Hand off `safeActions`, `controlSurfaces`, `controlBackends`, `evidence`, and `warnings` to the next agent.
- Never include API keys, bearer tokens, or machine-local secret values in the manifest.

## State, Watch, Profile, And Baseline

| Need | Script | Notes |
| --- | --- | --- |
| Snapshot/restore vault files | `scripts/obsidian_debug_vault_state.mjs` | Use before experiments that mutate vault/plugin files. |
| Preview/reset plugin-local state | `scripts/obsidian_debug_reset_state.mjs` | Start with `--mode preview`; reset preserves a snapshot. |
| Compare clean vs restored state | `scripts/obsidian_debug_state_matrix.mjs` | Runs the same job against reset and restored state. |
| Watch-on-save loop | `scripts/obsidian_debug_watch.mjs` | Command template supports `{{outputDir}}` and `{{run}}`; if the vault intentionally uses `mobile-hot-reload`, treat it as cross-device watch context instead of deterministic timing mode. |
| Repeated timing profile | `scripts/obsidian_debug_profile.mjs` | Use multiple runs to separate variance from regression. |
| Save/list/compare/prune baselines | `scripts/obsidian_debug_baseline.mjs` | Tag baselines by plugin, platform, mode, and scenario. |

Start plugin-local reset plans from `state-plans/plugin-data-reset.json`, then copy the plan into the target project before adding project-specific files.

## Fixtures And Evals

- `fixtures/native-smoke-sample-plugin/`: plugin-neutral host smoke fixture.
- `fixtures/package-manager-smoke-pnpm-plugin/`: package-manager/Corepack smoke fixture.
- `fixtures/preflight-smoke-plugin/`: optional lint and plugin-entry preflight fixture that intentionally fails on manifest/template residue before build.
- `fixtures/testing-framework-smoke-plugin/`: optional `obsidian-testing-framework` fixture with a repo-owned adapter config and CI dry-run job sample.
- `fixtures/obsidian-e2e-smoke-plugin/`: optional Vitest-style `obsidian-e2e` fixture with a repo-owned adapter config and CI dry-run job sample.
- `fixtures/wdio-obsidian-service-smoke-plugin/`: optional WebdriverIO-style `wdio-obsidian-service` fixture with a repo-owned adapter config and CI dry-run job sample.
- `evals/evals.json`: behavior prompts for checking skill coverage after edits.

## Optional Ecosystem Tools

- `obsidian-dev-utils`: when the repo already uses it, prefer its repo-owned `dev` / `build` / `lint` / `test` scripts over rebuilding a parallel local loop.
- `eslint-plugin-obsidianmd`: wire it through a repo-owned lint script before build when the repo wants official manifest/template validation.
- `Logstravaganza`: if the target vault enables it, collect its NDJSON log files as persistent secondary evidence in addition to CLI/CDP output; doctor can surface discovered files up front and reports show merged provenance explicitly.
- `obsidian-e2e`, `obsidian-testing-framework`, and `wdio-obsidian-service`: optional CI/headless adapters that should stay repo-owned rather than hard-coded by the skill.
- `generator-obsidian-plugin`: prefer this when the user needs a production-ready plugin project scaffold instead of a minimal debug fixture.
- `semantic-release-obsidian-plugin`: release automation belongs in release-management flows, not the default local debug loop.

For from-zero project selection, read `references/plugin-development-tooling.md` before recommending a scaffold or installing optional frameworks.

## CI And Headless Quality Gates

Generate CI templates only after a local desktop smoke run passes:

```bash
node scripts/obsidian_debug_ci_templates.mjs --repo-dir <repo> --job <repo>/.obsidian-debug/job.json --output-dir <repo>/autodebug/ci --output <repo>/.obsidian-debug/ci-templates.json
```

Keep the split explicit:

- CI-suitable: install, repo-owned lint and optional plugin-entry validation preflight commands before build, build/test commands, optional `obsidian-e2e`, `obsidian-testing-framework`, or `wdio-obsidian-service` repo scripts, and job dry-runs.
- Local-only: fresh-vault bootstrap, desktop Obsidian reload, CLI/CDP console capture, screenshots, DOM snapshots, Playwright traces.

## Troubleshooting

- `obsidian help` cannot find Obsidian: run `node scripts/obsidian_debug_launch_app.mjs --mode cli ...`, then retry.
- Artifact grep is fresh but UI text/CSS is old after `plugin:reload`: run `obsidian reload vault="<vault>"`, recapture DOM/CSS, then disable/enable before editing plugin code.
- Locale string assertions fail after changing `plugin.settings.locale`: assert the runtime translator state, save via the plugin API, and reload plugin or vault; prefer the real settings UI when the plugin wires locale through UI coordinators.
- CSS visual assertions hang on missing business data: inject a synthetic fixture and assert `getComputedStyle`, then reserve screenshots for human review.
- Windows note: the Node helpers now merge the current process `PATH` with the Windows user/machine `Path` scopes before probing `obsidian`, so stale long-lived agent sessions no longer misclassify the CLI just because they inherited an old `PATH`.
- CDP fetch fails: let `scripts/obsidian_debug_launch_app.mjs --mode cdp ...` perform its restart fallback, or run `scripts/obsidian_windows_restart_cdp.ps1` / `scripts/obsidian_mac_restart_cdp.sh` directly and then probe `http://127.0.0.1:9222/json/list`.
- Logs show Hot Reload churn: use controlled mode for deterministic timing or coexist mode when intentionally letting Hot Reload drive reload.
- UI selectors are flaky: add a surface profile, then assert stable root selectors/text instead of screenshot-only evidence.
- Screenshot review is still incomplete: generate `visual-review.html`, inspect it manually, then back critical findings with DOM/text/log assertions.
