# Autopilot Round Roadmap

## Queue

### [DONE] B1 - Config-driven debug job spec and platform-neutral command adapters

- **Lane**: Bugfix / backlog
- **Goal**: Replace long ad-hoc cycle command templates with a generic job spec that describes build, deploy, reload, log watch, scenario, assertions, comparison, profile, report, and state handling.
- **Priority entrypoints**:
- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/`
- `custom/obsidian-plugin-autodebug/assertions/`
- `custom/obsidian-plugin-autodebug/rules/`
- **Constraints**:
  - Keep schemas and examples plugin-agnostic
  - Support Windows PowerShell and macOS/Linux Bash quoting without plugin-specific branches
  - Avoid unrelated cleanup
- **Acceptance**:
  - A generic job spec format and runner path exist or are measurably advanced
  - Existing direct-command workflows remain documented as fallback
  - At least one Windows-style and one Bash-style dry-run/example command is documented
  - The phase doc records scope, changed files, and validation results

### [DONE] B2 - Generic view-open strategy chain and selector discovery

- **Lane**: Bugfix / backlog
- **Goal**: Add plugin-neutral ways to open a plugin surface and discover likely root selectors, headings, settings surfaces, error banners, and empty states.
- **Constraints**:
  - Prefer declared plugin metadata first, then Obsidian commands/view types, then CDP DOM heuristics
  - Do not hard-code OpenCodian selectors except in example fixtures
- **Acceptance**:
  - The strategy chain is documented and testable with a synthetic or real plugin fixture
  - Discovery output is machine-readable for downstream assertions

### [DONE] B3 - Rich generic assertions and performance budgets

- **Lane**: Bugfix / backlog
- **Goal**: Extend assertions beyond simple DOM/log checks to cover counts, visibility, text regex, attributes, computed styles, grouped log rules, and timing budgets.
- **Constraints**:
  - Keep assertion definitions declarative JSON
  - Preserve fail/warn/expected/flaky severities
- **Acceptance**:
  - Assertion failures are summarized in diagnosis and report outputs
  - Generic examples do not require a specific plugin

### [DONE] B4 - Baseline taxonomy, regression comparison, and retention

- **Lane**: Bugfix / backlog
- **Goal**: Classify baselines by platform, vault state, cold/warm mode, scenario, plugin id, and run label; compare against the closest matching baseline.
- **Constraints**:
  - Keep old diagnosis/comparison files readable
  - Avoid absolute local paths in committed examples
- **Acceptance**:
  - Baseline save/list/compare flows can select by tags
  - Retention rules protect recent useful artifacts and clean stale debug output

### [DONE] B5 - Screenshot diff and report artifact previews

- **Lane**: Bugfix / backlog
- **Goal**: Add screenshot comparison and richer HTML report sections for UI regressions that DOM checks miss.
- **Constraints**:
  - Prefer optional dependencies or pure Node fallback behavior
  - Reports should degrade gracefully when screenshots are missing
- **Acceptance**:
  - Pixel/region diff results are recorded in diagnosis or comparison output
  - HTML reports link screenshots, DOM snapshots, logs, and diffs

### [DONE] B6 - Executable playbooks, doctor --fix, and state matrices

- **Lane**: Bugfix / backlog
- **Goal**: Turn diagnostic playbooks into safe command templates and add doctor/fix plus clean-state/restored-state matrix helpers.
- **Constraints**:
  - Commands must be explicit, dry-run friendly, and never destructive by default
  - Local absolute paths belong in runtime profiles, not committed defaults
- **Acceptance**:
  - Playbooks can suggest runnable next steps with safety labels
  - Doctor reports missing CLI/CDP/build/deploy prerequisites with optional fixes

### [DONE] B7 - Cross-platform validation checkpoint

- **Lane**: Checkpoint
- **Goal**: Run or document Windows and macOS smoke tests for shipped automation slices and decide whether to continue the backlog lane.
- **Constraints**:
  - Do not add new feature work in this checkpoint
  - Record failures as follow-up queue items instead of silently widening scope
- **Acceptance**:
  - The phase doc captures shipped slices, smoke results, remaining risks, and the stop/continue recommendation

### [DONE] B8 - Smoke-mode diagnosis honors intentional skips

- **Lane**: Bugfix / backlog
- **Goal**: Make smoke-style validation runs distinguish intentionally skipped screenshot/DOM/console artifacts from truly missing artifacts so lightweight CI-like checks can pass without faking full UI capture.
- **Constraints**:
  - Preserve blocking failures when artifact capture was requested but missing
  - Keep diagnosis/report outputs backward compatible for existing full-capture runs
- **Acceptance**:
  - Smoke jobs can mark capture as intentionally skipped without forcing a blocking diagnosis failure
  - Reports and comparison flows keep enough metadata to tell skipped capture apart from capture regressions

### [DONE] B9 - Native macOS smoke host validation

- **Lane**: Checkpoint follow-up
- **Goal**: Re-run the shipped Bash/macOS automation slices on a native macOS host and record real CLI/CDP/screenshot smoke evidence.
- **Constraints**:
  - Use plugin-neutral fixtures or generic sample data
  - Record host-specific failures as queue items instead of bundling unrelated fixes
- **Acceptance**:
  - The phase doc records native macOS smoke evidence for doctor, job/cycle, and state-matrix/report flows
  - Remaining macOS-only gaps are isolated into follow-up backlog items

### [DONE] B10 - Fresh-vault bootstrap and Node/WebSocket doctor follow-up

- **Lane**: Bugfix / backlog
- **Goal**: Close the remaining clean-vault first-install gap with zero-touch bootstrap and make doctor explicitly surface Node runtime WebSocket compatibility for CDP automation.
- **Constraints**:
  - Keep the bootstrap flow plugin-agnostic and cross-platform
  - Avoid hard-coding one repository, one vault, or one plugin id
  - Preserve the existing direct wrapper and job-spec entrypoints
- **Acceptance**:
  - Fresh-vault first-install flows can auto-discover and enable a newly copied plugin without manual reload/restart steps
  - Doctor reports fresh-vault discovery status and Node/WebSocket CDP readiness with runnable remediation commands
  - Windows and native macOS smoke validation record evidence for both additions

### [DONE] B11 - Package-manager and runtime doctor coverage

- **Lane**: Bugfix / backlog
- **Goal**: Teach the generic doctor/job runner how to identify Node version, Corepack readiness, npm/pnpm/yarn/bun usage, lockfiles, package-manager fields, and repo build/dev/test scripts so future rounds stop assuming npm-only workflows.
- **Constraints**:
  - Keep all detection plugin-agnostic and repo-driven
  - Treat missing optional tools as warnings unless they block the selected scenario
  - Do not silently overwrite repository-owned scripts or lockfiles
- **Acceptance**:
  - Doctor surfaces package-manager/runtime findings with clear remediation guidance
  - Job/cycle runners can choose inferred package-manager commands or explain why inference is weak
  - Windows and macOS smoke evidence covers at least one npm-style and one non-npm-style path or fixture

### [DONE] B12 - Optional Playwright and UI trace adapter

- **Lane**: Bugfix / backlog
- **Goal**: Add an optional Playwright-backed scenario adapter for richer UI interactions, locator assertions, and trace artifacts while preserving the existing CLI/CDP-first path.
- **Constraints**:
  - Keep Playwright optional and doctor-detected rather than mandatory
  - Preserve plugin-neutral scenario metadata and selector discovery
  - Do not break existing CLI/CDP-only smoke jobs
- **Acceptance**:
  - Scenario execution can choose CLI/CDP or Playwright adapters through config
  - Diagnosis/report artifacts can link Playwright traces/screenshots when available
  - Plugin-neutral fixtures or templates demonstrate the adapter without hard-coding one plugin

### [DONE] B13 - Hot Reload coordination doctor

- **Lane**: Bugfix / backlog
- **Goal**: Detect repository/vault Hot Reload conditions and guide automation toward controlled reload or Hot Reload-friendly modes so startup logs stay trustworthy.
- **Constraints**:
  - Treat Hot Reload support as optional context, not a hard dependency
  - Prefer detection plus strategy guidance over plugin-specific hacks
  - Preserve deterministic log ordering in explicit reload scenarios
- **Acceptance**:
  - Doctor reports likely Hot Reload presence or conflicting reload conditions with runnable advice
  - Job/cycle flows can opt into controlled reload or friendly coexistence modes
  - Reports make it clear when Hot Reload may have influenced captured timings/logs

### [DONE] B14 - Sample-plugin scaffold and bootstrap mode

- **Lane**: Bugfix / backlog
- **Goal**: Extend the framework from “debug an existing plugin” to “scaffold a minimal debug-ready plugin workspace” using generic sample-plugin patterns, manifest/bootstrap defaults, job specs, and assertions.
- **Constraints**:
  - Keep the scaffold generic and avoid baking in one plugin's branding or commands
  - Reuse existing debug job/spec/assertion templates where possible
  - Do not require online cloning during every smoke run if local templates suffice
- **Acceptance**:
  - The framework can generate or document a minimal plugin scaffold plus debug-ready job/config files
  - Fresh-vault bootstrap works against the scaffolded sample on Windows and macOS
  - Docs clearly separate scaffolding flows from existing-plugin retrofit flows

### [DONE] B15 - Optional testing-framework and CI templates

- **Lane**: Bugfix / backlog
- **Goal**: Add optional `obsidian-testing-framework` and CI-ready templates so agents can plug the framework into repeatable E2E/quality-gate pipelines after local smoke success.
- **Constraints**:
  - Keep adapters optional and degrade gracefully when dependencies are absent
  - Respect repository-owned validation commands instead of inventing mandatory gates
  - Avoid shipping CI steps that require secrets or machine-local absolute paths
- **Acceptance**:
  - Doctor or docs can detect/describe optional testing-framework support
  - The framework can emit or document CI-ready quality-gate templates for local/headless checks
  - The phase doc records what remains local-only versus CI-suitable

### [DONE] B16 - Optional ecosystem integration pass

- **Lane**: Bugfix / backlog
- **Goal**: Integrate the reviewed optional Obsidian ecosystem tools into doctor/docs/CI without turning them into mandatory dependencies: official lint rules, repo-owned `obsidian-dev-utils` flows, optional `obsidian-e2e` / `obsidian-testing-framework` / `wdio-obsidian-service` gates, persistent vault logging, MCP/CDP alternates, cross-device hot reload context, and release-adjacent validation routing.
- **Constraints**:
  - Keep repo-owned scripts authoritative instead of inventing parallel wrappers
  - Treat optional tools as additive signals, not hard requirements
  - Keep release automation routed to release-management flows rather than the default debug loop
- **Acceptance**:
  - Doctor surfaces optional ecosystem support when it is installed, declared, or visible in the target vault
  - CI templates can wire optional lint, plugin-entry validation, and repo-owned Obsidian E2E scripts without machine-local paths
  - Docs explain how `Logstravaganza`, MCP, `generator-obsidian-plugin`, `mobile-hot-reload`, `obsidian-typings`, and release-adjacent checks fit the debug workflow

### [DONE] B17 - Persistent vault log ingestion via Logstravaganza

- **Lane**: Bugfix / backlog
- **Goal**: Extend generic capture, diagnosis, and report flows so they can ingest `Logstravaganza` NDJSON logs from a vault when available, correlate them with existing console/CDP evidence, and preserve structured source metadata for downstream analysis.
- **Constraints**:
  - Keep file-based vault logging optional and additive; the framework must still work when no vault logger is installed
  - Prefer repo/vault-driven discovery of log paths over hard-coded machine-local locations
  - Preserve existing console/CDP capture paths and make merged log provenance explicit in reports
- **Acceptance**:
  - Doctor can detect usable `Logstravaganza` context and explain how the framework will consume it
  - Capture/analysis/report flows can import structured vault logs when present and degrade cleanly when absent
  - Fixture or sample artifacts validate NDJSON parsing, source attribution, and no-logger fallback behavior

### [NEXT] B18 - Preflight lint and plugin-entry validation gates

- **Lane**: Bugfix / backlog
- **Goal**: Turn optional `eslint-plugin-obsidianmd` and ReviewBot-style plugin-entry validation into reusable preflight checks that run before build/deploy flows and can be emitted into generated CI templates.
- **Constraints**:
  - Keep repository-owned lint scripts authoritative instead of inventing mandatory replacement commands
  - Treat plugin-entry validation as optional and avoid network, secret, or machine-local path requirements
  - Surface manifest/template residue issues early without widening scope into unrelated release automation
- **Acceptance**:
  - Doctor/runtime detection can identify runnable lint and plugin-entry preflight commands with remediation hints
  - Generated CI templates can emit optional lint and plugin-entry validation steps before build/deploy
  - Fixtures, templates, or docs demonstrate that manifest and template-residue failures can be caught pre-build

### [QUEUED] B19 - Repo-owned Obsidian E2E adapter fixtures and CI wiring

- **Lane**: Bugfix / backlog
- **Goal**: Make optional `obsidian-e2e`, `obsidian-testing-framework`, and `wdio-obsidian-service` support actionable by shipping detector-backed fixture/script patterns and CI wiring instead of documentation-only references.
- **Constraints**:
  - Keep every adapter optional and repo-owned; do not bundle Obsidian binaries or machine-local paths
  - Prefer existing repository scripts when present and only infer commands when the repo leaves them implicit
  - Preserve compatibility with the existing CLI/CDP-first path when no E2E adapter is installed
- **Acceptance**:
  - Doctor can distinguish declared dependencies from runnable adapter scripts and explain gaps clearly
  - Generated templates or fixtures demonstrate both Vitest-style and WebdriverIO-style Obsidian E2E lanes
  - CI wiring can target the chosen adapter without forcing one framework across all plugin repos

## Current state

- B1-B10 are complete.
- B11-B13 are complete.
- B14 is complete.
- B15 is complete.
- B16 is complete.
- B17 is complete.
- B18 is next.
- B19 is queued.
