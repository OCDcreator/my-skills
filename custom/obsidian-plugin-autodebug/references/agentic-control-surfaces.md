# Agentic Control Surfaces

Use this table to choose the control lane per task. Keep the default path CLI-first, then bundled CDP fallback.

| Surface | Best use | Can control plugin reload/log capture? | Notes |
| --- | --- | --- | --- |
| Obsidian CLI (`obsidian-cli`) | Default desktop debug loop: reload, console/errors, screenshot, DOM/CSS | Yes | First choice when `obsidian help` exposes `Developer:` commands. |
| Bundled CDP scripts (`scripts/obsidian_cdp_*.mjs`) | Early startup logs, strict event ordering, real-time trace | Yes | Portable fallback when CLI is unavailable or misses timing-critical evidence. |
| Chrome DevTools MCP | Agent-native DevTools automation on the Obsidian Electron target | Yes (if attached to the Obsidian app target) | Optional lane; validate target selection and permissions before trusting. |
| Playwright MCP | Browser-style automation and locator assertions | Partial | Useful for UI interaction/assertions; usually not the primary plugin reload control lane. |
| Obsidian CLI REST | HTTP wrapper around Obsidian CLI commands | Yes (if server exposes reload/dev endpoints) | Treat as optional local bridge; require localhost binding, auth key, and tool allowlist checks. |
| Vault MCP | Vault content read/write/search for notes/files | No | Vault content only; does not prove desktop devtools/reload control exists. |
| Nexus / Claudesidian-like vault MCP | Extended vault indexing/search/chat over vault data | No | Still vault-content-centric; not a replacement for plugin runtime control. |
| MCP Inspector | Inspect/test MCP server tool schema and calls | No | Useful for server/tool validation only; not a desktop smoke runner. |

Quick rule:

- Need reload, console/errors, screenshot, DOM on live plugin runtime: choose CLI/CDP/DevTools MCP lanes.
- Need vault notes/files only: choose Vault MCP/Nexus-style lanes.
- Need MCP server introspection/debugging: choose MCP Inspector.

## Backend Contract

The skill now exposes a compact control backend abstraction so agents do not have to guess which surface to use for every step.

Generate it from doctor/diagnosis evidence:

```bash
node scripts/obsidian_debug_control_backend_support.mjs \
  --doctor .obsidian-debug/doctor.json \
  --diagnosis .obsidian-debug/diagnosis.json \
  --output .obsidian-debug/control-backends.json
```

Backend ids:

- `obsidian-cli`: local developer commands for reload, console/errors, screenshot, DOM, and scenarios.
- `bundled-cdp`: bundled CDP scripts for console/error trace, screenshot, DOM, scenario, and network/perf inspection.
- `obsidian-cli-rest`: local REST/MCP bridge when probed with localhost/auth/allowlist evidence.
- `chrome-devtools-mcp`: agent-native DevTools backend after target selection is confirmed.
- `playwright-script`: repo-owned Playwright/WDIO/E2E script lane for locator assertions and visual review evidence.
- `playwright-mcp`: agent-native Playwright backend for snapshot/click/fill/screenshot style UI work.

Capability routing is advisory, not magic. External MCP/REST backends still need the agent runtime to provide actual callable tools. Local scripts can execute `obsidian-cli`, `bundled-cdp`, and `playwright-script` paths directly; DevTools MCP and Playwright MCP remain agent-native external backends unless the current runtime exposes their tools.
