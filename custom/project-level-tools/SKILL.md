---
name: project-level-tools
description: "Configure GitNexus and lean-ctx at the PROJECT LEVEL instead of globally. Use this skill whenever the user mentions project-level MCP setup, per-project configuration, isolating tools to a repo, or says anything like 'don''t install globally', 'project level only', 'per project', 'mcp setup', 'gitnexus setup', 'lean-ctx setup'. Also trigger when the user wants code intelligence, context compression, auto-update constraints after code changes, or is setting up a new machine (Windows or Mac). Trigger even if the user doesn''t explicitly name GitNexus or lean-ctx but mentions wanting smarter code understanding or token savings in their project."
compatibility: opencode
---

# Project-Level MCP & Tool Setup

Configure GitNexus (code intelligence) and lean-ctx (token compression) at the project level, with auto-update constraints.
Works on both Windows (with WSL workaround) and macOS (native).

## What This Skill Covers

- Migrate MCP servers from global config to project-level for **OpenCode** (`.opencode/opencode.json`) and **Codex** (`.codex/config.toml`)
- Install GitNexus skills locally under `.opencode/skills/` (OpenCode) or `.claude/skills/` (Claude Code / Codex)
- Create cross-platform scripts to check tool freshness and auto-update indexes
- Wire constraints into `package.json`, `AGENTS.md`, and git hooks
- Handle Windows-specific issues (LadybugDB WAL incompatibility via WSL)
- Keep platform-specific configs out of git/Syncthing to avoid sync conflicts

## When to Use

- User says "don''t install globally" or "project level only"
- User wants GitNexus on a new project
- User wants lean-ctx isolated per project
- User asks to add constraints so indexes update after code changes
- User mentions code intelligence / context compression setup
- User is setting up on a new machine (Windows or Mac)

## Prerequisites

```bash
lean-ctx --version    # Should show 3.x.x
gitnexus --version    # Should show 1.x.x
```

If missing:
```bash
cargo install lean-ctx
npm install -g gitnexus
```

On Windows, also verify WSL: `wsl -l -v`

## Workflow

### Step 1: Assess Current State

Read the global OpenCode config to see what''s currently installed globally:
```bash
cat ~/.config/opencode/opencode.json
```

Look for `mcp` entries with `lean-ctx` and/or `gitnexus`.

### Step 2: Remove Global MCP Entries

Edit `~/.config/opencode/opencode.json` and remove `lean-ctx` and `gitnexus` MCP entries. Leave other MCPs untouched.

**Also check and clean other agents'' global configs:**
- `~/.cursor/mcp.json` — remove lean-ctx/gitnexus
- `~/.codex/config.toml` — remove `[mcp_servers.lean-ctx]` and `[mcp_servers.gitnexus]`
- `~/.claude/settings.json` — remove GitNexus hooks
- `~/.codeium/windsurf/mcp_config.json` — remove if present

### Step 3: Create Project-Level MCP Config

**Critical rule:** Platform-specific config files must NOT be committed to git. Use the template approach: commit a `.template` file, create the actual config locally on each machine.

#### OpenCode (`.opencode/opencode.json`)

Create `.opencode/opencode.json.template` (committed to git):
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lean-ctx": {
      "type": "local",
      "command": ["lean-ctx"],
      "enabled": true
    },
    "gitnexus": {
      "type": "local",
      "command": ["gitnexus", "mcp"],
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

Then create `.opencode/opencode.json` locally (do not commit):

**Windows:**
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lean-ctx": {
      "type": "local",
      "command": ["lean-ctx"],
      "enabled": true,
      "environment": {
        "LEAN_CTX_DATA_DIR": "C:\Users\<USERNAME>\.config\lean-ctx"
      }
    },
    "gitnexus": {
      "type": "local",
      "command": [
        "wsl", "-d", "Ubuntu", "-e", "bash", "-lc",
        "cd \"/mnt/c/<WSL_PATH>\" && npx -y gitnexus@<VERSION> mcp"
      ],
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

**macOS:**
```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lean-ctx": {
      "type": "local",
      "command": ["lean-ctx"],
      "enabled": true,
      "environment": {
        "LEAN_CTX_DATA_DIR": "/Users/<USERNAME>/.config/lean-ctx"
      }
    },
    "gitnexus": {
      "type": "local",
      "command": ["gitnexus", "mcp"],
      "enabled": true,
      "timeout": 15000
    }
  }
}
```

#### Codex (`.codex/config.toml`)

Create `.codex/config.toml.template` (committed to git):
```toml
# Copy to .codex/config.toml locally. Do NOT commit the local copy.

# Windows:
# [mcp_servers.lean-ctx]
# command = "C:\Users\<USERNAME>\.cargo\bin\lean-ctx.exe"
# [mcp_servers.gitnexus]
# command = "cmd"
# args = ["/c", "npx", "-y", "gitnexus@latest", "mcp"]

# macOS:
# [mcp_servers.lean-ctx]
# command = "lean-ctx"
# [mcp_servers.gitnexus]
# command = "npx"
# args = ["-y", "gitnexus@latest", "mcp"]
```

Then create `.codex/config.toml` locally (do not commit), uncommenting the appropriate platform section.

**Why WSL for GitNexus on Windows?** GitNexus uses LadybugDB which has WAL corruption issues on Windows native filesystem. The index must be built and served from WSL. On macOS, GitNexus runs natively without issues.

### Step 4: Copy GitNexus Skills to Project

```bash
# Find source path
# Windows: %APPDATA%/npm/node_modules/gitnexus/skills
# macOS: $(npm root -g)/gitnexus/skills

mkdir -p .opencode/skills
cp "<SRC>/gitnexus-guide.md" .opencode/skills/gitnexus-guide/SKILL.md
cp "<SRC>/gitnexus-exploring.md" .opencode/skills/gitnexus-exploring/SKILL.md
cp "<SRC>/gitnexus-impact-analysis.md" .opencode/skills/gitnexus-impact-analysis/SKILL.md
cp "<SRC>/gitnexus-debugging.md" .opencode/skills/gitnexus-debugging/SKILL.md
cp "<SRC>/gitnexus-refactoring.md" .opencode/skills/gitnexus-refactoring/SKILL.md
cp "<SRC>/gitnexus-cli.md" .opencode/skills/gitnexus-cli/SKILL.md
cp "<SRC>/gitnexus-pr-review.md" .opencode/skills/gitnexus-pr-review/SKILL.md
```

Update stale-index references in copied skills from `npx gitnexus analyze` to `npm run update:gitnexus`.

### Step 5: Create Scripts

Create three scripts in `scripts/`:

**`check-gitnexus-freshness.mjs`:**
```javascript
#!/usr/bin/env node
import { execSync } from "child_process";
import { existsSync, readFileSync } from "fs";

const meta = existsSync(".gitnexus/meta.json")
  ? JSON.parse(readFileSync(".gitnexus/meta.json", "utf-8"))
  : null;
const head = execSync("git rev-parse HEAD", { encoding: "utf-8" }).trim();

if (!meta || meta.lastCommit !== head) {
  console.error("❌ GitNexus index stale. Run: npm run update:gitnexus");
  process.exit(1);
}
console.log("✅ GitNexus index fresh");
```

**`update-gitnexus.mjs`:**
```javascript
#!/usr/bin/env node
import { execSync } from "child_process";

const FORCE = process.argv.includes("--force") ? " --force" : "";
const IS_WINDOWS = process.platform === "win32";

if (IS_WINDOWS) {
  const distro = process.env.GITNEXUS_WSL_DISTRO || "Ubuntu";
  const wslPath = execSync(`wsl -d ${distro} -e wslpath -u "${process.cwd()}"`, { encoding: "utf-8" }).trim();
  execSync(`wsl -d ${distro} -e bash -lc "cd '${wslPath}' && npx -y gitnexus@latest analyze${FORCE}"`, { stdio: "inherit" });
} else {
  execSync(`npx -y gitnexus@latest analyze${FORCE}`, { stdio: "inherit" });
}
```

**`check-lean-ctx.mjs`:**
```javascript
#!/usr/bin/env node
import { execSync } from "child_process";

try {
  const v = execSync("lean-ctx --version", { encoding: "utf-8" }).trim();
  console.log(`✅ lean-ctx ${v}`);
} catch {
  console.error("❌ lean-ctx not found. Install: cargo install lean-ctx");
  process.exit(1);
}
```

### Step 6: Wire Into package.json

```json
{
  "scripts": {
    "check:gitnexus-freshness": "node scripts/check-gitnexus-freshness.mjs",
    "check:lean-ctx": "node scripts/check-lean-ctx.mjs",
    "update:gitnexus": "node scripts/update-gitnexus.mjs",
    "verify": "npm run check:gitnexus-freshness && npm run check:lean-ctx && <rest>"
  }
}
```

### Step 7: Update AGENTS.md

Add lean-ctx usage guide, GitNexus usage guide, and the update constraint rule (after every code change, run `npm run update:gitnexus`).

### Step 8: Add Pre-Commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/sh
node scripts/check-gitnexus-freshness.mjs || {
  echo "❌ Commit blocked: index stale. Run: npm run update:gitnexus"
  exit 1
}
```
`chmod +x .git/hooks/pre-commit`

### Step 9: Configure gitignore and Syncthing

`.gitignore`:
```gitignore
# Platform-specific MCP configs
.opencode/opencode.json
.codex/config.toml

# Local git hooks
.git/hooks/pre-commit

# GitNexus index
.gitnexus

# Syncthing
.stfolder
.stignore.local
```

`.stignore`:
```
.gitnexus
.opencode/opencode.json
.codex/config.toml
.git/hooks/pre-commit
.stfolder
.stignore.local
.DS_Store
Thumbs.db
```

### Step 10: Build Initial Index

```bash
npm run update:gitnexus
```

### Step 11: Verify

```bash
npm run verify
node scripts/check-gitnexus-freshness.mjs
node scripts/check-lean-ctx.mjs
```

## Critical Gotchas (From Real Usage)

### 1. Double-Check the Target Project

**Before starting, confirm which project the user wants to configure.** Ask explicitly: "Which project should I configure?" Common projects:
- `skills-manager-system`
- `opencodian`
- Other repos under `custom-project/`

### 2. Platform-Specific Configs Must Stay Out of Git

`.opencode/opencode.json` and `.codex/config.toml` contain absolute paths (Windows `C:` vs macOS `/Users/`). If committed, they cause:
- Constant git conflicts between Windows and Mac
- Syncthing overwriting the correct config with the wrong platform''s paths
- Agents failing to start because paths don''t exist

**Always:**
- Commit only the `.template` file
- Add the actual config file to `.gitignore`
- Create the actual config locally on each machine

### 3. GitNexus Index Commit Mismatch After Pull/Merge

After `git pull` or `git merge`, the GitNexus index may be stale even if you didn''t change code (the merge commit changed HEAD). Always run `npm run update:gitnexus` after pulling.

### 4. Windows: Never Run `npx gitnexus analyze` Natively

Always use `npm run update:gitnexus` (which routes through WSL). Running natively on Windows corrupts the LadybugDB WAL.

### 5. Codex Project Trust

Codex only loads `.codex/config.toml` when the project is trusted. Check `~/.codex/config.toml`:
```toml
[projects."/path/to/project"]
trust_level = "trusted"
```

## Verification Checklist

### OpenCode
- [ ] Global `~/.config/opencode/opencode.json` no longer has `lean-ctx` or `gitnexus` MCP entries
- [ ] Project `.opencode/opencode.json` has both MCP entries (platform-specific, not in git)
- [ ] `.opencode/skills/` contains 7 GitNexus skills

### Codex (if configured)
- [ ] Project `.codex/config.toml` has both MCP entries (platform-specific, not in git)
- [ ] `.codex/config.toml.template` is committed to git
- [ ] `.gitignore` excludes `.codex/config.toml`
- [ ] Codex project trust level is `trusted`

### Shared
- [ ] `.gitignore` excludes `.opencode/opencode.json`, `.codex/config.toml`, `.gitnexus/`
- [ ] `.stignore` excludes platform-specific files
- [ ] `npm run check:gitnexus-freshness` passes
- [ ] `npm run check:lean-ctx` passes
- [ ] `npm run update:gitnexus` completes without errors
- [ ] `.gitnexus/meta.json` `lastCommit` matches `git rev-parse HEAD`
- [ ] `npm run verify` passes
- [ ] Git commit triggers pre-commit hook

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GitNexus index stale after update | Restart agent to reload MCP server |
| `wslpath` not found (Windows) | `wsl --install -d Ubuntu` |
| `gitnexus` not found (macOS) | Add npm global bin to PATH or symlink to `/opt/homebrew/bin/` |
| lean-ctx hook not active | Windows: `. $PROFILE`; macOS: `source ~/.zshrc` |
| `npx gitnexus analyze` fails on Windows | Never run natively — always use `npm run update:gitnexus` |
| Pre-commit hook not running | `chmod +x .git/hooks/pre-commit` |
| Syncthing overwrites `.opencode/opencode.json` | Add to `.stignore` on both machines |
| Sync conflict files (`.sync-conflict-*`) | Restore from git, ensure `.stignore` configured |
| Codex not loading project MCP | Check `~/.codex/config.toml` project trust level |
| **Configured wrong project** | `git reset --hard HEAD~1` to revert, then confirm target project |
| **Git conflict on `.codex/config.toml`** | File is platform-specific; keep local version, don''t merge |

## References

- lean-ctx: https://github.com/yvgude/lean-ctx
- GitNexus: https://github.com/abhigyanpatwari/gitnexus
- OpenCode MCP: https://opencode.ai/docs/zh-cn/mcp-servers/
- Codex MCP: https://developers.openai.com/codex/mcp
