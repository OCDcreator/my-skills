---
name: obsidian-plugin-autodebug
description: Use when developing or debugging Obsidian community plugins end-to-end: build/deploy/reload loops, fresh test vault bootstrap, Obsidian CLI/CDP console capture, screenshots, DOM assertions, startup profiling, watch-on-save, plugin state reset, CI quality gates, or sample plugin scaffolding.
---

# Obsidian Plugin Autodebug

Use this skill to turn Obsidian plugin development into a repeatable debug loop: prepare the app-control surface, build, deploy to a test vault, bootstrap fresh-vault discovery, reload, capture logs/UI artifacts, analyze diagnosis output, patch, and repeat.

Keep the loaded skill focused on decisions and workflow. For script flags and copy-ready commands, read `references/command-reference.md` or run any runnable `.mjs` helper with `--help`.

## When To Use

Use this skill when the user asks for:

- full Obsidian plugin smoke/debug cycles: build, deploy, reload, capture, diagnose;
- fresh clean-vault or first-install bootstrap problems;
- dev console, startup logs, CDP traces, screenshots, DOM/CSS inspection, or UI assertions;
- slow startup, slow view-open, hydration, server warmup, or timing regression analysis;
- watch-on-save automation, state reset, baseline comparison, profiling, or HTML reports;
- CI/headless quality-gate templates that stay separate from desktop-only checks;
- a minimal sample plugin workspace when no real plugin repo exists yet.

Do not use it for normal note/vault operations. Use `obsidian-cli` directly for reading notes, creating files, searching vault content, or simple one-shot vault management.

## App-Control Reality Check

The Obsidian CLI controls an already-running Obsidian desktop instance. It is not a headless runner and should not be treated as proof that Obsidian has launched.

Before any real reload, console, screenshot, DOM, or plugin command:

- launch Obsidian desktop;
- open or focus the target test vault;
- run `obsidian help`;
- confirm the help output includes `Developer:` commands.

If `obsidian help`, `obsidian dev:console`, or any plugin command says it cannot find Obsidian, first launch/focus Obsidian and retry. Treat that error as a missing desktop/app-control precondition, not as a plugin build failure.

On macOS, the app binary is not a full CLI replacement. If the full CLI is unavailable, start Obsidian with a CDP debug port and use the CDP-first path.

## Relationship To `obsidian-cli`

The `obsidian-cli` skill provides primitive app-control commands such as:

- `obsidian plugin:reload id=<plugin-id>`
- `obsidian dev:console limit=200`
- `obsidian dev:errors`
- `obsidian dev:screenshot path=<file>`
- `obsidian dev:dom selector=<css> all`
- `obsidian dev:css selector=<css> prop=<name>`
- `obsidian eval code="<javascript>"`

This skill is the higher-level workflow wrapper. Prefer CLI-first automation when the CLI preflight works. Use CDP only when CLI buffers miss timing-critical logs, real-time ordering matters, or the CLI surface is unavailable but a debug port is reachable.

In this source repo, the mirrored skill lives at `external/kepano-obsidian-skills/obsidian-cli/SKILL.md`. In an installed agent environment, load the skill named `obsidian-cli` when it is available; do not confuse that skill with the Obsidian desktop application's `obsidian` executable.

## Preconditions

Before editing or running a long loop, quickly detect:

- Obsidian desktop is running with the target vault open or recently focused.
- `obsidian help` works and includes `Developer:` commands, or a CDP port is reachable.
- The repo is an Obsidian plugin: `manifest.json`, `package.json`, and generated `dist/main.js` or equivalent output.
- The plugin id from `manifest.json`.
- The test vault plugin directory, usually `<vault>/.obsidian/plugins/<plugin-id>/`.
- The repo’s own build, deploy, and validation instructions. Repo-local `AGENTS.md` instructions override this generic workflow.

If the repo already has a release/deploy script or skill, reuse it instead of inventing a parallel deployment path.

## Choose The Flow

| Situation | Preferred path |
| --- | --- |
| Existing plugin repo | Copy `job-specs/generic-debug-job.template.json`, tailor runtime/build/deploy values, run doctor, dry-run, then execute. |
| No plugin repo yet | If you need a real production-ready plugin repo, start from `generator-obsidian-plugin`. Use `scripts/obsidian_debug_scaffold_plugin.mjs` only when you want a minimal debug fixture, test vault, job spec, assertions, scenario, and CI templates. |
| CLI developer commands work | Use CLI-first reload/log/screenshot/DOM capture. |
| CLI cannot see Obsidian but app can expose CDP | Start Obsidian with a debug port and use CDP capture/reload scripts. |
| One-off local pass | Use `scripts/obsidian_plugin_debug_cycle.ps1` or `scripts/obsidian_plugin_debug_cycle.sh`. |
| Repeatable agent/CI-like plan | Use `scripts/obsidian_debug_job.mjs` with a job spec. |

For exact commands, read `references/command-reference.md`.

## Default Debug Loop

1. **Preflight**: run the doctor to catch missing Node/WebSocket support, bad plugin ids, missing build outputs, unavailable CLI developer commands, CDP reachability, Hot Reload interference, package-manager signals, fresh-vault discovery gaps, and optional ecosystem adapters such as official lint rules, repo-owned E2E scripts, and vault logging helpers when they are detectable.
2. **Build**: prefer the repo’s documented command. Respect package-manager signals such as `packageManager`, lockfiles, Corepack, and repo-owned scripts. If the repo already routes build/dev through `obsidian-dev-utils`, prefer those repo-owned scripts over reconstructing a parallel copy/reload loop.
3. **Deploy**: copy only generated runtime artifacts into the test vault plugin directory: `main.js`, `manifest.json`, `styles.css`, and changed bundled assets.
4. **Bootstrap**: for a brand-new plugin in a fresh vault, bootstrap discovery immediately after deploy and before the real reload/log-watch pass.
5. **Reload**: use `obsidian plugin:reload id=<plugin-id>` first. Fall back to disable/enable or CDP only when reload is unavailable or stuck.
6. **Capture**: clear stale buffers, watch console/errors, capture screenshot and DOM/CSS evidence, and run any configured scenario. If the target vault intentionally enables `Logstravaganza`, treat its NDJSON files as a persistent secondary log source alongside CLI/CDP capture and preserve the discovered source metadata in the generated `vault-log-capture.json`.
7. **Generate diagnosis**: wrappers and `scripts/obsidian_debug_job.mjs` write `diagnosis.json` automatically; for a manual path, run `scripts/obsidian_debug_analyze.mjs --summary .obsidian-debug/summary.json --assertions assertions/plugin-view-health.template.json --output .obsidian-debug/diagnosis.json`.
8. **Analyze**: inspect `diagnosis.json` before raw logs. It aggregates assertions, timings, known issue signatures, and next-step recommendations.
9. **Patch and repeat**: make the smallest root-cause fix, rebuild/deploy/reload, then compare against the previous diagnosis or saved baseline.

Save runtime artifacts under `.obsidian-debug/` or another repo-local debug folder. Do not commit raw runtime logs unless the user asks.

## Job Specs

Use config-driven jobs for repeatability across Windows PowerShell and macOS/Linux Bash. A job spec can describe:

- `runtime`: plugin id, test vault plugin directory, cwd, Obsidian command, vault name, output directory;
- `build` / `deploy` / `bootstrap` / `reload` / `logWatch`: build argv, deploy source, fresh-vault bootstrap policy, CLI/CDP reload, Hot Reload coordination, polling;
- `scenario` / `assertions` / `comparison`: view-opening scenario, surface profile, assertion JSON, DOM selector, baseline comparison;
- `profile` / `report`: repeated-cycle timing and optional HTML report generation;
- `state`: optional vault snapshot, plugin-local reset preview/reset, and restore-after-run handling.

For an existing plugin, keep absolute machine paths in the copied repo-local job file, not in shared templates. For a scaffolded sample plugin, use the generated `autodebug/<plugin-id>-debug-job.json`; scaffold-owned reusable config lives under `autodebug/`, while runtime captures still go under `.obsidian-debug/`.

## UI Surface And Assertions

Use DOM checks for deterministic assertions and screenshots for visual review. Good generic assertions include:

- plugin view/root selector exists and is visible;
- expected heading, status, button, or settings text is present;
- error banners are absent;
- key attributes or computed styles are correct;
- startup or view-open timings stay within budget.

Start from `assertions/plugin-view-health.template.json`. Use `surface-profiles/plugin-surface.template.json` when the plugin does not have one obvious command id or root selector.

Use `scenarios/open-plugin-view.json` for generic view-opening smoke checks. Use `scenarios/playwright-locator-health.template.json` only when Playwright is explicitly available and the plugin needs click/locator assertions.

The scenario runner resolves surface-opening strategies in this order:

1. declared surface profile metadata;
2. known Obsidian command ids or view types;
3. CDP DOM heuristics.

`scenario-report.json` records the selected strategy plus discovered root selectors, headings, settings surfaces, error banners, and empty states.

## Performance Debugging Pattern

When the user reports “startup is slow” or “first open is slow,” split the timeline instead of guessing:

1. plugin `onload` / startup total;
2. deferred runtime warmup such as local server start;
3. view open / tab restore;
4. conversation/message hydration;
5. post-render UI tail;
6. background refreshes.

Add timing logs around each suspected phase. For Obsidian plugin UI, `onload` can be fast while the visible sidebar is slow because view hydration waits for a server-dependent request.

Safe fix pattern:

- keep identity/state shell writes synchronous;
- move slow server snapshots or non-critical enrichments to background refreshes;
- guard stale async writes before mutating UI state;
- log background completion separately;
- verify visible `view-open` timing improves while background work still completes.

For deeper breakpoint/flame-chart workflows, pair this pattern with the `obsidian-typings` code-debugging guide as a reference companion.

## State, Watch, Profile, And Baseline

Use state helpers when bugs depend on dirty vault/plugin data:

- preview reset targets before deleting anything;
- snapshot plugin-local files before reset;
- restore snapshots after experiments;
- compare clean-state and restored-state runs with the same job spec.

Start from `state-plans/plugin-data-reset.json` for conservative plugin-local resets, then copy it into the target project before adding project-specific files.

Use watch mode for “save → build → deploy → reload → diagnose” loops. Use profile mode when one run is too noisy to trust. Save baselines by plugin/platform/mode/scenario so later comparisons use the nearest matching class.

## Optional Ecosystem Integrations

When the surrounding repo or target vault already uses these tools, integrate with them instead of fighting them:

- `obsidian-dev-utils`: prefer repo-owned `dev` / `build` / `lint` / `test` scripts that already route through it.
- `eslint-plugin-obsidianmd`: run it through a repo-owned lint script before build when the repo wants official Obsidian manifest/template checks.
- `Logstravaganza`: use it as persistent secondary console/error evidence, especially for mobile or user-supplied repro logs; doctor/capture/report now preserve NDJSON source metadata so merged evidence stays attributable.
- `obsidian-e2e`, `obsidian-testing-framework`, and `wdio-obsidian-service`: keep them optional; doctor and CI templates should surface them only when the repo already owns matching scripts or dependencies.
- `mobile-hot-reload`: treat it as intentional cross-device watch context because it can influence reload timing and log ordering.
- `generator-obsidian-plugin`: recommend it when the user wants a real plugin project scaffold rather than a minimal debug fixture.
- `semantic-release-obsidian-plugin`: release automation belongs in `obsidian-plugin-release-manager`, not the default autodebug loop.

## CDP Fallback

Use CDP when:

- CLI logs miss early startup messages;
- the user asks for real-time console capture;
- exact reload/log ordering matters;
- JavaScript must run repeatedly during startup;
- macOS lacks the full CLI but the app can be launched with a debug port.

Before CDP work, probe the target list and attach to the `app://obsidian.md/index.html` target. In multi-window setups, filter by vault title.

If the agent runtime already exposes `obsidian-devtools-mcp` or another DevTools MCP surface attached to the Obsidian Electron target, that can replace the bundled CDP scripts as an alternate control surface. This is an optional path; keep the built-in scripts as the portable fallback.

## CI, Optional E2E, And Release-Adjacent Checks

After a local desktop smoke run passes, generate headless quality-gate templates. Keep this split explicit:

- **CI-suitable**: repo-owned install/lint/build/test commands, optional plugin-entry validation scripts, optional `obsidian-e2e`, `obsidian-testing-framework`, or `wdio-obsidian-service` package scripts, and `obsidian_debug_job.mjs --dry-run` plans.
- **Local-only**: fresh-vault bootstrap, real Obsidian reloads, CLI/CDP console capture, screenshots, DOM snapshots, and Playwright traces.

The doctor reports whether official lint rules, `obsidian-e2e`, `obsidian-testing-framework`, `wdio-obsidian-service`, and plugin-entry validation scripts are installed, declared, absent, or already wired into repo-owned scripts. `wdio-obsidian-service` is the main optional path that can promote real plugin E2E into CI instead of keeping it desktop-only.

## Diagnosis Workflow

Read `diagnosis.json` before raw logs. Use it to answer:

1. Did required artifacts exist?
2. Was startup slow, view-open slow, or was visible delay mostly server readiness?
3. Did known issue signatures match?
4. Which recommendation is the best next edit or instrumentation pass?

Default signatures in `rules/issue-signatures.json` must stay generic to Obsidian plugin debugging. A target plugin may need its own tests, assertions, signatures, or playbooks, but those are project-local configuration: copy them into that plugin repo or pass them explicitly with `--signatures` / `--playbooks`. Do not promote one plugin's business-domain logs into the skill's default rules.

`rules/opencodian-issue-signatures.json` and `rules/opencodian-issue-playbooks.json` are optional examples for an OpenCodian/OpenCode-style plugin only. Load them only for projects that intentionally emit those logs and metrics.

If diagnosis is inconclusive, inspect raw console/CDP logs and consider adding a generic signature to `rules/issue-signatures.json` so the next run catches that symptom automatically.

## Bundled Smoke And Eval Resources

- `fixtures/native-smoke-sample-plugin/`: plugin-neutral load/reload smoke fixture.
- `fixtures/package-manager-smoke-pnpm-plugin/`: package-manager detection fixture.
- `fixtures/preflight-smoke-plugin/`: lint and plugin-entry preflight fixture with intentional manifest/template residue failures.
- `fixtures/testing-framework-smoke-plugin/`: optional `obsidian-testing-framework` fixture with a repo-owned adapter config and CI dry-run job sample.
- `fixtures/obsidian-e2e-smoke-plugin/`: optional Vitest-style `obsidian-e2e` fixture with repo-owned adapter config and CI dry-run job sample.
- `fixtures/wdio-obsidian-service-smoke-plugin/`: optional WebdriverIO-style `wdio-obsidian-service` fixture with repo-owned adapter config and CI dry-run job sample.
- `evals/evals.json`: behavior prompts for evaluating whether the skill still covers common autodebug workflows.

## Final Report Format

When handing back results, include:

- branch/build identity and whether it was deployed to the test vault;
- exact commands run;
- validation results;
- key before/after timings;
- log/screenshot/DOM/report artifact paths;
- root cause and code path;
- remaining background long-tail work, if any;
- whether changes were committed.

Summarize important log lines with artifact paths and line numbers. Do not paste raw logs unless the user asks.

## Common Mistakes

- Treating `obsidian` command availability as proof that Obsidian desktop is running.
- Debugging plugin code when the real failure is “CLI cannot find Obsidian.”
- Reloading before deploy/bootstrap finishes.
- Committing machine-local vault paths or raw runtime logs.
- Using screenshots as the only assertion when stable DOM/text checks are available.
- Mixing cold-start and warm-start timings in the same baseline class.
- Putting desktop-only Obsidian phases into CI instead of local smoke workflows.
