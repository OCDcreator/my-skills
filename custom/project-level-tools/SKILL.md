---
name: project-level-tools
description: "Use when the user wants to configure GitNexus, lean-ctx, or any MCP tools/skills at the project level instead of globally. Triggers on phrases like 'project level', 'project-level', 'don't install globally', 'per project', 'mcp setup', 'gitnexus setup', 'lean-ctx setup', or when the user wants to isolate tool configurations to a specific repository. Also triggers when the user mentions adding constraints so tools update after code changes, or when setting up on a new machine (Windows or Mac)."
compatibility: opencode
---

# Project-Level MCP & Tool Setup

Configure GitNexus and lean-ctx at the project level, with auto-update constraints.
Works on both Windows (with WSL workaround) and macOS (native).

## What This Skill Covers

- Migrate MCP servers from global config to project-level for **OpenCode** (`.opencode/opencode.json`) and **Codex** (`.codex/config.toml`)
- Install GitNexus skills locally under `.opencode/skills/` (OpenCode) or `.claude/skills/` (Claude Code / Codex)
- Create cross-platform scripts to check tool freshness and auto-update indexes
- Wire constraints into `package.json`, `AGENTS.md`, and git hooks
- Handle Windows-specific issues (LadybugDB WAL incompatibility via WSL)
- Keep platform-specific configs out of git/Syncthing to avoid sync conflicts

## When to Use

- User says "don't install globally" or "project level only"
- User wants GitNexus on a new project
- User wants lean-ctx isolated per project
- User asks to add constraints so indexes update after code changes
- User mentions code intelligence / context compression setup
- User is setting up on a new machine (Windows or Mac)

## Prerequisites

Before starting, verify these are already installed globally:

```bash
lean-ctx --version    # Should show 3.x.x
gitnexus --version    # Should show 1.x.x
```

If missing, install first:
```bash
cargo install lean-ctx
npm install -g gitnexus
```

On Windows, also verify WSL:
```bash
wsl -l -v             # Should show Ubuntu (or another distro)
```

## Workflow

### Step 1: Assess Current State

Read the global OpenCode config to see what's currently installed globally:
```bash
cat ~/.config/opencode/opencode.json
```

Look for `mcp` entries with `lean-ctx` and/or `gitnexus`.

### Step 2: Remove Global MCP Entries

Edit `~/.config/opencode/opencode.json` and remove:
- The `lean-ctx` MCP entry
- The `gitnexus` MCP entry

Leave other MCPs (web-reader, zread, etc.) untouched.

### Step 3: Create Project-Level MCP Config

**Important:** `.opencode/opencode.json` is platform-specific. It should NOT be committed to git or synced via Syncthing. Use the template below and create it locally on each machine.

Create `.opencode/opencode.json` in the project root:

#### Windows

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "lean-ctx": {
      "type": "local",
      "command": ["lean-ctx"],
      "enabled": true,
      "environment": {
        "LEAN_CTX_DATA_DIR": "C:\\Users\\<USERNAME>\\.config\\lean-ctx"
      }
    },
    "gitnexus": {
      "type": "local",
      "command": [
        "wsl",
        "-d",
        "Ubuntu",
        "-e",
        "bash",
        "-lc",
        "cd \"$GITNEXUS_REPO_PATH\" && npx -y gitnexus@<VERSION> mcp"
      ],
      "enabled": true,
      "environment": {
        "GITNEXUS_REPO_PATH": "/mnt/c/<WSL_PATH_TO_PROJECT>"
      },
      "timeout": 15000
    }
  }
}
```

#### macOS

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

Replace:
- `<USERNAME>` with the actual username
- `<WSL_PATH_TO_PROJECT>` (Windows only) with the WSL path (e.g., `/mnt/c/Users/alice/project`)
- `<VERSION>` (Windows only) with the installed GitNexus version (e.g., `1.6.3`)

**Why WSL for GitNexus on Windows?** GitNexus uses LadybugDB which has WAL corruption issues on Windows native filesystem. The index must be built and served from WSL. On macOS, GitNexus runs natively without issues.

### Step 3b: Create Project-Level Codex MCP Config (Optional)

If the user also uses **Codex** (OpenAI Codex CLI), create `.codex/config.toml`:

**Important:** `.codex/config.toml` is platform-specific and should NOT be committed to git. Use the template approach below.

Create `.codex/config.toml.template` (committed to git):

```toml
# Codex project-level MCP configuration template
# Copy this file to .codex/config.toml and adjust paths for your platform.
# Do NOT commit .codex/config.toml — it contains platform-specific absolute paths.

# =============================================================================
# Windows Configuration
# =============================================================================
# [mcp_servers.lean-ctx]
# command = "C:\\Users\\<USERNAME>\\.cargo\\bin\\lean-ctx.exe"
#
# [mcp_servers.gitnexus]
# command = "cmd"
# args = ["/c", "npx", "-y", "gitnexus@latest", "mcp"]

# =============================================================================
# macOS Configuration
# =============================================================================
# [mcp_servers.lean-ctx]
# command = "lean-ctx"
#
# [mcp_servers.gitnexus]
# command = "npx"
# args = ["-y", "gitnexus@latest", "mcp"]
```

Then create `.codex/config.toml` locally on each machine (do not commit):

#### Windows

```toml
[mcp_servers.lean-ctx]
command = "C:\\Users\\<USERNAME>\\.cargo\\bin\\lean-ctx.exe"

[mcp_servers.gitnexus]
command = "cmd"
args = ["/c", "npx", "-y", "gitnexus@latest", "mcp"]
```

#### macOS

```toml
[mcp_servers.lean-ctx]
command = "lean-ctx"

[mcp_servers.gitnexus]
command = "npx"
args = ["-y", "gitnexus@latest", "mcp"]
```

Add `.codex/config.toml` to `.gitignore`:
```gitignore
# Codex local config (platform-specific)
.codex/config.toml
```

**Note:** Codex loads project-level config from `.codex/config.toml` when the project is trusted. The config precedence is: CLI flags > profile > project config (`.codex/config.toml`) > user config (`~/.codex/config.toml`).

### Step 4: Copy GitNexus Skills to Project

GitNexus skills are bundled with the npm package. Copy them to the project:

```bash
# Find the source path
# Windows: %APPDATA%/npm/node_modules/gitnexus/skills
# macOS: $(npm root -g)/gitnexus/skills

# Destination
mkdir -p .opencode/skills

# Copy each skill into its own directory with SKILL.md
cp "<SRC>/gitnexus-guide.md" .opencode/skills/gitnexus-guide/SKILL.md
cp "<SRC>/gitnexus-exploring.md" .opencode/skills/gitnexus-exploring/SKILL.md
cp "<SRC>/gitnexus-impact-analysis.md" .opencode/skills/gitnexus-impact-analysis/SKILL.md
cp "<SRC>/gitnexus-debugging.md" .opencode/skills/gitnexus-debugging/SKILL.md
cp "<SRC>/gitnexus-refactoring.md" .opencode/skills/gitnexus-refactoring/SKILL.md
cp "<SRC>/gitnexus-cli.md" .opencode/skills/gitnexus-cli/SKILL.md
cp "<SRC>/gitnexus-pr-review.md" .opencode/skills/gitnexus-pr-review/SKILL.md
```

Then update all stale-index references in the copied skills from `npx gitnexus analyze` to `npm run update:gitnexus`.

### Step 5: Create Freshness Check Script

Create `scripts/check-gitnexus-freshness.mjs`:

```javascript
#!/usr/bin/env node
import { execSync } from "child_process";
import { existsSync, readFileSync } from "fs";
import { resolve } from "path";

const META_PATH = resolve(".gitnexus/meta.json");

function getCurrentHead() {
  return execSync("git rev-parse HEAD", { encoding: "utf-8" }).trim();
}

function getMetaCommit() {
  if (!existsSync(META_PATH)) return null;
  try {
    const meta = JSON.parse(readFileSync(META_PATH, "utf-8"));
    return meta.lastCommit || null;
  } catch {
    return null;
  }
}

const currentHead = getCurrentHead();
const metaCommit = getMetaCommit();

if (!metaCommit || metaCommit !== currentHead) {
  console.error("❌ GitNexus index is stale. Run: npm run update:gitnexus");
  process.exit(1);
}

console.log("✅ GitNexus index is fresh");
```

### Step 6: Create Cross-Platform Update Script

Create `scripts/update-gitnexus.mjs`:

```javascript
#!/usr/bin/env node
/**
 * update-gitnexus.mjs
 *
 * Rebuilds the GitNexus index.
 * On macOS/Linux: runs natively.
 * On Windows: uses WSL (LadybugDB WAL incompatibility).
 */

import { execSync } from "child_process";
import { resolve } from "path";

const REPO_ROOT = resolve(".");
const FORCE = process.argv.includes("--force");
const IS_WINDOWS = process.platform === "win32";

function main() {
  const forceFlag = FORCE ? " --force" : "";

  if (IS_WINDOWS) {
    const DISTRO = process.env.GITNEXUS_WSL_DISTRO || "Ubuntu";
    let wslPath;
    try {
      wslPath = execSync(
        `wsl -d ${DISTRO} -e wslpath -u "${REPO_ROOT}"`,
        { encoding: "utf-8" }
      ).trim();
    } catch {
      console.error(`❌ Failed to convert path to WSL format.`);
      process.exit(1);
    }

    console.log(`🔄 Updating GitNexus index via WSL (${DISTRO})...`);
    execSync(
      `wsl -d ${DISTRO} -e bash -lc "cd '${wslPath.replace(/'/g, "'\"'\"'")}' && npx -y gitnexus@<VERSION> analyze${forceFlag}"`,
      { stdio: "inherit", cwd: REPO_ROOT }
    );
  } else {
    console.log("🔄 Updating GitNexus index...");
    execSync(
      `npx -y gitnexus@<VERSION> analyze${forceFlag}`,
      { stdio: "inherit", cwd: REPO_ROOT }
    );
  }

  console.log("✅ GitNexus index updated successfully");
}

main();
```

Replace `<VERSION>` with the GitNexus version (e.g., `1.6.3`).

### Step 7: Create lean-ctx Check Script

Create `scripts/check-lean-ctx.mjs`:

```javascript
#!/usr/bin/env node
import { execSync } from "child_process";

try {
  const version = execSync("lean-ctx --version", { encoding: "utf-8" }).trim();
  console.log(`✅ lean-ctx is installed (${version})`);
  process.exit(0);
} catch {
  console.error("❌ lean-ctx not found. Install: cargo install lean-ctx");
  process.exit(1);
}
```

### Step 8: Wire Into package.json

Add scripts:
```json
{
  "scripts": {
    "check:gitnexus-freshness": "node scripts/check-gitnexus-freshness.mjs",
    "check:lean-ctx": "node scripts/check-lean-ctx.mjs",
    "update:gitnexus": "node scripts/update-gitnexus.mjs"
  }
}
```

Add to the `verify` script (at the beginning):
```bash
npm run check:gitnexus-freshness && npm run check:lean-ctx && ...
```

### Step 9: Update AGENTS.md

Add two sections:

1. **lean-ctx usage** — Explain how it works (shell hooks, auto-compress on cd), CLI commands (`cache stats`, `cache clear`, `doctor`), and MCP tool usage.

2. **GitNexus usage** — Explain the tools (`query`, `context`, `impact`, `detect_changes`), stale index warning, and the update constraint.

3. **Update Constraint** — Explicit rule: after every code change, run `npm run update:gitnexus`.

### Step 10: Add Pre-Commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/sh
echo "🔍 Checking GitNexus index freshness..."
node scripts/check-gitnexus-freshness.mjs
if [ $? -ne 0 ]; then
    echo "❌ Commit blocked: index stale. Run: npm run update:gitnexus"
    exit 1
fi
echo "✅ Index is fresh. Proceeding."
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Step 11: Configure gitignore and Syncthing

Add to `.gitignore`:
```gitignore
# Platform-specific OpenCode MCP config
.opencode/opencode.json

# Platform-specific Codex MCP config
.codex/config.toml

# Local git hooks (platform-specific paths)
.git/hooks/pre-commit

# GitNexus index data
.gitnexus

# Syncthing internal files
.stfolder
.stignore.local
```

Add to `.stignore` (if using Syncthing):
```
# Syncthing ignore patterns
.gitnexus
.opencode/opencode.json
.git/hooks/pre-commit
.stfolder
.stignore.local
.DS_Store
Thumbs.db
```

**Why exclude `.opencode/opencode.json`?** This file contains platform-specific paths (Windows WSL vs macOS native). If synced between machines, it will cause constant conflicts and overwrite the correct configuration.

### Step 12: Build Initial Index

Run the GitNexus analyzer:
```bash
npm run update:gitnexus
```

### Step 13: Verify

Run the verify gate:
```bash
npm run verify
```

Also verify manually:
```bash
node scripts/check-gitnexus-freshness.mjs   # Should pass
node scripts/check-lean-ctx.mjs             # Should pass
```

## Platform-Specific Notes

### Windows: LadybugDB WAL Corruption

**Symptom:** `Runtime exception: Corrupted wal file. Read out invalid WAL record type.`

**Cause:** GitNexus uses LadybugDB for the knowledge graph. Its Write-Ahead Log (WAL) implementation is incompatible with Windows native filesystem locking.

**Solution:** Always run GitNexus MCP server and `analyze` through WSL. The index lives in `.gitnexus/` but the registry and MCP must operate from the Linux side.

### macOS: npm Global Bin PATH

If `gitnexus` command is not found after `npm install -g gitnexus`:

```bash
# Find the binary location
ls $(npm root -g)/../bin/gitnexus

# Add to PATH in ~/.zshrc
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Or create a symlink
ln -s $(npm root -g)/../bin/gitnexus /opt/homebrew/bin/gitnexus
```

### macOS: lean-ctx Shell Hook

On macOS, lean-ctx shell hooks work with zsh. After installation:
```bash
lean-ctx init --global    # Installs zsh aliases
source ~/.zshrc           # Activate in current session
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
- [ ] Codex recognizes the project as trusted (shows in `codex` TUI or `~/.codex/config.toml` projects table)

### Shared
- [ ] `.gitignore` excludes `.opencode/opencode.json`, `.codex/config.toml`, and `.gitnexus/`
- [ ] `.stignore` (if using Syncthing) excludes platform-specific files
- [ ] `npm run check:gitnexus-freshness` passes
- [ ] `npm run check:lean-ctx` passes
- [ ] `npm run update:gitnexus` completes without errors
- [ ] `.gitnexus/meta.json` exists and `lastCommit` matches `git rev-parse HEAD`
- [ ] `npm run verify` passes (including the new checks)
- [ ] Git commit triggers the pre-commit hook successfully

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GitNexus index stale after update | Restart OpenCode to reload the MCP server |
| `wslpath` not found (Windows) | Ensure WSL Ubuntu is installed: `wsl --install -d Ubuntu` |
| `gitnexus` not found (macOS) | Add npm global bin to PATH or create symlink to `/opt/homebrew/bin/` |
| lean-ctx hook not active (Windows) | Run `. $PROFILE` in PowerShell, or restart terminal |
| lean-ctx hook not active (macOS) | Run `source ~/.zshrc`, or restart terminal |
| `npx gitnexus analyze` fails on Windows | Never run this on Windows native — always use `npm run update:gitnexus` |
| Pre-commit hook not running | Ensure it's executable: `chmod +x .git/hooks/pre-commit` |
| Syncthing keeps overwriting `.opencode/opencode.json` | Add `.opencode/opencode.json` to `.stignore` on both machines |
| Sync conflict files appear (`.sync-conflict-*`) | Restore files from git and ensure `.stignore` is configured |

## References

- lean-ctx: https://github.com/yvgude/lean-ctx
- GitNexus: https://github.com/abhigyanpatwari/gitnexus
- OpenCode MCP docs: https://opencode.ai/docs/zh-cn/mcp-servers/
- OpenCode Skills docs: https://opencode.ai/docs/zh-cn/skills/
