# Agent Quickstart

Use this page first when another agent needs to debug or develop an Obsidian plugin with this skill. For full details, read `SKILL.md` and `references/command-reference.md`.

## 0. Boundary

- This framework automates build/deploy/reload/log/screenshot/DOM/scenario evidence when Obsidian desktop or a valid control backend is available.
- Screenshot review helps human/agent inspection, but it does **not** fully replace reliable manual GUI validation.
- MCP/REST/DevTools/Playwright backends are optional. Treat them as routed control surfaces only after target, auth, localhost, and tool allowlist checks pass.

## 1. Identify The Target

```bash
cd <plugin-repo>
cat manifest.json
cat package.json
```

Find:

- plugin id from `manifest.json`;
- repo build command;
- test vault plugin dir: `<vault>/.obsidian/plugins/<plugin-id>/`;
- Obsidian CLI command or CDP endpoint;
- whether this is a real project scaffold or only a minimal debug fixture.

For from-zero production plugin work, read `references/plugin-development-tooling.md` before scaffolding. Prefer `generator-obsidian-plugin` or the official sample plugin for real projects; use `scripts/obsidian_debug_scaffold_plugin.mjs` only for minimal autodebug fixtures.

## 2. Doctor First

Run from the skill directory, pointing at the target repo:

```bash
node scripts/obsidian_debug_doctor.mjs \
  --repo-dir <plugin-repo> \
  --plugin-id <plugin-id> \
  --test-vault-plugin-dir <vault>/.obsidian/plugins/<plugin-id> \
  --output <plugin-repo>/.obsidian-debug/doctor.json \
  --fix
```

If Obsidian is closed or the wrong vault is focused, use:

```bash
node scripts/obsidian_debug_launch_app.mjs --mode auto --vault-name "<vault>" --output <plugin-repo>/.obsidian-debug/app-launch.json
```

## 3. Choose Backend

```bash
node scripts/obsidian_debug_control_backend_support.mjs \
  --doctor <plugin-repo>/.obsidian-debug/doctor.json \
  --output <plugin-repo>/.obsidian-debug/control-backends.json
```

Default order:

1. `obsidian-cli` for reload, logs, screenshot, DOM.
2. `bundled-cdp` when CLI misses early logs or cannot see Obsidian.
3. `playwright-script` for repo-owned locator/assertion flows.
4. `obsidian-cli-rest`, `chrome-devtools-mcp`, or `playwright-mcp` only when the current agent runtime exposes safe callable tools.

## 4. Run The Loop

Prefer a copied job spec for repeatable work:

```bash
node scripts/obsidian_debug_job.mjs --job <plugin-repo>/.obsidian-debug/job.json --platform auto --dry-run
node scripts/obsidian_debug_job.mjs --job <plugin-repo>/.obsidian-debug/job.json --platform auto --mode run
```

For one-off local runs, use:

```bash
powershell -File scripts/obsidian_plugin_debug_cycle.ps1 -PluginId <plugin-id> -TestVaultPluginDir <vault>/.obsidian/plugins/<plugin-id>
bash scripts/obsidian_plugin_debug_cycle.sh --plugin-id <plugin-id> --test-vault-plugin-dir <vault>/.obsidian/plugins/<plugin-id>
```

## 5. Analyze Evidence

```bash
node scripts/obsidian_debug_analyze.mjs \
  --summary <plugin-repo>/.obsidian-debug/summary.json \
  --assertions assertions/plugin-view-health.template.json \
  --doctor <plugin-repo>/.obsidian-debug/doctor.json \
  --agent-tools-output <plugin-repo>/.obsidian-debug/agent-tools.json \
  --output <plugin-repo>/.obsidian-debug/diagnosis.json

node scripts/obsidian_debug_visual_review.mjs \
  --diagnosis <plugin-repo>/.obsidian-debug/diagnosis.json \
  --output <plugin-repo>/.obsidian-debug/visual-review.json \
  --html-output <plugin-repo>/.obsidian-debug/visual-review.html

node scripts/obsidian_debug_report.mjs \
  --diagnosis <plugin-repo>/.obsidian-debug/diagnosis.json \
  --agent-tools <plugin-repo>/.obsidian-debug/agent-tools.json \
  --output <plugin-repo>/.obsidian-debug/report.html
```

Read in this order:

1. `diagnosis.json` for pass/fail assertions and recommendations.
2. `agent-tools.json` for safe next actions, control surfaces, control backends, and evidence paths.
3. `visual-review.html` for screenshot-based human review.
4. Raw console/CDP/Logstravaganza files only when diagnosis is inconclusive.

## 6. Patch Discipline

- Fix the smallest root cause, then rebuild/deploy/reload and compare a new diagnosis against the previous run.
- Do not commit raw `.obsidian-debug/` logs unless explicitly requested.
- Do not leak API keys or bearer tokens into diagnosis, reports, or handoff manifests.
- Do not claim “GUI verified” from screenshot alone; say “visual review artifact generated” unless a human/manual GUI pass actually happened.
