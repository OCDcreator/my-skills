---
name: lean-ctx-deploy
description: Guide for deploying lean-ctx token optimization into AI coding agents. Covers three integration modes — MCP server mode (Claude Code, Kiro, OpenCode, Cursor), CLI-redirect plugin mode (OpenCode), and Hybrid mode with shell hooks (Codex) — with project-level setup, cross-platform debugging (Windows + macOS), and verification. Includes battle-tested examples and test reports. This skill should be used when setting up lean-ctx in any agent, choosing between MCP vs plugin vs hybrid integration, writing OpenCode plugins that wrap CLI tools, deploying Codex hooks, or debugging lean-ctx integration issues on any platform.
---

# lean-ctx Deployment Guide

## Background

[lean-ctx](https://github.com/yvgude/lean-ctx) is a CLI-first token optimization tool (v3.4.7+) with 90+ compression patterns. It reduces token waste by compressing `read`, `grep`, `glob`, and `bash` outputs before they reach the LLM context window.

## Integration Modes

| Mode | How it works | Best for |
|------|-------------|----------|
| **MCP** (Mode A) | lean-ctx runs as MCP server, exposes 49 tools (ctx_read, ctx_search, etc.) | Agents with native MCP (Claude Code, Kiro, OpenCode, Cursor) |
| **CLI-redirect** (Mode B) | Plugin wraps built-in tools to call `lean-ctx` CLI, falls back to native | Agents with plugin/hook systems (OpenCode) |
| **Hybrid** (Mode C) | MCP for reads + Shell hooks for Bash compression | Codex CLI (officially recommended by lean-ctx) |

### When to Choose Which

- **MCP**: Zero-friction, just add config + rules. Works on Windows + macOS.
- **Plugin**: Fine-grained control over tool behavior.
- **Hybrid**: Best of both worlds — MCP tools for file reads, hooks intercept Bash commands and redirect to `lean-ctx -c`.
- **Claude Code**: Best-supported agent. Pure MCP (Mode A). Configure project-level `.claude/settings.local.json` + `.claude/rules/lean-ctx.md` manually (avoid `lean-ctx init` — it modifies global files).
- **OpenCode**: Both Mode A and B work. **Do NOT use both simultaneously** — agent prefers MCP tools over plugin overrides.
- **Codex**: Use Mode C (Hybrid). For project-level deployment, prefer committed `.codex/hooks.json` for hooks and keep `.codex/config.toml` local for MCP paths. Avoid `lean-ctx init --agent codex` when you want project-only setup, because it installs global Codex config.
- **Project-level > global**: Portable, commit-friendly, avoids sync conflicts.

---

## Mode A: MCP Server Deployment

### Prerequisites

```bash
lean-ctx --version   # v3.4.7+
which lean-ctx        # Must be in PATH
```

Install if missing: `cargo install lean-ctx` or `npm install -g lean-ctx`

### Steps

1. **Add MCP config** — see `references/mcp-config-examples.md` for complete snippets (OpenCode, Claude Code, Kiro, Cursor, Codex)
2. **Add agent rules** — the agent must be told to prefer lean-ctx tools over built-in tools; see `references/mcp-config-examples.md` for rules templates per agent
3. **Verify** — run `opencode run "Read file <some-file>" --format json --dangerously-skip-permissions` and check for `lean-ctx_ctx_read` in tool names

**Claude Code** is the best-supported agent (lean-ctx is developed with Claude Code). Configure project-level files manually: `.claude/settings.local.json` + `.claude/rules/lean-ctx.md`. See `references/mcp-config-examples.md` for complete Claude Code config with dual-platform examples.

### Platform Differences

Same config on Windows and macOS. Only binary path differs:
- Windows: `C:\Users\<user>\.cargo\bin\lean-ctx.exe`
- macOS: `/Users/<user>/.cargo/bin/lean-ctx`

Template approach for git: commit `.opencode.json.template`, `.gitignore` the actual config.

---

## Mode B: CLI-Redirect Plugin (OpenCode)

### Prerequisites

(Same as Mode A)

### Steps

1. **Create plugin directory**: `.opencode/plugins/lean-ctx.ts`
2. **Copy plugin code**: from `references/lean-ctx-opencode-plugin.ts` (battle-tested, works on Windows + macOS)
3. **Remove competing MCP**: delete `lean-ctx` from `mcpServers` in `.opencode/opencode.json` and `~/.config/opencode/opencode.json`
4. **Verify**: run 4-tool test below

### 6 Critical Pitfalls

See `references/plugin-pitfalls.md` for detailed code snippets:
1. **Bun.spawn > Bun shell** — template strings break multi-word args on all platforms
2. **bash hook Unix paths on Windows** — `hook rewrite-inline` returns `/c/Users/...`; must detect and skip
3. **glob pattern parsing** — `lean-ctx find` doesn't support `**/*.rs`; split into searchPath + leafPattern
4. **Always include native fallbacks** — lean-ctx might not be installed or might fail
5. **MCP + plugin conflict** — remove MCP when using plugin mode
6. **Global vs project plugins** — global hooks execute first and can break project hooks

### Verification Test

```bash
opencode run "Do these 4 tasks: \
  1) Read file src-tauri/src/main.rs \
  2) Grep for 'fn main' in src-tauri/src/ \
  3) Glob for all .rs files under src-tauri/src/commands/ \
  4) Run git status via bash. \
  Report results for each." \
  --format json --dangerously-skip-permissions
```

Expected:
- **read**: `main.rs [15L]` compressed header
- **grep**: `path/to/file.rs:3:fn main()` compact format
- **glob**: file list via `lean-ctx find`
- **bash**: native execution (Windows skips rewrite; macOS rewrites correctly)

---

## Mode C: Hybrid MCP + Shell Hooks (Codex)

Officially recommended by lean-ctx (`lean-ctx init --agent codex`). Combines MCP tools for file reads with shell hooks that intercept Bash commands.

Codex supports both repo-local `.codex/hooks.json` and inline `[hooks]` inside `.codex/config.toml`, and loads all matching hook sources. For project-level deployment, prefer `.codex/hooks.json` for hooks because it is portable, purpose-built, and can be committed without machine-specific paths. Keep `.codex/config.toml` for MCP server settings only.

### How It Works

1. **MCP server** provides `ctx_read`, `ctx_search`, `ctx_shell`, etc. via `[mcp_servers]`
2. **SessionStart hook** injects developer context telling Codex to prefer `lean-ctx -c` for shell commands
3. **PreToolUse hook** intercepts Bash calls matching lean-ctx compression rules, returns `exit 2` to block, suggests `lean-ctx -c <command>` replacement

### Prerequisites

```bash
lean-ctx --version   # v3.4.7+
codex --version      # v0.123.0+
```

Global config must have hooks enabled: `[features] codex_hooks = true`

### Steps (Project-Level)

1. **Ensure project is trusted first** — add `[projects."/path/to/project"] trust_level = "trusted"` to `~/.codex/config.toml`
2. **Keep global Codex lean-ctx config minimal** — leave `[features] codex_hooks = true`, but remove global lean-ctx hook definitions from `~/.codex/hooks.json` and remove inline global `[hooks.*]` entries if you are moving the workflow to one repo
3. **Create committed `.codex/hooks.json`** in project root — see `references/mcp-config-examples.md` for the portable Codex hooks file
4. **Create local `.codex/config.toml`** in project root for `[mcp_servers.lean-ctx]` only — keep it uncommitted if it contains machine-specific paths
5. **Verify hooks** — test manually (see below)
6. **Verify MCP** — run `codex exec "List all MCP tools starting with mcp__"`

### Manual Hook Verification

```bash
# Test SessionStart hook
echo '{"source":"startup","session_id":"test","cwd":"/path/to/project","hook_event_name":"SessionStart","model":"gpt-5.4"}' | lean-ctx hook codex-session-start
# Expected: exits 0, outputs lean-ctx usage instructions

# Test PreToolUse hook (intercepts Bash)
echo '{"tool_name":"Bash","tool_input":{"command":"git status"},"session_id":"test","cwd":"/path/to/project","hook_event_name":"PreToolUse","model":"gpt-5.4"}' | lean-ctx hook codex-pretooluse
# Expected: exits 2, outputs "Command should run via lean-ctx for compact output"
```

### Codex MCP Tool Names

Codex exposes lean-ctx MCP tools as `mcp__lean_ctx__.*`:
- `mcp__lean_ctx__.ctx_read`
- `mcp__lean_ctx__.ctx_search`
- `mcp__lean_ctx__.ctx_shell`
- `mcp__lean_ctx__.ctx_tree`
- `mcp__lean_ctx__.ctx_edit`
- `mcp__lean_ctx__.ctx_multi_read`
- etc.

### Platform Differences

| Aspect | Windows | macOS |
|--------|---------|-------|
| MCP command | `C:\Users\<user>\.cargo\bin\lean-ctx.exe` | `lean-ctx` (if in PATH) |
| Hook command | `lean-ctx hook codex-*` | `lean-ctx hook codex-*` |
| Hook config | `<repo>\.codex\hooks.json` | `<repo>/.codex/hooks.json` |
| MCP config | `<repo>\.codex\config.toml` | `<repo>/.codex/config.toml` |
| Trust path format | `C:\\Users\\...` (escaped) | `/Volumes/...` or `/Users/...` |

### Codex Test Results

| Platform | SessionStart hook | PreToolUse hook | MCP ctx_read | exec mode | Details |
|----------|-------------------|-----------------|--------------|-----------|---------|
| **Windows 11** | ✅ | ✅ blocks git status | ✅ returns compressed | ✅ works | Codex CLI 0.125.0 |
| **macOS** | ✅ outputs instructions | ✅ blocks git status | ✅ (API timeout unrelated) | ⚠️ API issue | Codex CLI 0.123.0 |

---

## Cross-Platform Test Results

| Platform | read | grep | glob | bash | Details |
|----------|------|------|------|------|---------|
| **Windows 11** | ✅ compressed | ✅ compact | ✅ find | ✅ native (skip rewrite) | OpenCode 1.14.x |
| **macOS** | ✅ cached | ✅ compact | ✅ find | ✅ rewrite works | OpenCode 1.14.39 |

Full macOS test output: `references/macos-test-result.txt`

**Same plugin file works on both platforms** — no platform-specific changes needed.

---

## Troubleshooting

### General
- **lean-ctx not found**: `which lean-ctx` or `Get-Command lean-ctx`. Install via cargo or npm.
- **Agent ignores lean-ctx tools**: MCP → check rules loaded; Plugin → check plugin loaded.

### MCP Mode
- **MCP not connecting**: Check JSON valid. On Windows, ensure lean-ctx in PATH for agent process.
- **Agent uses native read/grep**: Rules file missing or wrong location.
- **Both MCP and plugin showing**: Pick one mode, remove the other.

### Plugin Mode
- **Plugin not loading**: Check `.opencode/plugins/lean-ctx.ts` exists with valid TS. Check global plugins conflicting.
- **Bash fails on Windows**: Expected — rewrite skipped, runs natively.
- **Glob empty**: Split `**/*.rs` pattern before calling `lean-ctx find`. Check `rg --files` fallback.
- **Bun.spawn empty**: Verify lean-ctx in PATH. Use Bun.spawn (not shell template strings).

### Codex Hybrid Mode
- **Hooks not firing**: Check `[features] codex_hooks = true` in global `~/.codex/config.toml`. Check project is trusted. Verify the repo uses `.codex/hooks.json` or inline `[hooks]`, not an empty layer.
- **MCP tools not appearing**: Verify `.codex/config.toml` has `[mcp_servers.lean-ctx]`. Run `codex exec "List MCP tools"`.
- **PreToolUse doesn't block**: Hook only blocks commands matching lean-ctx compression rules (git, npm, cargo, etc.).
- **Mac Codex hangs in exec**: Likely API connection issue, not hooks. Test hooks manually first.
- **Trust prompt appears**: Add project path to `~/.codex/config.toml` under `[projects]`.
- **Hook runs twice**: Remove duplicate lean-ctx hooks from global `~/.codex/hooks.json` or inline global `[hooks.*]`, and avoid defining both `hooks.json` and inline `[hooks]` in the same project layer.

---

## References

| File | Contents |
|------|----------|
| `references/mcp-config-examples.md` | Complete MCP config + rules for OpenCode, Claude Code, Kiro, Cursor, Codex |
| `references/lean-ctx-opencode-plugin.ts` | Battle-tested plugin code (Windows + macOS, cross-platform) |
| `references/plugin-pitfalls.md` | 6 critical pitfalls with code snippets |
| `references/macos-test-result.txt` | macOS full test output and platform comparison |
