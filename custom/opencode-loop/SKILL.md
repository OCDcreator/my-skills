---
name: opencode-loop
description: "Use when the user wants opencode-loop unattended or self-running multi-iteration coding over a target project: run build-verify-fix cycles, optimize/refactor repos, fix test/lint/type failures, or bootstrap projects. Trigger on phrases like 无人值守, 自动循环, 自动修 bug, 让大模型自己跑, overnight coding, autopilot coding, supervisor watchdog, self-healing loop, 全自动流水线, 从需求到代码. Also trigger for queue-gated execute mode with verification/acceptance gates, task-by-task gated execution, OpenSpec/Task Master adapter import, gate failures and retries. Do not trigger for one-shot debugging, generic for/while loops, or CI/CD pipeline setup."
---

# OpenCode Loop Skill

Use this skill to turn a natural language requirement into an autonomously executed project. The default workflow is the **Full Auto Pipeline**: you receive a requirement, structure it with OpenSpec, decompose it with Task Master, then execute each task through opencode-loop's gated queue — without asking the user to choose modes or run individual commands.

## How This Skill Works

When the user gives you a requirement (e.g., "帮我写一个计算器库", "build a REST API", "add auth to my app"), you do this automatically:

⚠️ HARD CONSTRAINT: When this skill triggers, the Full Auto Pipeline overrides any generic brainstorming, design Q&A, or route-selection flow. Do NOT ask "which mode?" or start a design conversation. Read `references/full-auto-pipeline.md` and begin executing Layer 0 (feature branch) immediately. Only ask for clarification if the target project path is missing or the requirement is genuinely ambiguous.

**NEVER run the pipeline on the main/master branch.** Always create a feature branch first (`git checkout -b feat/<name>`). All pipeline work — bootstrap, execute, commits — must stay on a dedicated branch. Main must remain clean.

1. **Read `references/full-auto-pipeline.md`** — it contains the complete three-layer workflow. Load it now and follow it end-to-end.
2. **Execute Layer 0** — `git checkout -b feat/<name>` on the target project.
3. **Execute Layer 1** (OpenSpec) — `openspec init`, `openspec new change`, then YOU write the proposal.
4. **Execute Layer 2** (Task Master) — `task-master init --yes`, `task-master parse-prd`, configure AI provider if needed.
5. **Execute Layer 3** (opencode-loop) — `plan --from-taskmaster`, enrich tasks, set `profile.isolation = "branch"`, promote, `init --mode execute`, start.
6. **Hand off** the running loop to the user with monitoring instructions.

Do NOT ask "which mode?" or "which route?" when the user gives a requirement. Just start the pipeline. Only ask for clarification if the target project path is unclear or the requirement is genuinely ambiguous.

The three routes exist for users who explicitly request them:
- **`dev` / `ml`** — user says "run opencode-loop in dev mode" or wants open-ended iteration without structured tasks.
- **Queue-gated `execute`** — user already has a tasks file and wants to skip OpenSpec/Task Master.
- **TUI** — user explicitly asks for the visual control plane.

## Before Starting

Clarify if unclear:

- Target project path (required).
- Safety boundary: files or directories the loop must not modify.
- Feature branch name (required for Full Auto Pipeline — the pipeline must NEVER run on main).

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
5. Keep secrets out of prompts, config checked into Git, logs, and `.opencode-loop/`.

## Command-Line Workflow (`dev` / `ml`)

Use this route for open-ended unattended runs.

### 1. Preflight

```bash
opencode-loop --version
opencode-loop doctor --dir /path/to/target --json
```

#### Script Permission Self-Check

```bash
# Before running any bin/*.sh wrapper, ensure it is executable:
ls -l bin/opencode-loop-plan.sh 2>/dev/null || true
# If not executable, fix:
chmod +x bin/opencode-loop-plan.sh
# Or fallback:
bash bin/opencode-loop-plan.sh --dir /path/to/target --from-taskmaster --tag tm
```

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

Key core-script flags:

- `--iterations N` — cap unattended loop length.
- `--timeout MIN` — per-iteration timeout.
- `--mode dev|ml|execute` — route selection.
- `--program FILE` — custom program prompt.
- `--auto-reset` — reset circuit breaker on startup.
- `--session-mode single|multi|auto|clean` — session strategy.
- `--session-rotate N` — iterations per session in multi mode.

### 4. Monitor

```bash
opencode-loop status --dir /path/to/target --json
opencode-loop logs --dir /path/to/target --file progress --tail 80
```

Target-side state lives under `.opencode-loop/progress.txt`, `.opencode-loop/state.json`, `.opencode-loop/runtime.json`, `.opencode-loop/logs/`, `.opencode-loop/output-*.jsonl`, and `.opencode-loop/stderr-*.log`.

## Monitoring And Health Checks

### Health Check Priority Order

When checking if the loop is alive and healthy, use this priority order:

1. **Process check** (ground truth):
   ```bash
   ps aux | grep -E 'opencode|opencode-loop' | grep -v grep
   ```
2. **Output file activity** (real execution flow):
   ```bash
   ls -lt /path/to/target/.opencode-loop/output-*.jsonl | head -5
   tail -20 /path/to/target/.opencode-loop/output-*.jsonl
   ```
3. **Supervisor child log** (loop boundary events):
   ```bash
   tail -50 /path/to/target/.opencode-loop/supervisor-child.log
   ```
4. **state.json / runtime.json** (high-level status — may be stale after forced stop):
   ```bash
   opencode-loop status --dir /path/to/target --json
   ```

⚠️ `status --json` is NOT the ground truth for liveness. After forced stop, state.json may still show `running`. Always cross-reference with `ps` and output file timestamps.

### Stale State After Forced Stop

If you killed processes manually, state.json and runtime.json may retain stale values (`status: running`, old PID). To reconcile:

```bash
# Check if process is truly dead
ps -p "$(jq -r '.pid // 0' /path/to/target/.opencode-loop/runtime.json)" 2>/dev/null && echo "ALIVE" || echo "DEAD"

# If dead, reset state manually
jq '.status = "stopped" | .iteration = 0' /path/to/target/.opencode-loop/state.json > /tmp/s.tmp && mv /tmp/s.tmp /path/to/target/.opencode-loop/state.json
jq '.process_state = "stopped" | .last_exit_reason = "killed"' /path/to/target/.opencode-loop/runtime.json > /tmp/r.tmp && mv /tmp/r.tmp /path/to/target/.opencode-loop/runtime.json
```

### 5. Optional Hooks

Hooks run shell commands at pre/post iteration boundaries. They are useful for external review or side checks and never stop the loop when exhausted.

```bash
opencode-loop hooks add --dir /path/to/target --event pre_iteration \
  --name kimi-ui --command 'kimi-code --dir "$OPENCODE_LOOP_TARGET_DIR" "Review UI"' --attempts 3
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name codex-review --command 'codex exec --cd "$OPENCODE_LOOP_TARGET_DIR" "Review"' --attempts 3
opencode-loop hooks add --dir /path/to/target --event post_iteration \
  --name claude-review --command 'claude -p --cwd "$OPENCODE_LOOP_TARGET_DIR" "Review code changes."' --attempts 3
opencode-loop hooks list --dir /path/to/target --json
opencode-loop hooks test --dir /path/to/target --event post_iteration --iteration 0
```

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

### 2. Enrich Tasks

Imported tasks need the task-level contract filled in before execution. Task Master imports usually carry `verification` from `testStrategy`, but `acceptance_checks` still need attention.

Add for each task:

- `verification` — project-specific commands that must pass.
- `acceptance_checks` — objective checks using `command`, `file_exists`, or `contains`.
- `verification_optional: true` — only when an empty verification list is intentionally allowed.
- `review_required: true` — to enable the review gate.
- `tdd_required: true` — to enable the TDD gate.

Use project-neutral verification: discover the project's real test/lint/build command first, then assign per-task checks. Do not assume `npm test` exists.

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

⚠️ IMPORTANT: Before starting execute mode, verify TWO conditions:
1. `control.json.desired_state` must be `"running"` — if not, set it:
   ```bash
   jq '.desired_state = "running"' /path/to/target/.opencode-loop/control.json > /tmp/c.tmp && mv /tmp/c.tmp /path/to/target/.opencode-loop/control.json
   ```
2. Git worktree must be clean, OR there must be an active task accepting the dirty changes:
   ```bash
   git -C /path/to/target status --porcelain
   ```
If the tree is dirty with no active task, commit bootstrap assets first.

```bash
opencode-loop init --dir /path/to/target --mode execute
opencode-loop start --dir /path/to/target --profile execute

bash opencode-loop.sh --dir /path/to/target --mode execute --iterations 20 --auto-reset
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

### Failure / Recovery

| Symptom | Check | Fix |
|---------|-------|-----|
| `doctor --json` shows `ok: false` | Missing `opencode`, `jq`, or `git` | Install missing dependency |
| Circuit breaker OPEN | 3+ no-progress or 5+ errors | `--auto-reset` on next start, or wait 30min cooldown |
| Task stuck `rejected` | `queue show --task ID --json` | Fix gate failure, `queue set-status --task ID --status todo --reason "retry"` |
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

## Bootstrap → First Execute Handoff

The Full Auto bootstrap creates files that make the working tree dirty. The execute loop will refuse to start new tasks on a dirty tree with no active task. This is the most counter-intuitive step. Follow this exact sequence:

1. **Create a feature branch first** — NEVER run the pipeline on main:
    ```bash
    cd /path/to/target
    git checkout -b feat/my-feature
    ```
    All pipeline work (bootstrap, execute, commits) stays on this branch. Main remains clean. The user can review and merge when satisfied.

2. After `plan --from-taskmaster`, enrich tasks, and promote them.

3. **Set queue isolation** to prevent tasks from touching the same branch:
    ```bash
    QUEUE="/path/to/target/.opencode-loop/queue.json"
    jq '.profile.isolation = "branch" | .profile.integration_strategy = "branch_chain"' \
      "$QUEUE" > "${QUEUE}.tmp" && mv "${QUEUE}.tmp" "$QUEUE"
    ```

4. **Commit all bootstrap assets** before starting execute:
    ```bash
    cd /path/to/target
    git add openspec/ .taskmaster/ opencode.json
    # program.md lives inside .opencode-loop/ which is gitignored; skip it
    # Also add any agent config files that were created:
    git add .claude/ .gemini/ .opencode/ 2>/dev/null || true
    git commit -m "chore: bootstrap opencode-loop pipeline artifacts"
    ```
5. Verify worktree is clean:
    ```bash
    git status --porcelain
    ```
6. Verify `control.json.desired_state == "running"`.
7. **Now** start execute:
    ```bash
    opencode-loop init --dir /path/to/target --mode execute
    opencode-loop start --dir /path/to/target --profile execute
    ```
8. **Immediately after start**, check if runtime wrote back config changes:
    ```bash
    git -C /path/to/target status --porcelain
    ```
    If only safe config normalization (e.g., `$schema` in opencode.json), do one more commit:
    ```bash
    git add -A && git commit -m "chore: runtime config normalization"
    ```

When all tasks complete, the feature branch contains all pipeline commits. The user can review with `git log main..feat/my-feature --oneline` and merge with `git checkout main && git merge feat/my-feature`.

## Safety And Boundaries

### Repo Assets vs Local Runtime State

**Repo assets** (survive across machines, safe to commit):
- `openspec/` — change proposals and specifications
- `.taskmaster/` — task database
- `opencode.json` — OpenCode configuration
- `.claude/`, `.gemini/`, `.opencode/` — agent instructions (if created)

**Local runtime state** (machine-specific, gitignored, do NOT commit):
- `.opencode-loop/queue.json` — execution queue
- `.opencode-loop/control.json` — pause/resume/stop state
- `.opencode-loop/runtime.json` — PID and process state
- `.opencode-loop/state.json` — iteration tracking
- `.opencode-loop/output-*.jsonl` — raw NDJSON output
- `.opencode-loop/logs/` — execution logs
- `.opencode-loop/circuit_breaker.json`, `rate_limit.json`

### Runtime Config Writeback

After starting execute mode, the OpenCode runtime may normalize `opencode.json` (e.g., adding `$schema`). This can make the tree dirty again even after a clean bootstrap commit. Always re-check `git status` immediately after first execute start and handle any safe writebacks.

### Expected Bootstrap Artifacts

When running the Full Auto Pipeline, the following files WILL be created in the target project. This is normal and expected:

| Tool | Files Created | Commit? |
|------|--------------|---------|
| `openspec init` | `.claude/`, `.gemini/`, `.opencode/` | Yes, if they contain project instructions |
| `openspec new change` | `openspec/changes/<name>/` | Yes |
| `task-master init` | `.taskmaster/`, `.env.example` | Yes |
| `opencode-loop init` | `opencode.json`, `.opencode-loop/program.md` | Yes for `opencode.json` only (`program.md` is gitignored) |
| Runtime (first start) | `.opencode-loop/` (state, runtime, logs, queue) | No — gitignored local runtime |

- Start with a small iteration cap before long unattended runs.
- Avoid broad destructive requests unless the user clearly intends them.
- Keep persisted loop state under the target project's `.opencode-loop/`.
- Preserve atomic JSON write semantics when editing loop internals.
- Never replace structured JSON exit detection with keyword guessing.
- Do not put API keys, credentials, or tokens into prompts, logs, or checked-in config.
- Set the API key in the target project's `.env` file (ensure `.env` is in `.gitignore`):
  - `OPENAI_COMPATIBLE_API_KEY=<your-key>` for `--openai-compatible` providers
  - `ANTHROPIC_API_KEY=<your-key>` for Anthropic
- In execute mode, imported tasks start as `draft` and require enrichment plus explicit promotion before execution.

## Final Response Pattern

When handing off:

- **Route** — command-line, execute, or TUI.
- **Prepared** — target path, mode, brief or task artifact, setup status.
- **Run** — exact command or exact TUI fields.
- **Monitor** — state/log locations to watch.
- **Next step** — start, continue, inspect failure, or increase iterations.

Keep the response concise and action-oriented. Include exact paths and commands.
