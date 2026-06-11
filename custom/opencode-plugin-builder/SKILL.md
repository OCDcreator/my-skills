---
name: opencode-plugin-builder
description: Guide LLMs through writing, testing, and configuring OpenCode plugins using the @opencode-ai/plugin TypeScript API. Use when the user wants to create, modify, or debug an OpenCode plugin (.ts/.js), register custom tools via the tool() helper, hook into OpenCode lifecycle events (tool.execute.before/after, chat.message, shell.env, config, permission.ask, etc.), configure plugin loading in opencode.json, or needs the complete Hooks API reference with real-world examples. Triggers: OpenCode plugin, opencode plugin, @opencode-ai/plugin, plugin hook, custom tool, tool override, opencode.json plugin array, .opencode/plugins/, tool.execute.before, tool.execute.after, OpenCode 扩展, OpenCode 插件开发, 写 opencode 插件.
---

# OpenCode Plugin Builder

## Overview

OpenCode plugins are TypeScript/JavaScript modules that extend OpenCode through hooks and custom tools. A plugin is an **async function** that receives a `PluginInput` context and returns a `Hooks` object. Runs on the Bun runtime.

**Core principle:** Export a function (named or default), not an object. The function receives context, returns hooks.

## When to Use

- Creating new custom tools for OpenCode agents
- Hooking into tool execution (before/after) to transform arguments or output
- Injecting environment variables into shell commands
- Overriding built-in tool behavior (read, grep, glob, bash)
- Sending notifications on session events
- Protecting sensitive files (e.g. blocking .env reads)
- Modifying LLM parameters or system prompts per-session

## Quick Start — Minimal Plugin

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ $ }) => {
  return {
    tool: {
      my_tool: tool({
        description: "This is a custom tool",
        args: {
          foo: tool.schema.string().describe("Some input"),
        },
        async execute(args) {
          return `Hello ${args.foo}!`
        },
      }),
    },
  }
}
```

Save to `.opencode/plugins/my-plugin.ts` — auto-loaded, no config needed.

## PluginInput — What You Receive

| Field | Type | Description |
|-------|------|-------------|
| `client` | `OpencodeClient` | SDK client for HTTP API calls |
| `project` | `Project` | Current project metadata |
| `directory` | `string` | Current working directory |
| `worktree` | `string` | Git worktree root |
| `serverUrl` | `URL` | OpenCode server URL |
| `$` | `BunShell` | Bun shell for running commands |

## Hooks — Quick Decision Matrix

```
Need to...                              → Use this hook
─────────────────────────────────────────────────────────
Add a new tool for the agent            → tool: { name: tool({...}) }
Override a built-in tool                → tool: { read/grep/glob/bash: ... }
Transform tool arguments before run     → tool.execute.before
Transform tool output after run         → tool.execute.after
Inject env vars into shell commands     → shell.env
Change tool descriptions for LLM        → tool.definition
Modify merged config programmatically   → config
Listen to all events                    → event
Transform user messages                 → chat.message
Adjust LLM params per request           → chat.params
Add custom HTTP headers to LLM requests → chat.headers
Override permission decisions           → permission.ask
Pre-process slash commands              → command.execute.before
Customize system prompt                 → experimental.chat.system.transform
Customize compaction behavior           → experimental.session.compacting
```

→ **For complete hook signatures, types, and code samples, read `references/hooks-api.md`.**

## Custom Tools via `tool()`

The `tool()` helper registers tools in the agent's palette. Uses Zod schemas:

```typescript
tool({
  description: "What this tool does",
  args: {
    query: tool.schema.string().describe("Search keyword"),
    limit: tool.schema.number().optional().describe("Max results"),
  },
  async execute(args, ctx) {
    // ctx: { sessionID, directory, worktree, abort, metadata(), ask() }
    ctx.metadata({ title: "Searching..." })  // UI feedback
    const result = await $`rg -l ${args.query} .`.quiet().nothrow()
    return result.stdout.toString() || "No results."
    // Also valid: return { output: "...", metadata: { ... } }
  },
})
```

**Key:** Plugin tools with the same name as built-ins (read, grep, glob) take precedence.

## Registration — How OpenCode Finds Your Plugin

### Auto-Discovery (Recommended)

Place `.ts` or `.js` files in plugin directories — no config needed:

| Scope | Path |
|-------|------|
| Project | `.opencode/plugins/` |
| Global | `~/.config/opencode/plugins/` |

### opencode.json plugin Array

```json
{
  "plugin": [
    "my-plugin",                     // npm package (latest)
    "my-plugin@1.2.3",               // npm package (pinned)
    "./local-plugin.ts",             // Local file
    ["my-plugin", { "debug": true }] // With options
  ]
}
```

### Load Order

1. Global config (`~/.config/opencode/opencode.json`) npm plugins
2. Project config (`opencode.json`) npm plugins
3. Global plugin directory (`~/.config/opencode/plugins/`)
4. Project plugin directory (`.opencode/plugins/`)

Duplicate npm packages (same name + version) load once.

## Dependencies for Local Plugins

Add `.opencode/package.json` — OpenCode runs `bun install` at startup:

```json
{
  "dependencies": {
    "shescape": "^2.1.0"
  }
}
```

## Structured Logging

Use `client.app.log()` instead of `console.log`:

```typescript
await client.app.log({
  body: { service: "my-plugin", level: "info", message: "Initialized" }
})
```

Levels: `debug`, `info`, `warn`, `error`.

## Event Types

The `event` hook receives all bus events. Key types:

| Category | Events |
|----------|--------|
| **Session** | `session.idle`, `session.created`, `session.compacted`, `session.error` |
| **Message** | `message.updated`, `message.part.updated` |
| **File** | `file.edited`, `file.watcher.updated` |
| **Tool** | `tool.execute.before`, `tool.execute.after` |
| **Permission** | `permission.asked`, `permission.replied` |

Common pattern — notify on completion:

```typescript
event: async ({ event }) => {
  if (event.type === "session.idle") {
    await $`osascript -e 'display notification "Done!" with title "opencode"'`.nothrow()
  }
},
```

## Critical Pitfalls (Top 3)

1. **Bun.spawn > Bun Shell `$` templates** — shell template breaks multi-word args. Use `Bun.spawn(["cmd", ...args])` for external tools.
2. **Always include native fallbacks** — external tools may not be installed. Try custom logic first, fall back to native.
3. **Config not hot-reloaded** — restart opencode after plugin changes.

→ **For full pitfall list with code examples, read `references/pitfalls.md`.**

## Verification

```bash
# Check plugin loads without errors
opencode run "hello" --format json 2>&1 | head -20

# Verify custom tool appears in tool calls
opencode run "Use my_tool with foo=test" --format json --dangerously-skip-permissions
```

## npm Publishing (Optional)

Export a `PluginModule` with `server` field:

```typescript
import type { Plugin, PluginModule } from "@opencode-ai/plugin"
const MyPlugin: Plugin = async (input) => { return { /* hooks */ } }
const module: PluginModule = { id: "my-plugin", server: MyPlugin }
export default MyPlugin
export { MyPlugin }
```

Users install via: `"plugin": ["your-npm-package"]`

## Reference Files

| File | When to Read |
|------|-------------|
| `references/hooks-api.md` | Need complete hook signatures, types, and code for any specific hook |
| `references/examples.md` | Need real-world plugin examples (tool override, .env protection, notifications) |
| `references/pitfalls.md` | Hitting a bug or unexpected behavior — check the full pitfall list |
| `references/plugin-template.ts` | Copy-paste starting point with all hook types (commented out) |

## External References

| URL | Description |
|-----|-------------|
| https://opencode.ai/docs/plugins/ | Official plugin documentation |
| https://opencode.ai/config.json | OpenCode config JSON Schema |
| https://opencode.ai/docs/custom-tools/ | Official custom tools documentation |
