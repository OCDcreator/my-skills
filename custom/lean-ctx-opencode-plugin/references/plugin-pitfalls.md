# lean-ctx Plugin Pitfalls (OpenCode Mode B)

Key implementation pitfalls and code snippets for the CLI-redirect plugin mode.

---

## Pitfall 1: Bun.spawn vs Bun Shell Template Strings

**Affects: All platforms. This is the #1 cause of plugin failures.**

```typescript
// ❌ WRONG — Bun shell breaks multi-word args on Windows (and unreliable on macOS)
const result = await $`lean-ctx ${subCmd} ${args.join(" ")}`.quiet()

// ✅ CORRECT — Bun.spawn passes args reliably across all platforms
const proc = Bun.spawn(["lean-ctx", ...args], { stdout: "pipe", stderr: "pipe" })
const exitCode = await proc.exited
const stdout = await new Response(proc.stdout).text()
```

**Why**: Bun shell template strings (`$\`cmd\``) treat the entire interpolated string as a single shell token. When `args` contains spaces or multiple arguments, they get mangled. `Bun.spawn(["lean-ctx", ...args])` bypasses the shell entirely and passes each arg as a separate process argument.

---

## Pitfall 2: bash Hook Unix-Style Paths on Windows

**Affects: Windows only. macOS works correctly.**

On Windows, `lean-ctx hook rewrite-inline` returns Unix-style paths like `/c/Users/lt/.cargo/bin/lean-ctx.exe`. PowerShell cannot execute these.

```typescript
const rewritten = await leanCtx(["hook", "rewrite-inline", command])
if (rewritten && rewritten !== command) {
  // Detect Unix-style drive letter paths (Windows only)
  const isUnixPath = /^\/[a-zA-Z]\//.test(rewritten)
  if (isUnixPath) return  // Skip rewrite on Windows

  output.args.command = rewritten
}
```

**Result**: On Windows, bash commands run natively without lean-ctx compression. On macOS, the rewrite works correctly.

---

## Pitfall 3: glob Pattern Parsing

**Affects: All platforms.**

`lean-ctx find` does NOT support recursive glob patterns like `**/*.rs`. Split the pattern before calling:

```typescript
// "src-tauri/src/commands/**/*.rs" →
//   searchPath = "src-tauri/src/commands/"
//   leafPattern = "*.rs"
const parts = rawPattern.split("/")
const leafPattern = parts[parts.length - 1] || "*"
if (parts.length > 1) {
  const patternDir = parts.slice(0, -1).join("/").replace(/\*\*\/?/g, "")
  basePath = basePath === "." ? patternDir : `${basePath}/${patternDir}`
}

const compressed = await leanCtx(["find", leafPattern, basePath])
```

---

## Pitfall 4: Always Include Fallbacks

lean-ctx might not be installed, might fail, or return empty output. Every tool override must have a native fallback:

```typescript
// read fallback
const compressed = await leanCtx(["read", path])
if (compressed) return compressed
return await Bun.file(path).text()

// grep fallback
const compressed = await leanCtx(["grep", pattern, searchPath])
if (compressed) return compressed
const result = await $`rg ${pattern} ${searchPath}`.quiet().nothrow()
return String(result.stdout) || "No matches found."

// glob fallback
const compressed = await leanCtx(["find", leafPattern, basePath])
if (compressed) return compressed
const result = await $`rg --files ${basePath} -g ${rawPattern}`.quiet().nothrow()
return String(result.stdout) || "No files matched."
```

---

## Pitfall 5: MCP + Plugin Conflict

**Affects: All platforms.**

If lean-ctx MCP is also configured in `opencode.json`, OpenCode will prefer MCP tools over plugin tool overrides. The plugin becomes invisible.

**Fix**: Remove lean-ctx from `mcpServers` in both project and global `opencode.json` when using plugin mode.

```jsonc
// .opencode/opencode.json — REMOVE lean-ctx from mcpServers
{
  "mcp": {
    // "lean-ctx": { ... }  ← DELETE this when using plugin mode
    "gitnexus": { ... }       // Keep other MCP servers
  }
}
```

---

## Pitfall 6: Global vs Project Plugin Conflicts

**Affects: All platforms.**

OpenCode loads global plugins (`~/.config/opencode/plugins/`) then project plugins (`.opencode/plugins/`). Hooks execute in order — global hooks run first and can silently override project-level logic.

**Fix**: Remove any conflicting global plugins. Keep lean-ctx plugin at project level only.

---

## Complete Plugin Code

See `lean-ctx-opencode-plugin.ts` in this directory for the full, battle-tested implementation.
