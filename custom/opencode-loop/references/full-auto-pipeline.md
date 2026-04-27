# Full Auto Pipeline

Use this reference when the user wants the full requirement-to-execution pipeline: **OpenSpec → Task Master → opencode-loop execute mode**. The main `SKILL.md` keeps the route-selection and core gate contract lean; this file holds the fuller workflow, one-script summaries, Windows caveats, and hook recipes.

## What This Pipeline Does

The three layers solve different problems:

1. **OpenSpec** structures a fuzzy requirement into a proposal.
2. **Task Master** decomposes the proposal into ordered tasks.
3. **opencode-loop execute mode** imports those tasks, adds gates, and runs them one by one.

Use it when the user wants a requirement turned into a gated execution queue instead of a single open-ended unattended run.

## Prerequisites

- `openspec` CLI installed: `npm install -g @fission-ai/openspec`
- `task-master` CLI installed: `npm install -g task-master-ai`
- `opencode-loop` CLI installed
- `opencode`, `jq`, and `git` available
- Task Master AI provider configured before `task-master parse-prd`

Set the API key in the target project's `.env` file (ensure `.env` is in `.gitignore`):

- `OPENAI_COMPATIBLE_API_KEY=<your-key>` for `--openai-compatible` providers
- `ANTHROPIC_API_KEY=<your-key>` for Anthropic

Example provider setup:

```bash
task-master models --set-main glm-5.1 \
  --openai-compatible \
  --baseURL https://open.bigmodel.cn/api/paas/v4/

task-master models --set-main deepseek-chat \
  --openai-compatible \
  --baseURL https://api.deepseek.com/v1/
```

`task-master parse-prd` must run from inside the target project directory because the PRD path is resolved relative to that directory.

## Pipeline Overview

```text
User requirement
    ↓
Layer 0: Create feature branch — NEVER work on main
    git checkout -b feat/my-feature
    ↓
Layer 1: OpenSpec — create a change proposal
    openspec init → openspec new change → write proposal.md
    ↓
Layer 2: Task Master — generate structured tasks
    task-master init --yes → task-master parse-prd → optional expand
    ↓
Layer 3: opencode-loop — import, enrich, promote, execute
    plan --from-taskmaster → enrich → set isolation → queue promote → start execute
```

## Layer 1: OpenSpec

OpenSpec creates the change container. The AI then writes the proposal content.

```bash
cd /path/to/target

openspec init /path/to/target
openspec new change my-feature --description "Short description of what we're building"
```

After `openspec new change`, the CLI creates the change directory and `.openspec.yaml` and `README.md`, but NOT `proposal.md`, `design.md`, `tasks.md`, or `specs/`. You must generate these artifacts explicitly:

```bash
openspec instructions proposal --change my-feature
openspec instructions design --change my-feature
openspec instructions specs --change my-feature
openspec instructions tasks --change my-feature
```

Then write each artifact file. Start with `proposal.md`:

After generating artifact instructions, write the proposal content in `openspec/changes/my-feature/proposal.md` before running `task-master parse-prd`.

Minimal proposal template:

```bash
cat > openspec/changes/my-feature/proposal.md << 'EOF'
# Proposal: [Feature Name]

## Problem
[What problem does this solve? Why is it needed?]

## Proposed Solution
[High-level approach]

## Scope
### In Scope
- [What we will build]

### Out of Scope
- [What we will NOT touch]

## Acceptance Criteria
- [Measurable outcomes]
- [Tests that must pass]

## Technical Constraints
- [Performance requirements]
- [Compatibility requirements]
- [Dependencies to consider]

## References
- [Existing code patterns to follow]
- [External docs/APIs]
EOF
```

Optionally add `openspec/changes/my-feature/tasks.md` when you already want a human-readable task checklist alongside the proposal:

```bash
cat > openspec/changes/my-feature/tasks.md << 'EOF'
# Tasks

## 1. Setup
- [ ] 1.1 Initialize project structure
- [ ] 1.2 Configure build tooling

## 2. Core Implementation
- [ ] 2.1 Implement [module A]
- [ ] 2.2 Implement [module B]
- [ ] 2.3 Wire modules together

## 3. Testing & Quality
- [ ] 3.1 Write unit tests
- [ ] 3.2 Write integration tests
- [ ] 3.3 Verify all acceptance criteria
EOF
```

## Layer 2: Task Master

Use the OpenSpec proposal as the PRD input for Task Master.

### Provider Preflight (MANDATORY)

Before running `parse-prd`, you MUST detect available API keys and configure the provider. Skip this only if the user has already configured Task Master.

If the target project has a `.env` file, source it first so the detection sees those keys:

```bash
[[ -f .env ]] && set -a && source .env && set +a
```

Then detect keys:
if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  task-master models --set-main deepseek-chat --openai-compatible --baseURL https://api.deepseek.com/v1/
  # If no fallback key, use same:
  task-master models --set-research deepseek-chat --openai-compatible --baseURL https://api.deepseek.com/v1/
elif [[ -n "${OPENAI_COMPATIBLE_API_KEY:-}" ]]; then
  export OPENAI_API_KEY="$OPENAI_COMPATIBLE_API_KEY"
  task-master models --set-main openai-compatible
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  task-master models --set-main anthropic
else
  echo "BLOCKER: No AI provider key found. Set one of: DEEPSEEK_API_KEY, OPENAI_COMPATIBLE_API_KEY, ANTHROPIC_API_KEY"
  exit 1
fi
```

If only `DEEPSEEK_API_KEY` is available but Task Master expects `OPENAI_API_KEY`:

```bash
export OPENAI_API_KEY="$DEEPSEEK_API_KEY"
```

```bash
cd /path/to/target

task-master init --yes
task-master parse-prd openspec/changes/my-feature/proposal.md

# Optional
# task-master parse-prd openspec/changes/my-feature/proposal.md --num-tasks=10
task-master expand --id=1
task-master expand --id=2
task-master list
```

### Task Normalization (MANDATORY after parse-prd)

`parse-prd` often generates meta-automation tasks (scaffolding scripts, guardrails, template files) instead of real repo work. You MUST normalize:

1. Read the generated task list:
   ```bash
   task-master list
   ```
2. Cross-reference with OpenSpec `tasks.md` (the authority).
3. Remove or consolidate tasks that:
   - Create automation scaffolding instead of implementing features
   - Invent new script/tool layers not requested by the user
   - Duplicate the same work across multiple tasks
4. Keep only tasks that directly modify the target repo's source code, tests, or configuration.
5. If tasks are too granular or too vague, restructure them to match the OpenSpec task boundaries.

⚠️ Task Master output is NOT authoritative. OpenSpec `tasks.md` is the contract authority. Task Master is a decomposition tool, not a design authority.

Notes:

- `parse-prd` requires a configured AI provider and the correct API key in `.env`.
- The Task Master adapter used by `opencode-loop plan --from-taskmaster` already handles `.master.tasks[]` automatically. Do not hand-roll your own JSON parser unless you are intentionally bypassing the adapter.

## Layer 3: Import Into `opencode-loop`

### Step 1: Import

```bash
opencode-loop plan --dir /path/to/target --from-taskmaster --tag tm
```

This reads `.taskmaster/tasks/tasks.json` and creates `.opencode-loop/queue.json` with tasks in `draft`.

`plan` refuses to overwrite an existing `queue.json`. Delete or rename the old file before re-importing.

### Step 2: Enrich

Task Master imports typically carry `verification` from `testStrategy`, but `acceptance_checks` still need to be added. Discover the project's real verification commands first, then assign per-task checks. Avoid assuming `npm test`.

Supported acceptance check types:

- `command`
- `file_exists`
- `contains`

Example Bash enrichment:

```bash
QUEUE="/path/to/target/.opencode-loop/queue.json"

jq '(.tasks[] | select(.id == "tm-1") | .verification) = ["make test"]' \
  "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"

jq '(.tasks[] | select(.id == "tm-1") | .acceptance_checks) = [{"type":"file_exists","path":"src/auth.ts"}]' \
  "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
```

Example PowerShell enrichment using UTF-8 no-BOM and `[System.IO.File]::WriteAllText`:

```powershell
$queue = "C:\path\to\target\.opencode-loop\queue.json"
$tmp = Join-Path $env:TEMP "q.tmp"
$utf8 = [System.Text.UTF8Encoding]::new($false)
$result = jq '(.tasks[] | select(.id == "tm-1") | .acceptance_checks) = [{"type":"file_exists","path":"src/auth.ts"}]' $queue
[System.IO.File]::WriteAllText($tmp, $result, $utf8)
Move-Item -Force $tmp $queue
```

PowerShell guidance here is **PowerShell 5.1+**, not 7+.

### Step 3: Optional Review Hook

The review gate only recognizes a `post_iteration` hook named exactly `gate-review`.

```bash
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name gate-review --command 'claude -p --cwd "$OPENCODE_LOOP_TARGET_DIR" "Review changes. Output ONLY JSON: {\"result\":\"pass\"} or {\"result\":\"needs_changes\"} or {\"result\":\"reject\"}"' --attempts 3
```

The last line of stdout must be valid JSON:

- `{"result":"pass"}`
- `{"result":"needs_changes"}`
- `{"result":"reject"}`

### Step 4: Promote

```bash
opencode-loop queue validate --dir /path/to/target

for id in $(jq -r '.tasks[] | select(.status=="draft") | .id' /path/to/target/.opencode-loop/queue.json); do
  opencode-loop queue promote --dir /path/to/target --task "$id"
done
```

### Step 5: Initialize And Start

```bash
opencode-loop init --dir /path/to/target --mode execute
opencode-loop start --dir /path/to/target --profile execute
```

Or use the core script when the user needs advanced flags:

```bash
bash opencode-loop.sh --dir /path/to/target --mode execute --iterations 30 --auto-reset
```

## One-Script Summary (Bash)

```bash
#!/bin/bash
set -euo pipefail
TARGET="${1:?Usage: $0 /path/to/target}"
CHANGE="${2:-my-feature}"
cd "$TARGET"

# === Layer 0: Feature branch ===
git checkout -b "feat/$CHANGE"

# === Layer 1: OpenSpec ===
openspec init "$TARGET"
openspec new change my-feature --description "See proposal.md"
openspec instructions proposal --change my-feature
openspec instructions design --change my-feature
openspec instructions specs --change my-feature
openspec instructions tasks --change my-feature

# Write proposal.md content here before running parse-prd
cat > openspec/changes/my-feature/proposal.md << 'EOF'
# Proposal: My Feature

## Problem
Describe the problem.

## Proposed Solution
Describe the solution.

## Acceptance Criteria
- Tests pass
- Feature works end-to-end
EOF

# === Layer 2: Task Master ===
# Provider preflight — detect available API keys
if [[ -n "${DEEPSEEK_API_KEY:-}" ]]; then
  task-master models --set-main deepseek-chat --openai-compatible --baseURL https://api.deepseek.com/v1/
elif [[ -n "${OPENAI_COMPATIBLE_API_KEY:-}" ]]; then
  export OPENAI_API_KEY="$OPENAI_COMPATIBLE_API_KEY"
  task-master models --set-main openai-compatible
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  task-master models --set-main anthropic
fi

task-master init --yes
task-master parse-prd openspec/changes/my-feature/proposal.md
# Task normalization: review and remove meta-automation tasks before import

# === Layer 3: opencode-loop ===
opencode-loop plan --dir "$TARGET" --from-taskmaster --tag tm

QUEUE="$TARGET/.opencode-loop/queue.json"
for id in $(jq -r '.tasks[] | select(.acceptance_checks | length == 0) | .id' "$QUEUE"); do
  jq --arg id "$id" '(.tasks[] | select(.id == $id) | .acceptance_checks) = [{"type":"command","command":"make test"}]' \
    "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
done

opencode-loop queue validate --dir "$TARGET"
for id in $(jq -r '.tasks[] | select(.status=="draft") | .id' "$QUEUE"); do
  opencode-loop queue promote --dir "$TARGET" --task "$id"
done

# Set branch isolation so tasks don't all land on the same branch
jq '.profile.isolation = "branch" | .profile.integration_strategy = "branch_chain"' \
  "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"

# Commit bootstrap assets before starting execute (dirty tree blocks new tasks)
git add openspec/ .taskmaster/ opencode.json
git add .claude/ .gemini/ .opencode/ 2>/dev/null || true
git commit -m "chore: bootstrap opencode-loop pipeline artifacts"

opencode-loop init --dir "$TARGET" --mode execute
opencode-loop start --dir "$TARGET" --profile execute
```

## One-Script Summary (PowerShell)

```powershell
param(
  [Parameter(Mandatory = $true)]
  [string]$Target,
  [string]$ChangeName = "my-feature"
)

Set-Location $Target

# === Layer 0: Feature branch ===
git checkout -b "feat/$ChangeName"

# === Layer 1: OpenSpec ===
openspec init $Target
openspec new change my-feature --description "See proposal.md"
openspec instructions proposal --change my-feature
openspec instructions design --change my-feature
openspec instructions specs --change my-feature
openspec instructions tasks --change my-feature

$proposal = @"
# Proposal: My Feature

## Problem
Describe the problem.

## Proposed Solution
Describe the solution.

## Acceptance Criteria
- Tests pass
- Feature works end-to-end
"@

$proposalPath = Join-Path $Target "openspec/changes/my-feature/proposal.md"
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($proposalPath, $proposal, $utf8)

# === Layer 2: Task Master ===
# Provider preflight — detect available API keys
if ($env:DEEPSEEK_API_KEY) {
  task-master models --set-main deepseek-chat --openai-compatible --baseURL https://api.deepseek.com/v1/
} elseif ($env:OPENAI_COMPATIBLE_API_KEY) {
  $env:OPENAI_API_KEY = $env:OPENAI_COMPATIBLE_API_KEY
  task-master models --set-main openai-compatible
} elseif ($env:ANTHROPIC_API_KEY) {
  task-master models --set-main anthropic
}

task-master init --yes
task-master parse-prd openspec/changes/my-feature/proposal.md
# Task normalization: review and remove meta-automation tasks before import

# === Layer 3: opencode-loop ===
opencode-loop plan --dir $Target --from-taskmaster --tag tm
opencode-loop queue validate --dir $Target

# Set branch isolation
$queueFile = Join-Path $Target ".opencode-loop/queue.json"
$tmp = Join-Path $env:TEMP "q.tmp"
$utf8 = [System.Text.UTF8Encoding]::new($false)
$result = jq '.profile.isolation = "branch" | .profile.integration_strategy = "branch_chain"' $queueFile
[System.IO.File]::WriteAllText($tmp, $result, $utf8)
Move-Item -Force $tmp $queueFile

# Commit bootstrap assets before starting execute
git add openspec/ .taskmaster/ opencode.json
git add .claude/ .gemini/ .opencode/ 2>$null; if ($LASTEXITCODE -ne 0) { $null }
git commit -m "chore: bootstrap opencode-loop pipeline artifacts"

opencode-loop init --dir $Target --mode execute
opencode-loop start --dir $Target --profile execute
```

PowerShell guidance here is **PowerShell 5.1+**. Use `[System.IO.File]::WriteAllText` for UTF-8 no-BOM; do not swap it for `Set-Content`.

## Hook Recipes

### Review Gate Hook

```bash
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name gate-review --command 'claude -p --cwd "$OPENCODE_LOOP_TARGET_DIR" "Review changes. Output ONLY JSON: {\"result\":\"pass\"} or {\"result\":\"needs_changes\"} or {\"result\":\"reject\"}"' --attempts 3
```

### Extra Reviewer Hooks

These run but do not satisfy the review gate on their own:

```bash
opencode-loop hooks add --dir /path/to/target --event pre_iteration \
  --name kimi-check --command 'kimi-code --dir "$OPENCODE_LOOP_TARGET_DIR" "Check for issues"' --attempts 3

opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name codex-review --command 'codex exec --cd "$OPENCODE_LOOP_TARGET_DIR" "Architectural review"' --attempts 3

opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name claude-review --command 'claude -p --cwd "$OPENCODE_LOOP_TARGET_DIR" "Review code changes."' --attempts 3
```

## Windows Caveats

On Windows, `opencode-loop` delegates Bash-facing workflows through WSL.

- Hook commands run in WSL via `bash -lc`.
- External CLIs used by hooks must be available inside WSL.
- Verify with `wsl -d Ubuntu -- which claude kimi-code codex`.
- If needed, symlink Windows-installed CLIs into WSL PATH, for example: `ln -s $(which claude.exe) /usr/local/bin/claude`
- `$OPENCODE_LOOP_TARGET_DIR` is a WSL path inside hooks; convert with `wslpath -w` only when a Windows-native CLI truly requires it.
- Use WSL for repo Bash/Python validation rather than native PowerShell test runs.

## Minimal Operator Checklist

1. Create the OpenSpec change.
2. Write `proposal.md` before `task-master parse-prd`.
3. Import with `opencode-loop plan --from-taskmaster`.
4. Enrich `verification` and `acceptance_checks`.
5. Promote each task.
6. Initialize `--mode execute`.
7. Start with `opencode-loop start --profile execute`.
8. Inspect `queue status`, `queue show`, `status --json`, and progress logs when anything fails.
