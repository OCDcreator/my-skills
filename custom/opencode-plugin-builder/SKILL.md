---
name: opencode-plugin-builder
description: Guide LLMs through writing, testing, and configuring OpenCode plugins using the @opencode-ai/plugin TypeScript API. Use when the user wants to create, modify, or debug an OpenCode plugin (.ts/.js), register custom tools via the tool() helper, hook into OpenCode lifecycle events (tool.execute.before/after, chat.message, shell.env, config, permission.ask, etc.), configure plugin loading in opencode.json, or needs the complete Hooks API reference with real-world examples. Triggers: OpenCode plugin, opencode plugin, @opencode-ai/plugin, plugin hook, custom tool, tool override, opencode.json plugin array, .opencode/plugins/, tool.execute.before, tool.execute.after, OpenCode 扩展, OpenCode 插件开发, 写 opencode 插件.
---

# OpenCode Plugin Builder

## Overview

OpenCode plugins are TypeScript/JavaScript modules that extend OpenCode's behavior through hooks and custom tools. A plugin is an **async function** that receives a `PluginInput` context and returns a `Hooks` object. Plugins run on the Bun runtime.

**Core principle:** Export a function (named or default), not an object. The function receives context, returns hooks.

## When to Use

- Creating new custom tools for OpenCode agents
- Hooking into tool execution (before/after) to transform arguments or output
- Injecting environment variables into shell commands
- Overriding built-in tool behavior (read, grep, glob, bash)
- Adding authentication providers
- Modifying LLM parameters or system prompts per-session
- Registering custom workspace adaptors
- Sending notifications on session completion or other events
- Protecting sensitive files (e.g. blocking .env reads)

## Quick Reference — Plugin Anatomy

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ client, project, directory, worktree, serverUrl, $ }) => {
  // Setup logic runs once on plugin load

  return {
    // Register custom tools
    tool: {
      my_tool: tool({ /* ... */ }),
    },

    // Hook into lifecycle events
    "tool.execute.before": async (input, output) => { /* ... */ },
    "tool.execute.after": async (input, output) => { /* ... */ },
    "shell.env": async (input, output) => { /* ... */ },
    config: async (cfg) => { /* ... */ },
    event: async ({ event }) => { /* ... */ },
  }
}) satisfies Plugin
```

## Dependencies for Local Plugins

Local plugins can use external npm packages. Add a `package.json` to your config directory:

```
.opencode/
  package.json        # Dependencies for local plugins/tools
  plugins/
    my-plugin.ts      # Can import packages from package.json
```

**.opencode/package.json:**

```json
{
  "dependencies": {
    "shescape": "^2.1.0"
  }
}
```

OpenCode runs `bun install` at startup to install these. Your plugins can then `import` them directly.

**For npm-published plugins**, dependencies go in the plugin's own `package.json` — no extra setup needed.

## Event Types Reference

The `event` hook receives all bus events. Key event types:

| Category | Events |
|----------|--------|
| **Session** | `session.created`, `session.idle`, `session.compacted`, `session.error`, `session.deleted`, `session.updated`, `session.diff`, `session.status` |
| **Message** | `message.updated`, `message.removed`, `message.part.updated`, `message.part.removed` |
| **Tool** | `tool.execute.before`, `tool.execute.after` |
| **File** | `file.edited`, `file.watcher.updated` |
| **Permission** | `permission.asked`, `permission.replied` |
| **Shell** | `shell.env` |
| **LSP** | `lsp.client.diagnostics`, `lsp.updated` |
| **TUI** | `tui.prompt.append`, `tui.command.execute`, `tui.toast.show` |
| **Server** | `server.connected` |
| **Todo** | `todo.updated` |
| **Installation** | `installation.updated` |
| **Command** | `command.executed` |

Common usage — send notification on session completion:

```typescript
event: async ({ event }) => {
  if (event.type === "session.idle") {
    await $`osascript -e 'display notification "Done!" with title "opencode"'`
  }
},
```

## Structured Logging

Use `client.app.log()` instead of `console.log` for proper structured logging:

```typescript
await client.app.log({
  body: {
    service: "my-plugin",
    level: "info",       // debug | info | warn | error
    message: "Plugin initialized",
    extra: { foo: "bar" },
  },
})
```

## PluginInput — What You Receive

| Field | Type | Description |
|-------|------|-------------|
| `client` | `OpencodeClient` | SDK client for HTTP API calls |
| `project` | `Project` | Current project metadata |
| `directory` | `string` | Current working directory |
| `worktree` | `string` | Git worktree root |
| `serverUrl` | `URL` | OpenCode server URL |
| `$` | `BunShell` | Bun shell for running commands |

## Hooks API — Complete Reference

### Custom Tools

Register tools that appear in the agent's tool palette:

```typescript
tool: {
  search_docs: tool({
    description: "Search project documentation for a keyword",
    args: {
      query: tool.schema.string().describe("Search keyword"),
      max_results: tool.schema.number().optional().describe("Max results (default 10)"),
    },
    async execute(args, ctx) {
      // ctx.sessionID, ctx.directory, ctx.worktree, ctx.abort (AbortSignal)
      // ctx.metadata({ title: "Searching..." }) for UI feedback
      const result = await $`rg -l ${args.query} docs/`.quiet().nothrow()
      return result.stdout.toString() || "No results found."
    },
  }),
}
```

**Key points:**
- `tool.schema` is Zod (`z`). Use `.string()`, `.number()`, `.boolean()`, `.array()`, `.enum()` etc.
- Return `string` or `{ output: string, metadata?: Record<string, any> }`
- Plugin tools **override** built-in tools with the same name (e.g. `read`, `grep`, `glob`)

### tool.execute.before — Intercept Tool Calls

Modify tool arguments before execution:

```typescript
"tool.execute.before": async (input, output) => {
  // input: { tool: string, sessionID: string, callID: string }
  // output: { args: any } — mutate in place

  if (input.tool === "bash") {
    const cmd = output.args?.command
    if (typeof cmd === "string" && cmd.startsWith("dangerous-cmd")) {
      output.args.command = `echo "Blocked: ${cmd}"`
    }
  }
},
```

### tool.execute.after — Post-Process Tool Output

Transform tool results after execution:

```typescript
"tool.execute.after": async (input, output) => {
  // input: { tool, sessionID, callID, args }
  // output: { title, output, metadata } — mutate in place

  if (input.tool === "bash") {
    // Truncate long outputs
    if (output.output.length > 5000) {
      output.output = output.output.slice(0, 5000) + "\n... [truncated]"
      output.title = "bash (truncated)"
    }
  }
},
```

### shell.env — Inject Environment Variables

Add environment variables to all shell executions:

```typescript
"shell.env": async (input, output) => {
  // input: { cwd, sessionID?, callID? }
  // output: { env: Record<string, string> }

  output.env["MY_TOOL_HOME"] = "/opt/my-tool"
  output.env["DEBUG"] = "1"
},
```

### config — Modify Merged Config

Mutate the live config object after all config files are merged:

```typescript
config: async (cfg) => {
  // cfg is the full merged Config object
  // Add instructions, adjust model, etc.
  if (!cfg.instructions) cfg.instructions = []
  cfg.instructions.push("docs/style.md")
},
```

### event — Listen to All Bus Events

Receive every event on the OpenCode event bus:

```typescript
event: async ({ event }) => {
  // event.type === "message" | "tool_call" | "session" | etc.
  console.log(`[plugin] event: ${event.type}`)
},
```

### chat.message — Modify User Messages

Transform incoming messages before they reach the LLM:

```typescript
"chat.message": async (input, output) => {
  // input: { sessionID, agent?, model?, messageID?, variant? }
  // output: { message: UserMessage, parts: Part[] }
},
```

### chat.params — Adjust LLM Parameters

Per-request temperature, topP, maxTokens adjustments:

```typescript
"chat.params": async (input, output) => {
  // output: { temperature, topP, topK, maxOutputTokens, options }
  if (input.agent === "plan") {
    output.temperature = 0.2  // Lower temperature for planning
  }
},
```

### chat.headers — Add Custom HTTP Headers

Inject headers into LLM API requests:

```typescript
"chat.headers": async (input, output) => {
  output.headers["X-Custom-Header"] = "value"
},
```

### permission.ask — Override Permission Decisions

Customize permission prompts:

```typescript
"permission.ask": async (input, output) => {
  // output: { status: "ask" | "deny" | "allow" }
  // Auto-allow specific tools
  if (input.tool === "my_custom_tool") {
    output.status = "allow"
  }
},
```

### tool.definition — Modify Tool Definitions

Change how tools appear to the LLM (description, parameters):

```typescript
"tool.definition": async (input, output) => {
  // input: { toolID: string }
  // output: { description: string, parameters: any }
  if (input.toolID === "bash") {
    output.description += "\nIMPORTANT: Always use --dry-run first."
  }
},
```

### experimental.* — Experimental Hooks

| Hook | Purpose |
|------|---------|
| `experimental.chat.messages.transform` | Transform message history before sending to LLM |
| `experimental.chat.system.transform` | Modify system prompt per session/model |
| `experimental.session.compacting` | Customize compaction prompt/context |
| `experimental.compaction.autocontinue` | Control auto-continue after compaction |
| `experimental.text.complete` | Intercept text completion |

### command.execute.before — Pre-process Slash Commands

```typescript
"command.execute.before": async (input, output) => {
  // input: { command: string, sessionID: string, arguments: string }
  // output: { parts: Part[] }
},
```

## Registration — How OpenCode Finds Your Plugin

### Method 1: Auto-Discovery (Recommended)

Place `.ts` or `.js` files in `.opencode/plugin/` or `.opencode/plugins/`:

```
your-project/
  .opencode/
    plugins/
      my-plugin.ts       # Auto-loaded, no config needed
```

### Method 2: opencode.json plugin Array

```json
{
  "plugin": [
    "my-plugin",                    // npm package (latest)
    "my-plugin@1.2.3",              // npm package (pinned)
    "./local-plugin.ts",            // Local file (relative to config)
    "file:///abs/path/plugin.js",   // Local file (absolute)
    ["my-plugin", { "debug": true }] // With options (passed as 2nd arg)
  ]
}
```

### Method 3: Global Plugins

Place in `~/.config/opencode/plugins/` for all projects.

### Load Order

Plugins load in this sequence (all hooks from all sources run in order):

1. **Global config** (`~/.config/opencode/opencode.json`) — npm plugins declared here
2. **Project config** (`opencode.json`) — npm plugins declared here
3. **Global plugin directory** (`~/.config/opencode/plugins/`) — local files
4. **Project plugin directory** (`.opencode/plugins/`) — local files

Duplicate npm packages (same name + version) load once. A local plugin and an npm plugin with similar names load separately.

## Configuration Verification

After creating or modifying a plugin:

```bash
# 1. Verify plugin loads (look for errors in startup)
opencode run "hello" --format json 2>&1 | head -20

# 2. Check tool is registered (custom tools appear in tool calls)
opencode run "Use my_tool with query=test" --format json --dangerously-skip-permissions

# 3. Verify hook fires (check stderr for console.log output)
```

**IMPORTANT:** Config is loaded once at startup. After saving plugin changes, **restart opencode**.

## Complete Minimal Plugin Template

See `references/plugin-template.ts` for a copy-paste starting point with all hook types commented out.

## Real-World Examples

### Example 1: Simple Custom Tool

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const MyPlugin: Plugin = async ({ $ }) => {
  return {
    tool: {
      count_files: tool({
        description: "Count files matching a glob pattern in the project",
        args: {
          pattern: tool.schema.string().describe("Glob pattern, e.g. 'src/**/*.ts'"),
          directory: tool.schema.string().optional().describe("Base directory"),
        },
        async execute(args) {
          const base = args.directory ?? "."
          const result = await $`rg --files ${base} -g ${args.pattern}`.quiet().nothrow()
          const count = result.stdout.toString().split("\n").filter(Boolean).length
          return `Found ${count} files matching '${args.pattern}' in ${base}`
        },
      }),
    },
  }
}
```

### Example 2: Tool Override with Fallback

Override a built-in tool (e.g. `read`) while keeping fallback behavior:

```typescript
import { type Plugin, tool } from "@opencode-ai/plugin"

export const ReadOverridePlugin: Plugin = async ({ $ }) => {
  const COMPRESSOR = "my-compressor" // hypothetical CLI tool

  async function compress(content: string): Promise<string | null> {
    try {
      const proc = Bun.spawn([COMPRESSOR, "--stdin"], {
        stdin: "pipe", stdout: "pipe", stderr: "pipe",
      })
      proc.stdin.write(content)
      proc.stdin.end()
      const exitCode = await proc.exited
      if (exitCode !== 0) return null
      return await new Response(proc.stdout).text()
    } catch { return null }
  }

  return {
    tool: {
      read: tool({
        description: "Read file (compressed via my-compressor for token savings)",
        args: {
          filePath: tool.schema.string().describe("Absolute file path"),
          offset: tool.schema.number().optional().describe("0-based line offset"),
          limit: tool.schema.number().optional().describe("Max lines"),
        },
        async execute(args) {
          // Try compression first
          const file = Bun.file(args.filePath)
          let text = await file.text()
          if (args.offset != null || args.limit != null) {
            const lines = text.split("\n")
            const start = args.offset ?? 0
            const end = args.limit != null ? start + args.limit : lines.length
            text = lines.slice(start, end).join("\n")
          }
          const compressed = await compress(text)
          return compressed ?? text  // Fallback to raw content
        },
      }),
    },
  }
}
```

### Example 3: .env File Protection

Block reading of sensitive files:

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const EnvProtection: Plugin = async () => {
  return {
    "tool.execute.before": async (input, output) => {
      if (input.tool === "read" && output.args.filePath.includes(".env")) {
        throw new Error("Do not read .env files")
      }
    },
  }
}
```

### Example 4: Session Notification

Send system notification when opencode finishes a task:

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export const NotificationPlugin: Plugin = async ({ $ }) => {
  return {
    event: async ({ event }) => {
      if (event.type === "session.idle") {
        // macOS notification via osascript
        await $`osascript -e 'display notification "Session completed!" with title "opencode"'`.nothrow()
      }
    },
  }
}
```

## Common Pitfalls

### 1. Bun.spawn vs Bun Shell Template Strings

**#1 cause of plugin failures.** Bun shell (`$` template) breaks multi-word args:

```typescript
// WRONG — breaks on Windows with multi-word args
const result = await $`my-tool ${cmd} ${args.join(" ")}`.quiet()

// CORRECT — bypasses shell entirely
const proc = Bun.spawn(["my-tool", cmd, ...args], {
  stdout: "pipe", stderr: "pipe",
})
const stdout = await new Response(proc.stdout).text()
```

### 2. Plugin vs MCP Conflict

If both a plugin override and MCP server register the same tool name, **MCP wins**. Remove conflicting MCP entries when using plugin tool overrides.

### 3. Missing Fallbacks

Always provide native fallback when wrapping external tools. External tools may not be installed:

```typescript
const compressed = await externalTool(args)
if (compressed) return compressed
return await nativeFallback(args)  // ALWAYS include this
```

### 4. Export Convention

Both named and default exports work. Named exports are the official convention:

```typescript
// PREFERRED — named export (official convention)
export const MyPlugin: Plugin = async ({ $ }) => {
  return { /* hooks */ }
}

// ALSO WORKS — default export
export default (async ({ $ }) => {
  return { /* hooks */ }
}) satisfies Plugin
```

### 5. Config Not Hot-Reloaded

Plugin changes require **restarting opencode**. Running sessions keep using already-loaded code.

### 6. Global vs Project Hook Order

Global hooks (`~/.config/opencode/plugins/`) run before project hooks (`.opencode/plugins/`). If a global hook modifies `output.args`, the project hook sees the already-modified value. Avoid conflicting hooks between scopes.

### 7. Windows Path Handling

```typescript
const normalizedPath = args.filePath.replace(/\\/g, "/")
```

Some CLI tools on Windows return Unix-style paths (`/c/Users/...`) that PowerShell can't execute. Detect and skip:

```typescript
const isUnixPath = /^\/[a-zA-Z]\//.test(result)
if (isUnixPath) return  // Skip on Windows
```

## Hook Decision Matrix

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

## npm Publishing (Optional)

To distribute your plugin as an npm package:

1. `package.json` must have `"main"` pointing to the plugin entry
2. Export a `PluginModule` with `server` field:

```typescript
import type { Plugin, PluginModule } from "@opencode-ai/plugin"

const MyPlugin: Plugin = async (input) => {
  return { /* hooks */ }
}

const module: PluginModule = {
  id: "my-plugin",
  server: MyPlugin,
}

export default MyPlugin
export { MyPlugin }
```

3. Users install via: `"plugin": ["your-npm-package"]`

## References

| File / URL | Description |
|-------------|-------------|
| `references/plugin-template.ts` | Copy-paste minimal template with all hooks |
| https://opencode.ai/docs/plugins/ | Official plugin documentation |
| https://opencode.ai/config.json | OpenCode config JSON Schema |
| `@opencode-ai/plugin` npm package | Plugin API TypeScript types |
| https://opencode.ai/docs/custom-tools/ | Official custom tools documentation |
