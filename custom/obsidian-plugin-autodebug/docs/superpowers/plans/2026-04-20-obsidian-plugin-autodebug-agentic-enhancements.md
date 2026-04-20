# Obsidian Plugin Autodebug Agentic Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `obsidian-plugin-autodebug` from a desktop smoke/debug loop into an agent-native Obsidian plugin debugging framework that can discover MCP/REST/DevTools control surfaces, audit AI-plugin safety risks, emit machine-readable handoff tools, and surface official review-readiness gates without making the default loop project-specific.

**Architecture:** Keep the existing CLI/CDP-first runtime loop as the core. Add optional, auto-detected lanes through small focused detector/generator modules, then wire only summaries into `obsidian_debug_doctor.mjs`, reports, `SKILL.md`, and eval prompts. All AI/MCP/REST and official-review checks must remain optional support paths, not required defaults.

**Tech Stack:** Node.js ESM helper scripts, JSON fixtures/evals, Markdown skill references, existing doctor/job/analyze/report conventions. No package manager or new dependency should be introduced.

---

## Scope And Batch Map

### Batch 1: Agentic Control-Surface Reference And Skill Routing

**Purpose:** Document how agents should choose between Obsidian CLI, CDP, REST, MCP, Chrome DevTools MCP, Playwright MCP, Vault MCP, Nexus/Claudesidian, and Obsidian CLI REST.

**Files:**
- Create: `references/agentic-control-surfaces.md`
- Modify: `SKILL.md`
- Modify: `references/command-reference.md`
- Modify: `evals/evals.json`

**Implementation steps:**
- [ ] Create `references/agentic-control-surfaces.md` with a compact decision table:
  - CLI-first: default for reload/log/screenshot/DOM when `obsidian help` exposes developer commands.
  - CDP: fallback for early startup logs, ordering, screenshots, DOM, DevTools-like traces.
  - Chrome DevTools MCP / Playwright MCP: optional agent-native control surfaces when already configured, but keep bundled scripts as portable fallback.
  - Obsidian CLI REST: optional local HTTP + MCP bridge for automation and AI assistants; require localhost/API-key/tool whitelist checks before trust.
  - Vault MCP / Nexus-style plugins: vault-content MCP tools, not proof that plugin reload/devtools control is available.
  - MCP Inspector: useful for validating MCP server tools/list and tool calls, not a replacement for desktop smoke.
- [ ] Add a short `Agentic Control Surfaces` section to `SKILL.md` after `Relationship To obsidian-cli`, pointing to the new reference and emphasizing optional detection.
- [ ] Add command-reference examples for probing MCP/REST surfaces, without hard-coding machine-local ports or tokens.
- [ ] Add 2 eval prompts:
  - `agentic-control-surface-selection`: user has CLI REST and Chrome DevTools MCP; expected answer picks control surface by task and security checks.
  - `vault-mcp-not-devtools`: user has Vault MCP only; expected answer does not claim plugin reload/log capture is solved.

**Validation:**
- [ ] Run `node -e "JSON.parse(require('fs').readFileSync('evals/evals.json','utf8')); console.log('evals ok')"`.
- [ ] Run a grep sanity check that `SKILL.md` links `references/agentic-control-surfaces.md`.

### Batch 2: AI/MCP/REST Doctor Detection

**Purpose:** Add a focused detector that reports optional AI/MCP/REST support and AI-plugin risk signals without changing the default doctor contract.

**Files:**
- Create: `scripts/obsidian_debug_agentic_support.mjs`
- Modify: `scripts/obsidian_debug_doctor.mjs`
- Create: `fixtures/agentic-ai-smoke-plugin/package.json`
- Create: `fixtures/agentic-ai-smoke-plugin/manifest.json`
- Create: `fixtures/agentic-ai-smoke-plugin/src/main.ts`
- Create: `fixtures/agentic-ai-smoke-plugin/dist/main.js`
- Create: `fixtures/agentic-ai-smoke-plugin/dist/manifest.json`

**Detector responsibilities:**
- [ ] Read `package.json`, `manifest.json`, `src/**/*.ts`, `src/**/*.tsx`, `main.ts`, and root scripts when present.
- [ ] Detect declared or installed packages/scripts for MCP/REST/devtools-like control:
  - package/script/name tokens: `@modelcontextprotocol`, `mcp`, `obsidian-cli-rest`, `chrome-devtools-mcp`, `@playwright/mcp`, `playwright`, `vault-mcp`, `nexus`, `claudesidian`.
  - vault plugin dir signals when `testVaultPluginDir` is supplied: sibling plugin ids likely containing `obsidian-cli-rest`, `vault-mcp`, `nexus`, `claudesidian`, `logstravaganza`, hot reload.
- [ ] Detect AI-plugin safety signals:
  - positive: `app.secretStorage`, `SecretStorage`, `SecretComponent`, redaction helpers, diagnostic export/clipboard helpers.
  - warning: `apiKey`, `token`, `secret`, `Authorization`, `localStorage`, `saveData`, `console.log`, `requestUrl`, `fetch`, OpenAI-compatible provider URLs.
  - explain that text hits are heuristic and must not be treated as proof of a vulnerability.
- [ ] Return a stable JSON object with `controlSurfaces`, `aiSafety`, `recommendations`, and `sourceFiles`.
- [ ] Export `detectAgenticSupport({ repoDir, testVaultPluginDir })` for doctor use and allow direct CLI usage with `--repo-dir`, `--test-vault-plugin-dir`, and `--output`.

**Doctor integration:**
- [ ] Import and call `detectAgenticSupport` in `scripts/obsidian_debug_doctor.mjs`.
- [ ] Add doctor checks:
  - `agentic-control-surfaces`: status `info|warn|pass` based on detected optional surfaces.
  - `ai-plugin-secret-storage`: `pass` when secret storage signals exist, `warn` when key/token signals exist without secret storage, `info` otherwise.
  - `ai-plugin-network-boundary`: `warn` when external request signals exist and no settings/privacy/redaction hints are detected.
  - `mcp-rest-security`: `warn` when REST/MCP signals exist but no localhost/auth/whitelist hints are detected.
- [ ] Include `agenticSupport` in the final doctor JSON.

**Fixture requirements:**
- [ ] Fixture manifest id: `agentic-ai-smoke-plugin`.
- [ ] Fixture `src/main.ts` should intentionally include both good and risky patterns: `app.secretStorage`, `requestUrl`, an `apiKey` setting key, and a redaction function.
- [ ] Fixture `dist/main.js` can be minimal deployable smoke output.

**Validation:**
- [ ] Run `node scripts/obsidian_debug_agentic_support.mjs --repo-dir fixtures/agentic-ai-smoke-plugin --output .obsidian-debug/agentic-support-smoke.json`.
- [ ] Run `node scripts/obsidian_debug_doctor.mjs --repo-dir fixtures/agentic-ai-smoke-plugin --plugin-id agentic-ai-smoke-plugin --output .obsidian-debug/agentic-doctor-smoke.json`.
- [ ] Confirm the output JSON contains `agenticSupport`, `agentic-control-surfaces`, and `ai-plugin-secret-storage`.

### Batch 3: Agent Handoff Manifest

**Purpose:** Generate a compact machine-readable artifact that tells the next model what it can safely call next, which evidence files exist, and which control surfaces were detected.

**Files:**
- Create: `scripts/obsidian_debug_agent_tools.mjs`
- Modify: `scripts/obsidian_debug_analyze.mjs`
- Modify: `scripts/obsidian_debug_report.mjs`
- Modify: `references/command-reference.md`
- Modify: `evals/evals.json`

**Manifest schema:**
- [ ] `generatedAt`, `status`, `pluginId`, `vaultName`, `repoDir`, `outputDir`.
- [ ] `controlSurfaces`: derived from summary/diagnosis/doctor when available; include `cli`, `cdp`, `playwright`, `logstravaganza`, `mcpRest`, `devtoolsMcp`.
- [ ] `safeActions`: reviewable next commands such as rerun doctor, dry-run job, run analyzer, capture CDP UI, run scenario; never include secrets or API keys.
- [ ] `evidence`: paths to `summary.json`, `diagnosis.json`, `doctor.json`, `screenshot.png`, DOM/html/text logs, CDP traces, vault log capture, report HTML.
- [ ] `nextRecommendations`: top diagnosis recommendations and agentic-support recommendations.
- [ ] `warnings`: missing evidence, unsafe control surface, no auth/localhost evidence, raw log redaction reminders.

**Analyzer/report integration:**
- [ ] `scripts/obsidian_debug_agent_tools.mjs` should be usable standalone:
  - `node scripts/obsidian_debug_agent_tools.mjs --summary .obsidian-debug/summary.json --diagnosis .obsidian-debug/diagnosis.json --doctor .obsidian-debug/doctor.json --output .obsidian-debug/agent-tools.json`
- [ ] `scripts/obsidian_debug_analyze.mjs` should write `agentToolsPath` into diagnosis when `--agent-tools-output <path>` is provided.
- [ ] `scripts/obsidian_debug_report.mjs` should render a small `Agent handoff` section when diagnosis references an agent tools path or when `--agent-tools <path>` is supplied.
- [ ] Command reference should show the standalone command and explain that it is for model-to-model handoff.
- [ ] Add an eval prompt `agent-handoff-manifest` expecting an answer to generate/read `agent-tools.json` before handing off to another agent.

**Validation:**
- [ ] Create a small synthetic summary/diagnosis/doctor JSON under `.obsidian-debug/` during validation.
- [ ] Run the standalone script and parse output JSON.
- [ ] Run `node scripts/obsidian_debug_report.mjs --diagnosis <diagnosis> --agent-tools <agent-tools> --output .obsidian-debug/agent-tools-report.html`.

### Batch 4: Review-Readiness And Official-Guideline Gate

**Purpose:** Add optional Obsidian official review readiness signals so agents can catch obvious release-review blockers before runtime smoke passes are treated as release-ready.

**Files:**
- Create: `references/review-readiness.md`
- Create: `scripts/obsidian_debug_review_readiness.mjs`
- Modify: `scripts/obsidian_debug_doctor.mjs`
- Modify: `references/command-reference.md`
- Modify: `SKILL.md`
- Modify: `fixtures/preflight-smoke-plugin/src/main.ts` or create `fixtures/review-readiness-smoke-plugin/*` if cleaner.
- Modify: `evals/evals.json`

**Review readiness checks:**
- [ ] Manifest basics: `id`, `name`, `version`, `minAppVersion`, short description, desktop-only requirement when Node/Electron APIs are detected.
- [ ] Sample residue: placeholder class/plugin names, sample commands/settings strings, obvious `obsidian-sample-plugin` text.
- [ ] Console/logging: warn when `console.log` exists without debug/redaction gating.
- [ ] DOM security: warn on `innerHTML`, `outerHTML`, `insertAdjacentHTML`.
- [ ] Network/telemetry disclosure: warn on `fetch`, `requestUrl`, `navigator.sendBeacon`, analytics tokens unless docs/privacy/settings hints exist.
- [ ] UI text basics: warn on obvious title-case setting headings only as heuristic, not hard failure.

**Doctor integration:**
- [ ] Include `reviewReadiness` in doctor JSON.
- [ ] Add doctor check `review-readiness` with aggregate status and top issues.
- [ ] Keep wording clear: this is an optional heuristic gate, not an official Obsidian review result.

**Reference update:**
- [ ] `references/review-readiness.md` should cite the upstream source URLs as references and keep copied wording short/paraphrased.
- [ ] Link it from `SKILL.md` under CI/release-adjacent checks.

**Validation:**
- [ ] Run review readiness script on the existing `fixtures/preflight-smoke-plugin` and the new/reused review fixture.
- [ ] Run doctor on that fixture and verify a review-readiness check appears.
- [ ] Parse `evals/evals.json` after adding prompt `official-review-readiness-gate`.

### Batch 5: Consolidation, JSON Schema Drift, And Smoke Validation

**Purpose:** Ensure all batches compose cleanly and do not make the default skill OpenCodian-specific or require unavailable external tools.

**Files:**
- Modify only if needed after integration: `job-specs/obsidian-debug-job.schema.json`, `SKILL.md`, `references/command-reference.md`, `evals/evals.json`.

**Checks:**
- [ ] Run `node --check` on every changed `.mjs` script.
- [ ] Run every changed `.mjs --help` and confirm exit 0.
- [ ] Parse all changed JSON files.
- [ ] Run direct smoke commands for new scripts against fixtures.
- [ ] Run `rg -n "OpenCodian|opencodian" SKILL.md references scripts rules evals` and confirm generic defaults did not become OpenCodian-specific.
- [ ] Run `git diff --stat` and summarize all changed files.

---

## Non-Goals

- Do not add package dependencies.
- Do not require MCP, REST, Playwright MCP, Chrome DevTools MCP, or Obsidian CLI REST for the default debug loop.
- Do not store or print API keys, tokens, or MCP auth secrets.
- Do not claim heuristic review-readiness checks are equivalent to official Obsidian acceptance.
- Do not move OpenCodian-specific signatures into generic default rules.

## Source Notes Used For Planning

- `obsidian-cli-rest`: local HTTP API plus MCP server for Obsidian CLI commands, with localhost/API-key/tool-control concerns.
- `modelcontextprotocol/inspector`: MCP server testing/debugging and config export.
- `ChromeDevTools/chrome-devtools-mcp`: agent access to DevTools automation, performance, screenshots, and network analysis.
- `microsoft/playwright-mcp`: accessibility-snapshot browser automation for agents; CLI/skill workflows may be more token-efficient for coding agents.
- `jlevere/obsidian-mcp-plugin` and `ProfSynapse/claudesidian-mcp`: vault-content MCP plugins, useful but not a substitute for plugin reload/devtools control.
- `obsidianmd/obsidian-developer-docs`: plugin guidelines, submission requirements, `SecretStorage`, and `requestUrl` API references.
- `gapmiss/obsidian-plugin-skill`: agent-facing Obsidian quality/review skill with official guideline and ESLint-rule coverage.
