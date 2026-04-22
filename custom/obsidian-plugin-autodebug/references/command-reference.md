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
- Use `scripts/obsidian_debug_scenario_runner.mjs --dry-run` with `surface-profiles/synthetic-plugin-surface.fixture.json` to validate strategy selection without touching Obsidian.
- Use `--control-backend obsidian-cli|bundled-cdp|playwright-script` as a backend alias for local scenario runs. DevTools MCP and Playwright MCP are external agent-native backends, so route them through the MCP client rather than this local runner.
- Use `--playwright-cli-command <cmd>` when the repo has no Playwright dependency but a known `playwright-cli` entrypoint exists.
- Use `--playwright-no-bootstrap` when the environment must not auto-install `@playwright/cli`.

If Playwright setup fails, the scenario runner still writes `scenario-report.json` and exits `1`, so automation can inspect a structured error instead of parsing a raw stack trace.

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

Default `rules/issue-signatures.json` and `rules/issue-playbooks.json` are plugin-neutral. If a target plugin needs domain-specific signatures, keep them in that plugin repo or pass them explicitly:

```bash
node scripts/obsidian_debug_analyze.mjs \
  --summary .obsidian-debug/summary.json \
  --signatures path/to/project-issue-signatures.json \
  --playbooks path/to/project-issue-playbooks.json \
  --output .obsidian-debug/diagnosis.json
```

The bundled `rules/opencodian-issue-signatures.json` and `rules/opencodian-issue-playbooks.json` are examples for OpenCodian/OpenCode-style projects only; they are not generic Obsidian plugin defaults.

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
- Windows note: the Node helpers now merge the current process `PATH` with the Windows user/machine `Path` scopes before probing `obsidian`, so stale long-lived agent sessions no longer misclassify the CLI just because they inherited an old `PATH`.
- CDP fetch fails: let `scripts/obsidian_debug_launch_app.mjs --mode cdp ...` perform its restart fallback, or run `scripts/obsidian_windows_restart_cdp.ps1` / `scripts/obsidian_mac_restart_cdp.sh` directly and then probe `http://127.0.0.1:9222/json/list`.
- Logs show Hot Reload churn: use controlled mode for deterministic timing or coexist mode when intentionally letting Hot Reload drive reload.
- UI selectors are flaky: add a surface profile, then assert stable root selectors/text instead of screenshot-only evidence.
- Screenshot review is still incomplete: generate `visual-review.html`, inspect it manually, then back critical findings with DOM/text/log assertions.
