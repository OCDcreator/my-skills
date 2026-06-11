# OpenCode Plugin Pitfalls

Common mistakes and how to avoid them.

---

## 1. Bun.spawn vs Bun Shell Template Strings

**#1 cause of plugin failures.** Bun shell (`$` template) treats interpolated strings as single shell tokens, breaking multi-word args on all platforms.

```typescript
// WRONG — breaks multi-word args on Windows (and unreliable on macOS)
const result = await $`my-tool ${cmd} ${args.join(" ")}`.quiet()

// CORRECT — bypasses shell entirely, passes args as separate process arguments
const proc = Bun.spawn(["my-tool", cmd, ...args], {
  stdout: "pipe", stderr: "pipe",
})
const stdout = await new Response(proc.stdout).text()
```

**Rule:** Use `Bun.spawn` for any external CLI tool. Use `$` template only for simple, single-arg commands.

---

## 2. Plugin vs MCP Conflict

If both a plugin tool override and an MCP server register the same tool name, **MCP wins**. The plugin tool becomes invisible.

**Fix:** Remove the conflicting MCP entry from `opencode.json` when using plugin tool overrides:

```jsonc
// .opencode/opencode.json — REMOVE conflicting MCP entry
{
  "mcp": {
    // "lean-ctx": { ... }  ← DELETE this when using plugin mode
  }
}
```

---

## 3. Missing Fallbacks

Always provide native fallback when wrapping external tools. The external tool may not be installed, may fail, or return empty output:

```typescript
// read fallback
const compressed = await externalTool(["read", path])
if (compressed) return compressed
return await Bun.file(path).text()  // ALWAYS include this

// grep fallback
const compressed = await externalTool(["grep", pattern, searchPath])
if (compressed) return compressed
const result = await $`rg ${pattern} ${searchPath}`.quiet().nothrow()
return String(result.stdout) || "No matches found."

// glob fallback
const compressed = await externalTool(["find", leafPattern, basePath])
if (compressed) return compressed
const result = await $`rg --files ${basePath} -g ${rawPattern}`.quiet().nothrow()
return String(result.stdout) || "No files matched."
```

---

## 4. Export Convention

Both named and default exports work. Named exports are the official convention:

```typescript
// PREFERRED — named export (official convention from opencode.ai/docs/plugins)
export const MyPlugin: Plugin = async ({ $ }) => {
  return { /* hooks */ }
}

// ALSO WORKS — default export
export default (async ({ $ }) => {
  return { /* hooks */ }
}) satisfies Plugin
```

**Important:** Export must be a **function**, not a plain object:

```typescript
// WRONG — plain object
export default { tool: { ... } }

// CORRECT — function returning Hooks
export const MyPlugin: Plugin = async ({ $ }) => {
  return { tool: { ... } }
}
```

---

## 5. Config Not Hot-Reloaded

Plugin code is loaded once at startup. After saving changes:

- **Restart opencode** — running sessions keep using already-loaded code
- No hot-reload mechanism exists

---

## 6. Global vs Project Hook Order

Global hooks (`~/.config/opencode/plugins/`) run before project hooks (`.opencode/plugins/`). If a global hook modifies `output.args`, the project hook sees the already-modified value.

**Fix:** Avoid conflicting hooks between scopes. Keep project-specific logic in project plugins only.

---

## 7. Windows Path Handling

Cross-platform plugins must normalize paths:

```typescript
const normalizedPath = args.filePath.replace(/\\/g, "/")
```

Some CLI tools on Windows return Unix-style paths (`/c/Users/...`) that PowerShell can't execute. Detect and skip:

```typescript
const isUnixPath = /^\/[a-zA-Z]\//.test(result)
if (isUnixPath) return  // Skip rewrite on Windows
```

---

## 8. Logging Convention

Use `client.app.log()` instead of `console.log` for structured, visible logging:

```typescript
// WRONG — console.log may not be visible in all contexts
console.log("Plugin initialized")

// CORRECT — structured logging via SDK client
await client.app.log({
  body: { service: "my-plugin", level: "info", message: "Plugin initialized" }
})
```
