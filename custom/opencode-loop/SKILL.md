---
name: opencode-loop
description: "Use when the user wants opencode-loop unattended or self-running multi-iteration coding over a target project: run build-verify-fix cycles, optimize/refactor repos, fix test/lint/type failures, or bootstrap projects. Trigger on phrases like 无人值守, 自动循环, 自动修 bug, 让大模型自己跑, overnight coding, autopilot coding, supervisor watchdog, self-healing loop, 全自动流水线, 从需求到代码. Also trigger for queue-gated execute mode with verification/acceptance gates, task-by-task gated execution, OpenSpec/Task Master adapter import, gate failures and retries. Do not trigger for one-shot debugging, generic for/while loops, or CI/CD pipeline setup."
---

# OpenCode Loop Skill

Use this skill to turn a natural language requirement into an autonomously executed project. The default workflow is the **Full Auto Pipeline**: you receive a requirement, structure it with OpenSpec, decompose it with Task Master, then execute each task through opencode-loop's gated queue — without asking the user to choose modes or run individual commands.

## How This Skill Works

When the user gives you a requirement (e.g., "帮我写一个计算器库", "build a REST API", "add auth to my app"), you do this automatically:

1. **Read `references/full-auto-pipeline.md`** — it contains the complete three-layer workflow. Load it now and follow it end-to-end.
2. **Execute Layer 1** (OpenSpec) — `openspec init`, `openspec new change`, then YOU write the proposal.
3. **Execute Layer 2** (Task Master) — `task-master init --yes`, `task-master parse-prd`, configure AI provider if needed.
4. **Execute Layer 3** (opencode-loop) — `plan --from-taskmaster`, enrich tasks, promote, `init --mode execute`, start.
5. **Hand off** the running loop to the user with monitoring instructions.

Do NOT ask "which mode?" or "which route?" when the user gives a requirement. Just start the pipeline. Only ask for clarification if the target project path is unclear or the requirement is genuinely ambiguous.

The three routes exist for users who explicitly request them:
- **`dev` / `ml`** — user says "run opencode-loop in dev mode" or wants open-ended iteration without structured tasks.
- **Queue-gated `execute`** — user already has a tasks file and wants to skip OpenSpec/Task Master.
- **TUI** — user explicitly asks for the visual control plane.

## Before Starting

Clarify if unclear:

- Target project path (required).
- Safety boundary: files or directories the loop must not modify.

Everything else (proposal, tasks, gates) you handle autonomously.

## Locate The Repo

When already inside the `opencode-loop` repository, use the current repo root. Otherwise locate it first:

- Prefer the global `opencode-loop` wrapper if it is installed.
- Ask for the local repo path if it is unknown.
- On macOS, use the native repo path directly.
- On Windows, prefer WSL for Bash-facing workflows.
- Known Windows repo pattern for this environment: `C:\Users\lt\Desktop\Write\open-source-project\autonomous-ai-agents\agent-loops\opencode-loop`.

Never run `lib/*.sh` directly; they are sourced modules behind `opencode-loop.sh`.

## Prefer The AI-Friendly CLI

Prefer the wrapper for repeatable agent work:

```bash
opencode-loop --version
opencode-loop doctor --dir /path/to/target --json
opencode-loop status --dir /path/to/target --json
opencode-loop next-command --dir /path/to/target --kind supervisor --profile long
opencode-loop next-command --dir /path/to/target --kind supervisor --profile execute --wrap tmux --tmux-session target-loop
```

Use `opencode-loop update-check --json` only when the user explicitly asks whether the tool itself is current.

If the wrapper is missing, install it from the repo checkout:

```bash
bash bin/install-cli.sh
PowerShell -ExecutionPolicy Bypass -File .\bin\install-cli.ps1
```

## Prepare The Target Project

Prepare enough context so the unattended loop has a clear objective:

1. Ensure the target directory exists.
2. Ensure the project has Git when appropriate.
3. Add a concise project brief if the repo lacks one.
4. Record acceptance criteria in plain language.
5. Keep secrets out of prompts, `.env`, logs, and `.opencode-loop/`. Note: `opencode.json` is runtime-generated and gitignored by `setup.sh`; do not attempt to commit it unless the target project explicitly requires it.

## Command-Line Workflow (`dev` / `ml`)

Use this route for open-ended unattended runs.

### 1. Preflight

```bash
opencode-loop --version
opencode-loop doctor --dir /path/to/target --json
```

`doctor --json` returns a comprehensive health check:
- `commands` — availability of `opencode`, `jq`, `git`, `timeout`
- `provider_keys` — detected API keys, configured providers, missing keys, and `ok` boolean. Native catalog keys are `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_COMPATIBLE_API_KEY`, and `DEEPSEEK_API_KEY`; `ok` is still narrowed by providers detected in the target `opencode.json`, so `DEEPSEEK_API_KEY` alone is sufficient only when the configured provider set requires `deepseek` and does not also require another missing provider key.
- `taskmaster_normalization` — meta-task detection and suspicious task IDs in queue
- `process_check` — PID liveness for loop, supervisor, and child processes
- `version` — local version, commit, repo path
- `update_status` — ahead/behind metadata (local-only, no `git fetch`)
- `ok` — composite boolean (all checks pass)

Fallback from the repo root:

```bash
bash -n opencode-loop.sh
command -v opencode && command -v jq && command -v git
```

On Windows hosts, run validation in WSL:

```powershell
wsl -d Ubuntu -- bash -lic 'cd /mnt/.../opencode-loop && bash bin/test.sh'
```

### 2. Initialize The Target

```bash
opencode-loop init --dir /path/to/target --mode dev
opencode-loop init --dir /path/to/target --mode ml
```

Fallback:

```bash
bash bin/setup.sh --dir /path/to/target --mode dev
```

Setup creates `.opencode-loop/program.md`, `.opencode-loop/state.json`, `.opencode-loop/control.json`, `.opencode-loop/runtime.json`, `.opencode-loop/progress.txt`, and `opencode.json`.

### 3. Start The Loop

Use wrapper profiles first:

```bash
opencode-loop start --dir /path/to/target --profile quick
opencode-loop start --dir /path/to/target --profile long
```

Use the core script when the user needs advanced flags:

```bash
bash opencode-loop.sh --dir /path/to/target --mode dev --iterations 5 --timeout 15 --auto-reset
```

For longer runs, prefer the supervisor:

```bash
opencode-loop next-command --dir /path/to/target --kind supervisor --profile long
opencode-loop supervisor --dir /path/to/target --profile long
```

On macOS, Codex Desktop handoff, SSH, or any session that might lose its parent shell, do not rely on `nohup ... &` for long execute runs. Generate a tmux-backed supervisor command instead:

```bash
opencode-loop next-command --dir /path/to/target --kind supervisor --profile execute --wrap tmux --tmux-session target-loop
```

That command keeps the supervisor parent alive after the current terminal/session disconnects. For `execute` profile, tmux-wrapped `next-command` defaults stale detection to `1440` minutes; override with `--stale-minutes N` only after confirming the target's verification time.

Key core-script flags:

- `--iterations N` — cap unattended loop length.
- `--timeout MIN` — per-iteration timeout.
- `--mode dev|ml|execute` — route selection.
- `--program FILE` — custom program prompt.
- `--auto-reset` — reset circuit breaker on startup.
- `--session-mode single|multi|auto|clean` — session strategy.
- `--session-rotate N` — iterations per session in multi mode.

### 4. Monitor

Use `status --json` as the primary summary view — it merges all runtime state into one JSON object:

```bash
opencode-loop status --dir /path/to/target --json
```

The JSON output includes:
- `state` — iteration count, status, session ID from `state.json`
- `runtime` — PID, process state, active config, last exit reason from `runtime.json`
- `control` — desired state (running/stopped) and pending config from `control.json`
- `circuit_breaker` — breaker state (closed/open/half_open) from `circuit_breaker.json`
- `process_check` — PID liveness for loop, supervisor, and child processes
- `process_alive` — convenience boolean: is the main loop process actually running?
- `warning` — stale-running detection (state says running but process is dead)
- `logs` — paths to `progress.txt`, `supervisor.log`, `supervisor-child.log`

Do not treat `status --json` as liveness ground truth by itself. When a run looks stuck or inconsistent, use this order:

1. `ps` / PID check
2. Latest `output-*.jsonl` — the closest thing to the live execution stream
3. `supervisor-child.log` / `supervisor.log`
4. `state.json` / `runtime.json` / `progress.txt`

```bash
opencode-loop logs --dir /path/to/target --file progress --tail 80
opencode-loop logs --dir /path/to/target --file output --tail 80
opencode-loop logs --dir /path/to/target --file stderr --tail 80
opencode-loop logs --dir /path/to/target --file hook --match gate-review --tail 80
opencode-loop logs --dir /path/to/target --file gate --match policy --tail 80
```

Target-side state lives under `.opencode-loop/progress.txt`, `.opencode-loop/state.json`, `.opencode-loop/runtime.json`, `.opencode-loop/logs/`, `.opencode-loop/output-*.jsonl`, and `.opencode-loop/stderr-*.log`.

### 5. Optional Hooks

Normal hooks run shell commands at pre/post iteration boundaries. They are useful for external review or side checks and never stop the loop when exhausted. Do not confuse these with execute mode's `gate-review` blocking gate hook: that hook is consumed by the review gate, and a missing or failing `gate-review` makes the gate unavailable/fail instead of merely warning.

**Detect reviewer commands before adding hooks.** Commands vary across machines:

```bash
# Detect Kimi CLI (may be `kimi` or `kimi-code`)
KIMI_CMD=$(command -v kimi-code 2>/dev/null || command -v kimi 2>/dev/null || echo "")
CLAUDE_CMD=$(command -v claude 2>/dev/null || echo "")
CODEX_CMD=$(command -v codex 2>/dev/null || echo "")
```

```bash
opencode-loop hooks add --dir /path/to/target --event pre_iteration \
  --name kimi-ui --command "$KIMI_CMD --dir \"\$OPENCODE_LOOP_TARGET_DIR\" \"Review UI\"" --attempts 3
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name codex-review --command 'codex exec --cd "$OPENCODE_LOOP_TARGET_DIR" "Review"' --attempts 3
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name claude-review --command 'claude -p --cwd "$OPENCODE_LOOP_TARGET_DIR" "Review code changes."' --attempts 3
opencode-loop hooks list --dir /path/to/target --json
```

**Validate hooks in two layers.** `hooks test` may hang on slow reviewers — validate the reviewer command directly first:

```bash
# Layer 1: Validate reviewer produces valid output independently
$KIMI_CMD --print --final-message-only --cwd /path/to/target "Output ONLY JSON: {\"result\":\"pass\"}"
# Expected: {"result":"pass"}

# Layer 2 (supplementary): hooks test confirms wiring
# Use a timeout — it can hang if the reviewer takes >30s
timeout 120 opencode-loop hooks test --dir /path/to/target --event post_iteration --iteration 0
```

Do not treat `hooks test` as the sole gate-keper for hook readiness. If Layer 1 passes but Layer 2 hangs, the hook is still functional.

For the complete three-layer pipeline (OpenSpec → Task Master → opencode-loop), see `references/full-auto-pipeline.md`.

## Queue-Gated Execute Mode

Use `--mode execute` when the user has a structured task list and wants each task verified through gates before proceeding. This route is strict by design: imported tasks start as `draft`, need enrichment, then promotion, then execution.

### When To Use Execute Mode

- OpenSpec `tasks.md` should be executed task-by-task.
- Task Master `tasks.json` should be imported and run sequentially.
- A markdown checklist should become a gated queue.
- The user asks for queue mode, gated execution, acceptance gates, or task-by-task autopilot.

### 1. Import Tasks Into `queue.json`

Use `opencode-loop plan` to convert existing task artifacts into `queue.json`:

| Mode | When to use | What it reads | Prerequisites |
|------|-------------|---------------|---------------|
| `--manual` | Plain markdown checklist | Any `.md` with `- [ ]` checkboxes | None |
| `--from-openspec` | Existing OpenSpec change | `openspec/changes/<name>/tasks.md` + `proposal.md` | Change directory exists |
| `--from-taskmaster` | Existing Task Master database | `.taskmaster/tasks/tasks.json` | Task Master file exists |

```bash
echo "- [ ] Implement user login
- [ ] Add JWT middleware
- [ ] Write integration tests" > requirements.md
opencode-loop plan --dir /path/to/target --manual --input requirements.md

opencode-loop plan --dir /path/to/target --from-openspec --change my-feature
opencode-loop plan --dir /path/to/target --from-taskmaster --tag my-project
```

The Task Master adapter already handles `.master.tasks[]` automatically; do not hand-roll a parser around Task Master output.

For `--from-form` and `--manual`, keep the temporary input file outside the target repo, such as `/tmp/task-form.json` or `/tmp/requirements.md`. If an import artifact is left untracked inside the target repo, execute mode's dirty-worktree protection can block before the first task starts. `plan` can replace the empty execute placeholder queue created by `init --mode execute`, but it must not overwrite a non-empty queue.

### 2. Enrich Tasks

Imported tasks need the task-level contract filled in before execution. Task Master imports usually carry `verification` from `testStrategy`, but `acceptance_checks` still need attention.

Add for each task:

- `verification` — project-specific commands that must pass.
- `acceptance_checks` — objective checks using `command`, `file_exists`, or `contains`.
- `verification_optional: true` — only when an empty verification list is intentionally allowed.
- `review_required: true` — **MANDATORY for the review gate to participate in gate decisions.** The gate-review hook alone is NOT sufficient — if the task's `review_required` is false (and the queue profile's `reviewer_required` is also false), the review gate will be skipped even if the hook is attached and runs. Always verify both levels:
  ```bash
  # Task-level check
  jq '.tasks[] | select(.id == "tm-1") | .review_required // "unset"' queue.json
  # Profile-level fallback
  jq '.profile.reviewer_required // false' queue.json
  ```
- `tdd_required: true` — to enable the TDD gate.

Use project-neutral verification: discover the project's real test/lint/build command first, then assign per-task checks. Do not assume `npm test` exists.

Finish enrichment before the task becomes `in_progress`; execute prompts are captured at task selection time. Updating an active task can still harden gates, but it does not rewrite the prompt already handed to OpenCode. If a command acceptance check inspects a committed task diff, compare `HEAD^ HEAD` rather than plain `HEAD`.

```bash
jq '(.tasks[] | select(.id == "openspec-1-1") | .verification) = ["make test"]' \
  /path/to/target/.opencode-loop/queue.json > /tmp/q.tmp && mv /tmp/q.tmp /path/to/target/.opencode-loop/queue.json

jq '(.tasks[] | select(.id == "openspec-1-1") | .acceptance_checks) = [{"type":"file_exists","path":"src/auth.ts"}]' \
  /path/to/target/.opencode-loop/queue.json > /tmp/q.tmp && mv /tmp/q.tmp /path/to/target/.opencode-loop/queue.json
```

### 3. Promote Tasks

Promote tasks one at a time:

```bash
opencode-loop queue status --dir /path/to/target --json
opencode-loop queue validate --dir /path/to/target
opencode-loop queue promote --dir /path/to/target --task openspec-1-1
opencode-loop queue promote --dir /path/to/target --task openspec-1-2
```

Promotion checks queue integrity and valid verification configuration.

### 4. Initialize And Start

```bash
opencode-loop init --dir /path/to/target --mode execute
opencode-loop start --dir /path/to/target --profile execute

bash opencode-loop.sh --dir /path/to/target --mode execute --iterations 30 --timeout 60 --session-mode multi --session-rotate 5 --auto-reset
```

Gate order stays fixed:

1. Policy
2. Verification
3. Review (optional)
4. Acceptance
5. TDD (optional)

The review gate requires a `post_iteration` hook named exactly `gate-review`, whose last stdout line is one of:

- `{"result":"pass"}`
- `{"result":"needs_changes"}`
- `{"result":"reject"}`

### 5. Manage Queue Progress

```bash
opencode-loop queue status --dir /path/to/target --json
opencode-loop queue show --dir /path/to/target --task openspec-1-1 --json
opencode-loop queue next --dir /path/to/target
opencode-loop queue set-status --dir /path/to/target --task openspec-1-1 --status todo --reason "retrying"
```

Use `jq` with atomic temp-then-rename writes for queue edits not exposed by the CLI.

### 6. Isolation And Emergency Flags

- `"isolation": "none" | "worktree" | "branch"`
- `"integration_strategy": "fast_forward_merge" | "branch_chain" | "manual"`

Core-script emergency flags:

```bash
bash opencode-loop.sh --dir /path/to/target --mode execute --skip-gates review,tdd
bash opencode-loop.sh --dir /path/to/target --mode execute --unsafe-skip-baseline-gates
```

### Worktree Isolation Lifecycle

When `profile.isolation` is `worktree`, each queue task runs in an isolated Git worktree. The loop's `isolation_manager.sh` handles creation, cleanup, and integration automatically — but when an agent needs to manually manage worktrees (for recovery, continuation, or inspection), follow this lifecycle.

#### Recovery From Interrupted Worktree Creation

If `git worktree add -b <branch>` was killed mid-operation (SIGKILL, timeout, `index.lock` blockage), the branch may exist but the worktree directory may be missing or unregistered. Recovery:

```bash
TASK_ID="tm-8"
BRANCH="task/${TASK_ID}"
WORKTREE_PATH="/path/to/target/.opencode-loop/worktrees/${TASK_ID}"

# Step 1: Clear stale index.lock (use git rev-parse for worktree-safe path)
LOCK=$(git -C /path/to/target rev-parse --git-path index.lock 2>/dev/null || true)
if [[ -f "$LOCK" ]]; then
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -f "[g]it.*target" >/dev/null 2>&1 && echo "active lock" || rm -f "$LOCK"
  else
    PS_OUT=$(ps aux 2>/dev/null || true)
    if [[ -z "$PS_OUT" ]] || echo "$PS_OUT" | grep -q "[g]it.*target"; then
      echo "cannot confirm liveness — not removing lock"
    else
      rm -f "$LOCK"
    fi
  fi
fi

# Step 2: Inspect current state
git -C /path/to/target worktree list
git -C /path/to/target branch --list "$BRANCH"

# Step 3: Re-bind existing branch OR create fresh (conditional)
if git -C /path/to/target show-ref --verify "refs/heads/$BRANCH" 2>/dev/null &&
   ! git -C /path/to/target worktree list | grep -qF "$WORKTREE_PATH"; then
  git -C /path/to/target worktree add "$WORKTREE_PATH" "$BRANCH"
else
  git -C /path/to/target worktree add "$WORKTREE_PATH" -b "$BRANCH" HEAD
fi
```

If the loop's `isolation_manager.sh` refuses to delete a branch with unique commits, you must manually decide: (a) integrate the commits into base with `git checkout main && git merge --ff-only task/<id>`, or (b) re-bind the branch to a worktree path with `git worktree add <path> task/<id>`. Do not force-delete branches with unmerged work.

#### State Migration To New Worktree

New worktrees carry only Git-tracked files — not the `.opencode-loop/` runtime state from the original tree. To continue a paused queue in a new worktree:

```bash
OLD="/path/to/original-target"
NEW="/path/to/new-worktree"

opencode-loop init --dir "$NEW" --mode execute

cp "$OLD/.opencode-loop/queue.json"   "$NEW/.opencode-loop/"
cp "$OLD/.opencode-loop/program.md"   "$NEW/.opencode-loop/"
cp "$OLD/.opencode-loop/hooks.json"   "$NEW/.opencode-loop/"

# Reset stuck tasks to retryable
opencode-loop queue set-status --dir "$NEW" --task tm-8 --status todo --reason "continuing in new worktree"
```

#### Dependency Installation Before Execute

New worktrees start with no runtime dependencies. Install them before starting the loop:

```bash
cd /path/to/new-worktree
npm install          # Node.js
# pip install -r requirements.txt   # Python
# bundle install                     # Ruby
opencode-loop doctor --dir . --json
# Run project baseline tests
```

#### Full Continuation Checklist

After creating a worktree for execution continuation:

1. Create/add worktree with recovery checks (index.lock, branch state)
2. Install project dependencies
3. `opencode-loop doctor --dir <worktree> --json` to validate
4. Run project baseline tests to verify environment health
5. Migrate `.opencode-loop/` runtime state (`queue.json`, `program.md`, `hooks.json`)
6. Reset tasks to appropriate statuses
7. `opencode-loop start --dir <worktree> --profile execute`

#### Post-Commit / Post-Task Repo Cleanliness

After a task commits changes but before the loop finalizes the iteration, repo-visible runtime files (`opencode.json`) may show as uncommitted. (`.opencode-loop/` is already gitignored by `setup.sh` — it's `opencode.json` in the project root that causes the problem.) When this is detected with no active task, the loop immediately exits with `environment_blocked` status (exit code 6) — it does NOT spin or retry.

Resolution:

```bash
git status --porcelain
# If the only dirty file is opencode.json (everything else is clean or under .gitignore):

# Option A: Ensure opencode.json is in .gitignore (preferred, one-time fix)
grep -q "^opencode.json$" .gitignore 2>/dev/null || echo "opencode.json" >> .gitignore

# Option B: Absorb the runtime config change into the task's cleanup commit
git add opencode.json && git commit --amend --no-edit

# Option C: Discard the runtime noise
git checkout -- opencode.json
```

This is not a task-execution failure — the task's code changed successfully, but `opencode.json` was rewritten by runtime and left dirty. The loop correctly detects this and exits cleanly rather than spinning. Option A is preferred; verify `.gitignore` has `opencode.json` before starting long unattended runs.

### Failure / Recovery

| Symptom | Check | Fix |
|---------|-------|-----|
| `doctor --json` shows `ok: false` | Missing `opencode`, `jq`, or `git` | Install missing dependency |
| Circuit breaker OPEN | 3+ no-progress or 5+ errors | `--auto-reset` on next start, or wait 30min cooldown |
| Task stuck `rejected` | `queue show --task ID --json` | Fix gate failure, `queue set-status --task ID --status todo --reason "retry"` |
| Stale `index.lock` blocks worktree ops | `.git/index.lock` exists, no git process | `rm -f .git/index.lock` |
| Worktree: branch exists, path missing | `git branch` shows branch, `git worktree list` doesn't | `git worktree add <path> <branch>` (re-bind) |
| "Dirty working tree with no active task" | Completed task, `opencode.json` dirty | Loop exits `environment_blocked` (code 6). Gitignore `opencode.json` or absorb into commit |
| Rate limit hit | 100 calls/hour | Wait, or check `rate_limit.json` |
| Supervisor says stale | No activity for `--stale-minutes` | Check `supervisor.log` |
| WSL hooks can't find CLI | CLIs not in WSL PATH | Symlink: `ln -s $(which claude.exe) /usr/local/bin/claude` |
| `plan` refuses overwrite | `queue.json` exists | Delete before re-import |
| macOS `declare -A` error | `/bin/bash` is 3.2 | `brew install bash`, PATH priority |

For the complete three-layer pipeline (OpenSpec → Task Master → opencode-loop), see `references/full-auto-pipeline.md`.

## TUI Workflow

Use this route when the user wants the visual control plane.

### 1. Prepare Inputs

Prepare:

- Target path.
- Recommended mode.
- Suggested iteration cap and timeout.
- Short goal statement and acceptance criteria.
- Any custom program file path.
- Notes about the tests or commands the agent should run.

### 2. Launch The TUI

Unix / WSL:

```bash
bash bin/opencode-loop-tui.sh --dir /path/to/target
```

macOS:

```bash
open "/Volumes/SDD2T/obsidian-vault-write/open-source-project/autonomous-ai-agents/agent-loops/opencode-loop/OpenCode Loop TUI.command"
```

Windows:

```powershell
& ".\OpenCode Loop TUI (WSL).cmd" "C:\path\to\target"
```

The Windows TUI frontend runs natively while setup and loop actions still execute through WSL.

### 3. Tell The User What To Fill

- Target directory.
- Mode: `dev`, `ml`, or `execute`.
- Iterations: start small, then increase.
- Timeout: 15 minutes by default, longer for heavy builds.
- Program: leave default unless a custom plan file is ready.
- Controls: pause/resume/stop at iteration boundaries.

## Safety And Boundaries

- Start with a small iteration cap before long unattended runs.
- Avoid broad destructive requests unless the user clearly intends them.
- Keep persisted loop state under the target project's `.opencode-loop/`.
- Preserve atomic JSON write semantics when editing loop internals.
- Never replace structured JSON exit detection with keyword guessing.
- Do not put API keys, credentials, or tokens into prompts, logs, or checked-in config.
- Set the API key in the target project's `.env` file (ensure `.env` is in `.gitignore`):
  - `OPENAI_COMPATIBLE_API_KEY=<your-key>` for `--openai-compatible` providers
  - `ANTHROPIC_API_KEY=<your-key>` for Anthropic
  - `DEEPSEEK_API_KEY=<your-key>` for native `deepseek`
- `provider_keys.ok` is evaluated against the configured provider set detected from the target `opencode.json`. If no provider is configured, all catalog keys are required; if providers are configured, only those providers' keys are required. Therefore `DEEPSEEK_API_KEY` being detected does not by itself make preflight pass when the target config also names OpenAI, Anthropic, or OpenAI-compatible without their keys.
- In execute mode, imported tasks start as `draft` and require enrichment plus explicit promotion before execution.

## Final Response Pattern

When handing off:

- **Route** — command-line, execute, or TUI.
- **Prepared** — target path, mode, brief or task artifact, setup status.
- **Run** — exact command or exact TUI fields.
- **Monitor** — state/log locations to watch.
- **Next step** — start, continue, inspect failure, or increase iterations.

Keep the response concise and action-oriented. Include exact paths and commands.
