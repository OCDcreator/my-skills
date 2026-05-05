---
name: windows-project-level-tools
description: "Use when the user wants to configure GitNexus, lean-ctx, or any MCP tools/skills at the project level instead of globally on Windows. Triggers on phrases like 'project level', 'project-level', 'don't install globally', 'per project', 'windows mcp setup', 'gitnexus windows', 'lean-ctx setup', or when the user wants to isolate tool configurations to a specific repository. Also triggers when the user mentions adding constraints so tools update after code changes."
compatibility: opencode
---

# Windows Project-Level MCP & Tool Setup

Configure GitNexus and lean-ctx at the project level on Windows, with auto-update constraints.

## What This Skill Covers

- Migrate MCP servers from global `~/.config/opencode/opencode.json` to project-level `.opencode/opencode.json`
- Install GitNexus skills locally under `.opencode/skills/`
- Create scripts to check tool freshness and auto-update indexes
- Wire constraints into `package.json`, `AGENTS.md`, and git hooks
- Handle Windows-specific issues (LadybugDB WAL incompatibility via WSL)

## When to Use

- User says "don't install globally" or "project level only"
- User wants GitNexus on a new Windows project
- User wants lean-ctx isolated per project
- User asks to add constraints so indexes update after code changes
- User mentions Windows + code intelligence / context compression setup

## Prerequisites

Before starting, verify these are already installed globally:

```bash
lean-ctx --version    # Should show 3.x.x
gitnexus --version    # Should show 1.x.x
wsl -l -v             # Should show Ubuntu (or another distro)
```

If missing, install first:
```bash
cargo install lean-ctx
npm install -g gitnexus
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

Create `.opencode/opencode.json` in the project root:

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

Replace:
- `<USERNAME>` with the actual Windows username
- `<WSL_PATH_TO_PROJECT>` with the WSL path (e.g., `/mnt/c/Users/alice/project`)
- `<VERSION>` with the installed GitNexus version (e.g., `1.6.3`)

**Why WSL for GitNexus?** GitNexus uses LadybugDB which has WAL corruption issues on Windows native filesystem. The index must be built and served from WSL.

### Step 4: Copy GitNexus Skills to Project

GitNexus skills are bundled with the npm package. Copy them to the project:

```bash
# Source path (adjust version if needed)
SRC="$APPDATA/npm/node_modules/gitnexus/skills"

# Destination
mkdir -p .opencode/skills

# Copy each skill into its own directory with SKILL.md
cp "$SRC/gitnexus-guide.md" .opencode/skills/gitnexus-guide/SKILL.md
cp "$SRC/gitnexus-exploring.md" .opencode/skills/gitnexus-exploring/SKILL.md
cp "$SRC/gitnexus-impact-analysis.md" .opencode/skills/gitnexus-impact-analysis/SKILL.md
cp "$SRC/gitnexus-debugging.md" .opencode/skills/gitnexus-debugging/SKILL.md
cp "$SRC/gitnexus-refactoring.md" .opencode/skills/gitnexus-refactoring/SKILL.md
cp "$SRC/gitnexus-cli.md" .opencode/skills/gitnexus-cli/SKILL.md
cp "$SRC/gitnexus-pr-review.md" .opencode/skills/gitnexus-pr-review/SKILL.md
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

### Step 6: Create Update Script

Create `scripts/update-gitnexus.mjs`:

```javascript
#!/usr/bin/env node
import { execSync } from "child_process";
import { resolve } from "path";

const REPO_ROOT = resolve(".");
const FORCE = process.argv.includes("--force");
const DISTRO = process.env.GITNEXUS_WSL_DISTRO || "Ubuntu";

const forceFlag = FORCE ? " --force" : "";
const wslPath = execSync(
  `wsl -d ${DISTRO} -e wslpath -u "${REPO_ROOT}"`,
  { encoding: "utf-8" }
).trim();

function escapeShellArg(arg) {
  return "'" + arg.replace(/'/g, "'\"'\"'") + "'";
}

execSync(
  `wsl -d ${DISTRO} -e bash -lc "cd ${escapeShellArg(wslPath)} && npx -y gitnexus@<VERSION> analyze${forceFlag}"`,
  { stdio: "inherit" }
);
```

Replace `<VERSION>` with the GitNexus version.

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

### Step 11: Build Initial Index

Run the GitNexus analyzer via WSL:
```bash
npm run update:gitnexus
```

### Step 12: Verify

Run the verify gate:
```bash
npm run verify
```

Also verify manually:
```bash
node scripts/check-gitnexus-freshness.mjs   # Should pass
node scripts/check-lean-ctx.mjs             # Should pass
```

## Windows-Specific Issues

### LadybugDB WAL Corruption

**Symptom:** `Runtime exception: Corrupted wal file. Read out invalid WAL record type.`

**Cause:** GitNexus uses LadybugDB for the knowledge graph. Its Write-Ahead Log (WAL) implementation is incompatible with Windows native filesystem locking.

**Solution:** Always run GitNexus MCP server and `analyze` through WSL. The index lives in `.gitnexus/` but the registry and MCP must operate from the Linux side.

### WSL Path Conversion

Use `wslpath -u` to convert Windows paths to WSL paths:
```bash
wsl -d Ubuntu -e wslpath -u "C:\Users\Alice\project"
# Output: /mnt/c/Users/Alice/project
```

Always quote paths and escape shell arguments when building WSL commands programmatically.

## Verification Checklist

- [ ] Global `~/.config/opencode/opencode.json` no longer has `lean-ctx` or `gitnexus` MCP entries
- [ ] Project `.opencode/opencode.json` has both MCP entries
- [ ] `.opencode/skills/` contains 7 GitNexus skills
- [ ] `npm run check:gitnexus-freshness` passes
- [ ] `npm run check:lean-ctx` passes
- [ ] `npm run update:gitnexus` completes without errors
- [ ] `.gitnexus/meta.json` exists and `lastCommit` matches `git rev-parse HEAD`
- [ ] `npm run verify` passes (including the new checks)
- [ ] Git commit triggers the pre-commit hook successfully

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GitNexus index stale after update | Restart OpenCode to reload the WSL-based MCP server |
| `wslpath` not found | Ensure WSL Ubuntu is installed: `wsl --install -d Ubuntu` |
| lean-ctx hook not active | Run `. $PROFILE` in PowerShell, or restart terminal |
| `npx gitnexus analyze` fails on Windows | Never run this on Windows native — always use `npm run update:gitnexus` |
| Pre-commit hook not running | Ensure it's executable: `chmod +x .git/hooks/pre-commit` |

## References

- lean-ctx: https://github.com/yvgude/lean-ctx
- GitNexus: https://github.com/abhigyanpatwari/gitnexus
- OpenCode MCP docs: https://opencode.ai/docs/zh-cn/mcp-servers/
- OpenCode Skills docs: https://opencode.ai/docs/zh-cn/skills/
