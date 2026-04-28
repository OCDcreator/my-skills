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
- `DEEPSEEK_API_KEY=<your-key>` for native `deepseek`

`opencode-loop doctor/preflight` detects `DEEPSEEK_API_KEY` natively. Its `provider_keys.ok` result is still narrowed by the providers detected in the target project's `opencode.json`: if `deepseek` is the only configured provider, `DEEPSEEK_API_KEY` can satisfy the provider-key check; if the config also names OpenAI, Anthropic, or OpenAI-compatible providers, those keys are still required. If no provider is configured, the current preflight treats the full catalog as required.

Example provider setup:

```bash
task-master models --set-main glm-5.1 \
  --openai-compatible \
  --baseURL https://open.bigmodel.cn/api/paas/v4/

task-master models --set-main deepseek-chat \
  --openai-compatible \
  --baseURL https://api.deepseek.com/v1/
```

The Task Master example above uses its OpenAI-compatible adapter for DeepSeek. That is separate from opencode-loop's native `deepseek` provider-key detection, which looks for `DEEPSEEK_API_KEY` when the target `opencode.json` names `deepseek`.

`task-master parse-prd` must run from inside the target project directory because the PRD path is resolved relative to that directory.

## Pipeline Overview

```text
User requirement
    ↓
Layer 1: OpenSpec — create a change proposal
    openspec init → openspec new change → write proposal.md
    ↓
Layer 2: Task Master — generate structured tasks
    task-master init --yes → task-master parse-prd → optional expand
    ↓
Layer 3: opencode-loop — import, enrich, promote, execute
    plan --from-taskmaster → enrich → queue promote → start execute
```

## Layer 1: OpenSpec

OpenSpec creates the change container. The AI then writes the proposal content.

```bash
cd /path/to/target

openspec init /path/to/target
openspec new change my-feature --description "Short description of what we're building"
```

After `openspec new change`, write `openspec/changes/my-feature/proposal.md` before running `task-master parse-prd`.

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

Notes:

- `parse-prd` requires a configured AI provider and the correct API key in `.env`; for DeepSeek, use the key expected by the adapter you configured for Task Master, and remember that opencode-loop preflight separately checks the target `opencode.json` provider set.
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

### Step 3: Review Gate (Hook + Queue Contract)

The review gate only recognizes a `post_iteration` hook named exactly `gate-review`, AND the task must have `review_required: true` (or the profile must have `reviewer_required: true`). **Attaching the hook is not enough** — the task-level flag must be set.

Detect the reviewer command first, then build the appropriate flags per CLI:

```bash
if command -v kimi-code >/dev/null 2>&1; then
  REVIEWER_CMD="kimi-code"
elif command -v kimi >/dev/null 2>&1; then
  REVIEWER_CMD="kimi"
elif command -v claude >/dev/null 2>&1; then
  REVIEWER_CMD="claude"
else
  echo "No reviewer CLI found — install kimi-code, kimi, or claude"
  exit 1
fi

# Build flags per reviewer
case "$(basename "$REVIEWER_CMD")" in
  kimi|kimi-code)
    REVIEWER_FLAGS="--print --final-message-only"
    ;;
  claude)
    REVIEWER_FLAGS="-p"
    ;;
  *)
    echo "Unknown reviewer: $REVIEWER_CMD"
    exit 1
    ;;
esac
```

Add the gate-review hook:

```bash
REVIEW_MSG="Review changes. Output ONLY JSON: {\"result\":\"pass\"} or {\"result\":\"needs_changes\"} or {\"result\":\"reject\"}"
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name gate-review --command "$REVIEWER_CMD $REVIEWER_FLAGS --cwd \"\$OPENCODE_LOOP_TARGET_DIR\" \"$REVIEW_MSG\"" --attempts 3
```

The last line of stdout must be valid JSON:

- `{"result":"pass"}`
- `{"result":"needs_changes"}`
- `{"result":"reject"}`

Validate the reviewer independently before trusting `hooks test`:

```bash
$REVIEWER_CMD $REVIEWER_FLAGS --cwd /path/to/target "Output ONLY JSON: {\"result\":\"pass\"}"
# Must return: {"result":"pass"}
```

Set `review_required: true` on each task that needs gated review:

```bash
jq '.tasks[].review_required = true' \
  /path/to/target/.opencode-loop/queue.json > /tmp/q.tmp && mv /tmp/q.tmp /path/to/target/.opencode-loop/queue.json
```

Verify:

```bash
jq '.tasks[] | {id, review_required}' /path/to/target/.opencode-loop/queue.json
jq '.profile.reviewer_required' /path/to/target/.opencode-loop/queue.json
```

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

# === Layer 1: OpenSpec ===
openspec init "$TARGET"
openspec new change "$CHANGE" --description "See proposal.md"

# Write proposal.md content here before running parse-prd
cat > "openspec/changes/$CHANGE/proposal.md" << 'EOF'
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
task-master init --yes
task-master parse-prd "openspec/changes/$CHANGE/proposal.md"

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

# === Layer 1: OpenSpec ===
openspec init $Target
openspec new change $ChangeName --description "See proposal.md"

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

$proposalPath = Join-Path $Target "openspec/changes/$ChangeName/proposal.md"
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($proposalPath, $proposal, $utf8)

# === Layer 2: Task Master ===
task-master init --yes
task-master parse-prd "openspec/changes/$ChangeName/proposal.md"

# === Layer 3: opencode-loop ===
opencode-loop plan --dir $Target --from-taskmaster --tag tm
opencode-loop queue validate --dir $Target
opencode-loop init --dir $Target --mode execute
opencode-loop start --dir $Target --profile execute
```

PowerShell guidance here is **PowerShell 5.1+**. Use `[System.IO.File]::WriteAllText` for UTF-8 no-BOM; do not swap it for `Set-Content`.

## Hook Recipes

### Review Gate Hook

```bash
REVIEWER_CMD=$(command -v kimi-code 2>/dev/null || command -v kimi 2>/dev/null || command -v claude 2>/dev/null || echo "")
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name gate-review --command "$REVIEWER_CMD --print --final-message-only --cwd \"\$OPENCODE_LOOP_TARGET_DIR\" \"Review changes. Output ONLY JSON: {\\\"result\\\":\\\"pass\\\"} or {\\\"result\\\":\\\"needs_changes\\\"} or {\\\"result\\\":\\\"reject\\\"}\"" --attempts 3
```

**Important**: The `gate-review` hook must be paired with `review_required: true` on each task (or `reviewer_required: true` on the queue profile) for the review gate to participate in gate decisions. A hook without the queue flag is a no-op for gating.

### Extra Reviewer Hooks

These run but do not satisfy the review gate on their own:

```bash
KIMI_CMD=$(command -v kimi-code 2>/dev/null || command -v kimi 2>/dev/null || echo "")
opencode-loop hooks add --dir /path/to/target --event pre_iteration \
  --name kimi-check --command "$KIMI_CMD --dir \"\$OPENCODE_LOOP_TARGET_DIR\" \"Check for issues\"" --attempts 3

opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name codex-review --command 'codex exec --cd "$OPENCODE_LOOP_TARGET_DIR" "Architectural review"' --attempts 3

opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name claude-review --command 'claude -p --cwd "$OPENCODE_LOOP_TARGET_DIR" "Review code changes."' --attempts 3
```

## Windows Caveats

On Windows, `opencode-loop` delegates Bash-facing workflows through WSL.

- Hook commands run in WSL via `bash -lc`.
- External CLIs used by hooks must be available inside WSL.
- Verify with `wsl -d Ubuntu -- which claude kimi-code kimi codex`.
- If needed, symlink Windows-installed CLIs into WSL PATH, for example: `ln -s $(which claude.exe) /usr/local/bin/claude`
- `$OPENCODE_LOOP_TARGET_DIR` is a WSL path inside hooks; convert with `wslpath -w` only when a Windows-native CLI truly requires it.
- Use WSL for repo Bash/Python validation rather than native PowerShell test runs.

## Minimal Operator Checklist

1. Create the OpenSpec change.
2. Write `proposal.md` before `task-master parse-prd`.
3. Import with `opencode-loop plan --from-taskmaster` — this creates `.opencode-loop/queue.json`.
4. Enrich `verification` and `acceptance_checks` in `queue.json`.
5. Set `review_required: true` on tasks that need gated review (hook alone is not sufficient).
6. Promote each task.
7. Initialize with `opencode-loop init --mode execute` — this creates `opencode.json`, `.opencode-loop/state.json`, and other runtime files. **Only `git add` files that exist at this point** (openspec/, .taskmaster/); `opencode.json` is gitignored by `setup.sh` and should not be committed.
8. Start with `opencode-loop start --profile execute`.
9. Inspect `queue status`, `queue show`, `status --json`, and progress logs when anything fails.

**When continuing in a new worktree**: Follow the full Worktree Continuation Checklist in SKILL.md § Worktree Isolation Lifecycle (state migration, dependency installation, baseline validation).
