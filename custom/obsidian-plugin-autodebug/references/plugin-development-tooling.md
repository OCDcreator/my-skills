# From-Zero Plugin Development Tooling

Use this page when the task starts before there is a real plugin repository, or when an existing repository needs stronger development scaffolding before the debug loop begins.

## Routing

| User intent | Route | Why |
| --- | --- | --- |
| Production plugin from scratch | `generator-obsidian-plugin` or the official sample plugin | Creates a real repo structure before autodebug adds job specs, assertions, and runtime capture. |
| Minimal smoke/debug fixture | `scripts/obsidian_debug_scaffold_plugin.mjs` | Creates only a lightweight local fixture for validating the autodebug framework. |
| Existing repo with weak quality gates | Add repo-owned lint/test scripts, then run doctor | Keeps project ownership in `package.json` instead of hard-coding a global debug loop. |
| AI/network plugin | Add SecretStorage, redaction, and request boundary checks before handoff | Prevents agent tools and diagnostics from leaking keys or hiding external behavior. |

## Recommended Stack

- **Template**: start from `generator-obsidian-plugin` when the user wants a production project; use `obsidianmd/obsidian-sample-plugin` when official minimalism is preferred.
- **Build/runtime utilities**: if the generated project uses `obsidian-dev-utils`, prefer its `dev`, `build`, `lint`, `test`, copy, release, and settings helpers instead of inventing parallel scripts.
- **Official lint rules**: wire `obsidianmd/eslint-plugin` through a repo-owned lint script; doctor detects `eslint-plugin-obsidianmd` and preflight scripts when present.
- **Runtime smoke**: add an autodebug job spec after the repo builds; keep Obsidian desktop reload, screenshot, DOM, and console capture local-only.
- **E2E escalation**: only add `wdio-obsidian-service`, Playwright-based E2E, `obsidian-e2e`, or `obsidian-testing-framework` when the repo owns fixtures and scripts.
- **Review readiness**: run `scripts/obsidian_debug_review_readiness.mjs` and doctor’s advisory review checks before treating a smoke pass as release-ready.

## Official Rule Themes To Encode Early

These should be reflected in scaffold prompts, review-readiness checks, lint config, and agent review instructions:

- **Naming/release hygiene**: remove sample names, avoid redundant `Obsidian`/`Plugin` naming, and do not commit generated release `main.js` unless the release process requires it.
- **Command/UI style**: avoid default hotkeys, avoid repeating plugin ID/name in command IDs and names, and use sentence case for UI text.
- **Lifecycle/memory**: register events/intervals, avoid storing stale view references, avoid global `app`, and keep `main.ts` small enough to review.
- **Mobile compatibility**: gate Node/Electron APIs behind desktop checks, avoid unsupported regex lookbehind when mobile support matters, and use Obsidian `Platform` APIs.
- **Network/security**: prefer `requestUrl` for external requests, disclose network/account/payment/telemetry behavior, avoid client-side telemetry, keep dependencies small, and use lockfiles.
- **Data APIs**: prefer `Editor`, `Vault.process`, `FileManager.processFrontMatter`, `FileManager.trashFile`, `Plugin.loadData`, `Plugin.saveData`, and `normalizePath`.
- **Performance**: keep startup light, use `workspace.onLayoutReady()` for UI setup that needs layout, minimize release bundles, and avoid whole-vault iteration for path lookups.

## Autodebug Integration Points

1. Create or identify the real plugin repo.
2. Add/verify `package.json` scripts: `build`, `lint`, optional `test`, optional E2E lane.
3. Run doctor:

```bash
node scripts/obsidian_debug_doctor.mjs --repo-dir <repo> --plugin-id <id> --output <repo>/.obsidian-debug/doctor.json
```

4. Generate CI templates only after the local desktop smoke path is understood:

```bash
node scripts/obsidian_debug_ci_templates.mjs --repo-dir <repo> --job <repo>/.obsidian-debug/job.json --output-dir <repo>/autodebug/ci
```

5. For AI/network plugins, run agentic safety probes and include results in `agent-tools.json`.

## Source Map

- Obsidian self-critique checklist: <https://docs.obsidian.md/oo/plugin>
- Obsidian sample plugin: <https://github.com/obsidianmd/obsidian-sample-plugin>
- Obsidian developer docs source: <https://github.com/obsidianmd/obsidian-developer-docs>
- Obsidian official ESLint plugin: <https://github.com/obsidianmd/eslint-plugin>
- `generator-obsidian-plugin`: <https://github.com/mnaoumov/generator-obsidian-plugin>
- `obsidian-dev-utils`: <https://github.com/mnaoumov/obsidian-dev-utils>
- WDIO Obsidian service docs: <https://webdriver.io/docs/wdio-obsidian-service/>
- Chrome DevTools MCP: <https://github.com/ChromeDevTools/chrome-devtools-mcp>
- Playwright MCP: <https://github.com/microsoft/playwright-mcp>

## Boundaries

- Do not install new frameworks by default; recommend them only when the project shape or user request justifies them.
- Do not replace the runtime smoke loop with static review rules. Use both: lint/review gates catch preventable issues; CLI/CDP/Playwright evidence catches real Obsidian behavior.
- Do not claim review-readiness output equals official Obsidian acceptance.
