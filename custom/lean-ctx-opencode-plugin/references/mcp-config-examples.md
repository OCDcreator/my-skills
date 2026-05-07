# lean-ctx MCP Config Examples

Complete config snippets for each supported agent. Copy the relevant section into your project.

---

## OpenCode

### `.opencode/opencode.json` (project-level)

Basic:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lean-ctx": {
      "type": "local",
      "command": ["lean-ctx"],
      "enabled": true
    }
  }
}
```

With macOS data directory override:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lean-ctx": {
      "type": "local",
      "command": ["lean-ctx"],
      "enabled": true,
      "environment": {
        "LEAN_CTX_DATA_DIR": "/Users/<user>/.config/lean-ctx"
      }
    }
  }
}
```

### `.opencode/opencode.json.template` (committed to git)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lean-ctx": {
      "type": "local",
      "command": ["lean-ctx"],
      "enabled": true
    }
  }
}
```

First clone: `cp .opencode/opencode.json.template .opencode/opencode.json`

Add to `.gitignore`: `.opencode/opencode.json`

### OpenCode MCP tool naming

lean-ctx MCP tools appear as `lean-ctx_ctx_read`, `lean-ctx_ctx_search`, `lean-ctx_ctx_shell`, `lean-ctx_ctx_edit`, etc. The agent sees all 49 tools and must be instructed to prefer them over built-in `read`, `grep`, `glob`.

### OpenCode Rules

**Option 1: AGENTS.md snippet** (add to project's AGENTS.md):
```markdown
## lean-ctx — Context Engineering Layer

PREFER lean-ctx MCP tools over native equivalents for token savings:

| PREFER | OVER | Why |
|--------|------|-----|
| `lean-ctx_ctx_read(path, mode)` | `read` / `cat` | Cached, 10 read modes, re-reads ~13 tokens |
| `lean-ctx_ctx_shell(command)` | `bash` / `shell` | Pattern compression for git/npm/cargo output |
| `lean-ctx_ctx_search(pattern, path)` | `grep` / `rg` | Compact, token-efficient results |
| `lean-ctx_ctx_tree(path, depth)` | `glob` / `ls` | Compact directory maps |

ctx_read modes: auto, full, map, signatures, diff, aggressive, entropy, task, reference, lines:N-M
```

**Option 2: Skill file** (`.opencode/skills/lean-ctx/SKILL.md`):
```markdown
---
name: lean-ctx
description: Use lean-ctx MCP tools for token-optimized file reading, searching, and shell output compression.
---

PREFER lean-ctx MCP tools over native equivalents for token savings:

| PREFER | OVER | Why |
|--------|------|-----|
| `lean-ctx_ctx_read(path, mode)` | `read` | Cached, 10 read modes |
| `lean-ctx_ctx_shell(command)` | `bash` | Pattern compression |
| `lean-ctx_ctx_search(pattern, path)` | `grep` | Compact results |
| `lean-ctx_ctx_tree(path, depth)` | `glob` / `ls` | Compact directory maps |

ctx_read modes: auto, full, map, signatures, diff, aggressive, entropy, task, reference, lines:N-M
```

---

## Claude Code

lean-ctx 对 Claude Code 支持最好（lean-ctx 本身用 Claude Code 开发），使用纯 MCP 模式（Mode A）。

> **Note**: Prefer manual project-level config below. Avoid `lean-ctx init --agent claude` as it modifies global files.

### Steps (project-level manual setup)

1. 创建 `.claude/settings.local.json`（MCP server 配置）
2. 创建 `.claude/rules/lean-ctx.md`（工具偏好规则）

### `.claude/settings.local.json` (project-level)

Windows:
```json
{
  "mcpServers": {
    "lean-ctx": {
      "command": "C:\\Users\\<user>\\.cargo\\bin\\lean-ctx.exe",
      "args": []
    }
  }
}
```

macOS:
```json
{
  "mcpServers": {
    "lean-ctx": {
      "command": "lean-ctx",
      "args": []
    }
  }
}
```

> `settings.local.json` 不提交到 git（已加入默认 `.gitignore`）。如需团队共享，用 `settings.json`。

### `.claude/rules/lean-ctx.md` (project-level rules)

```markdown
# lean-ctx — Context Engineering Layer
<!-- lean-ctx-rules-v9 -->

PREFER lean-ctx MCP tools over native equivalents for token savings:

| PREFER | OVER | Why |
|--------|------|-----|
| `ctx_read(path, mode)` | `Read` / `cat` | Cached, 10 read modes, re-reads ~13 tokens |
| `ctx_shell(command)` | `Shell` / `bash` | Pattern compression for git/npm/cargo output |
| `ctx_search(pattern, path)` | `Grep` / `rg` | Compact, token-efficient results |
| `ctx_tree(path, depth)` | `glob` / `ls` | Compact directory maps |

ctx_read modes: auto, full, map, signatures, diff, aggressive, entropy, task, reference, lines:N-M
```

### `CLAUDE.md` or `AGENTS.md` snippet (optional, stronger enforcement)

```markdown
## lean-ctx — Context Engineering Layer

PREFER lean-ctx MCP tools over native equivalents for token savings:

| PREFER | OVER | Why |
|--------|------|-----|
| `ctx_read(path, mode)` | `Read` / `cat` | Cached, 10 read modes, re-reads ~13 tokens |
| `ctx_shell(command)` | `Shell` / `bash` | Pattern compression for git/npm/cargo output |
| `ctx_search(pattern, path)` | `Grep` / `rg` | Compact, token-efficient results |
| `ctx_tree(path, depth)` | `glob` / `ls` | Compact directory maps |

ctx_read modes: auto, full, map, signatures, diff, aggressive, entropy, task, reference, lines:N-M
```

### Claude Code MCP Tool Names

Claude Code 直接使用 lean-ctx 工具名（无前缀）：
- `ctx_read` — cached file reads (10 modes)
- `ctx_search` — compact grep results
- `ctx_shell` — compressed shell output
- `ctx_tree` — directory maps
- `ctx_edit` — search-and-replace edit
- `ctx_multi_read` — batch file reads
- `ctx_session` — cross-session memory (CCP)
- `ctx_knowledge` — persistent project knowledge
- `ctx_discover_tools` — tool discovery
- `ctx_call` — call any ctx_* tool by name
- ...and 46 more tools (49 total)

### Platform Differences

| Aspect | Windows | macOS |
|--------|---------|-------|
| Binary path | `C:\Users\<user>\.cargo\bin\lean-ctx.exe` | `/Users/<user>/.cargo/bin/lean-ctx` |
| MCP command | Full `.exe` path recommended | `lean-ctx` (if in PATH) |
| Rules location | `.claude/rules/lean-ctx.md` | Same |
| Settings file | `.claude/settings.local.json` | Same |
| Shell hook | Auto-installed by `lean-ctx setup` | Same |

### Verification

Claude Code 启动时会自动加载 MCP server。检查方法：
1. 启动 Claude Code 后，输入 `/mcp` 查看已连接的 MCP server
2. 确认 `lean-ctx` 在列表中，状态为 connected
3. 让 Claude 读取一个文件，确认它使用 `ctx_read` 而非原生 `Read`

---

## Kiro

### `.kiro/steering/lean-ctx.md`

```markdown
# lean-ctx — Context Engineering Layer

PREFER lean-ctx MCP tools over native equivalents for token savings:

| PREFER | OVER | Why |
|--------|------|-----|
| `ctx_read(path, mode)` | `Read` / `cat` | Cached, 10 read modes, re-reads ~13 tokens |
| `ctx_shell(command)` | `Shell` / `bash` | Pattern compression for git/npm/cargo output |
| `ctx_search(pattern, path)` | `Grep` / `rg` | Compact, token-efficient results |

ctx_read modes: auto, full, map, signatures, diff, aggressive, entropy, task, reference, lines:N-M
```

Reference lean-ctx as a local MCP server in the Kiro config format.

---

## Cursor

### `~/.cursor/mcp.json` (user-level)

```json
{
  "mcpServers": {
    "lean-ctx": {
      "command": "lean-ctx",
      "args": []
    }
  }
}
```

---

## Codex CLI (Hybrid: MCP + Shell Hooks)

lean-ctx officially recommends **Hybrid mode** for Codex: MCP for file reads + hooks for Bash compression.

### `.codex/config.toml` (project-level) — Windows

```toml
[mcp_servers."lean-ctx"]
command = "C:\\Users\\<user>\\.cargo\\bin\\lean-ctx.exe"
args = []

[[hooks.SessionStart]]
matcher = "startup|resume|clear"

[[hooks.SessionStart.hooks]]
type = "command"
command = "lean-ctx hook codex-session-start"
timeout = 15

[[hooks.PreToolUse]]
matcher = "Bash"

[[hooks.PreToolUse.hooks]]
type = "command"
command = "lean-ctx hook codex-pretooluse"
timeout = 15
```

### `.codex/config.toml` (project-level) — macOS

```toml
[mcp_servers.lean-ctx]
command = "lean-ctx"

[[hooks.SessionStart]]
matcher = "startup|resume|clear"

[[hooks.SessionStart.hooks]]
type = "command"
command = "lean-ctx hook codex-session-start"
timeout = 15

[[hooks.PreToolUse]]
matcher = "Bash"

[[hooks.PreToolUse.hooks]]
type = "command"
command = "lean-ctx hook codex-pretooluse"
timeout = 15
```

### `~/.codex/config.toml` (global) — Required settings

```toml
[features]
codex_hooks = true

# Must add project to trusted list for project-level hooks to load:
[projects."/path/to/your/project"]
trust_level = "trusted"
```

### Codex Rules (AGENTS.md snippet)

Codex uses project `AGENTS.md` for agent instructions. Add:

```markdown
## lean-ctx — Context Engineering Layer

PREFER lean-ctx MCP tools over native equivalents for token savings:

| PREFER | OVER | Why |
|--------|------|-----|
| `mcp__lean_ctx__.ctx_read(path, mode)` | Read / cat | Cached, 10 read modes |
| `mcp__lean_ctx__.ctx_search(pattern, path)` | grep / rg | Compact results |
| `mcp__lean_ctx__.ctx_shell(command)` | Bash | Pattern compression |
| `mcp__lean_ctx__.ctx_tree(path, depth)` | glob / ls | Compact directory maps |

For Bash commands that get blocked by lean-ctx hooks, rerun with the exact command suggested by the hook.
```

### Quick Setup via lean-ctx CLI

```bash
# Auto-setup (installs global hooks + MCP + rules):
lean-ctx init --agent codex

# Or project-level only (add hooks to project .codex/config.toml):
# See config snippets above
```

### Verification

```bash
# Test hooks manually:
echo '{"source":"startup","session_id":"test","cwd":"$(pwd)","hook_event_name":"SessionStart","model":"gpt-5.4"}' | lean-ctx hook codex-session-start

echo '{"tool_name":"Bash","tool_input":{"command":"git status"},"session_id":"test","cwd":"$(pwd)","hook_event_name":"PreToolUse","model":"gpt-5.4"}' | lean-ctx hook codex-pretooluse

# Test MCP tools via Codex exec:
codex exec "List all MCP tools starting with mcp__ and use ctx_read to read a file"
```

---

## Platform Differences

| Aspect | Windows | macOS |
|--------|---------|-------|
| lean-ctx binary | `C:\Users\<user>\.cargo\bin\lean-ctx.exe` | `/Users/<user>/.cargo/bin/lean-ctx` |
| Data directory | `%APPDATA%\lean-ctx` or default | `~/.config/lean-ctx` or override |
| Config location | Same (project-level) | Same |
| Codex MCP command | Full `.exe` path recommended | `lean-ctx` (if in PATH) |
| Codex trust path | `C:\\Users\\...` (escaped backslashes) | `/Users/...` or `/Volumes/...` |
| Known issues | None specific to MCP mode | None |
