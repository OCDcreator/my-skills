---
name: opencode-loop
description: "Use when the user wants opencode-loop unattended or self-running multi-iteration coding over a target project: run build-verify-fix cycles, optimize/refactor repos, fix test/lint/type failures, or bootstrap projects. Trigger on phrases like 无人值守, 自动循环, 自动修 bug, 让大模型自己跑, overnight coding, autopilot coding, supervisor watchdog, self-healing loop, 全自动流水线, 从需求到代码. Also trigger for queue-gated execute mode with verification/acceptance gates, task-by-task gated execution, OpenSpec/Task Master adapter import, gate failures and retries. Do not trigger for one-shot debugging, generic for/while loops, or CI/CD pipeline setup."
---

# OpenCode Loop Skill

Use this skill to help the user run the local `opencode-loop` project as an unattended orchestrator over a target project. It fits repeated model iterations: bootstrapping, backlog execution, refactoring, bug fixing, test repair, lint/type cleanup, or ML experiment loops.

OpenCode Loop has three routes:

- **Command-line `dev` / `ml`** — open-ended unattended work.
- **Queue-gated `execute`** — task-by-task execution with mandatory gates.
- **TUI** — visual control plane for setup, monitoring, and multi-project supervision.

## First Decide The Route

Choose a route early:

- **Command-line `dev` / `ml`** when the user wants the loop to run directly from a broad goal.
- **Queue-gated `execute`** when the user has structured tasks and wants every task verified before the next one starts.
- **TUI** when the user wants a visual workflow or to supervise multiple targets.
- If the user does not choose, default to command-line `dev` and mention `execute` and TUI as alternatives.

Clarify before starting:

- Target project path, or whether a new project should be created.
- Goal statement: what should be built, improved, fixed, or investigated.
- Mode: `dev`, `ml`, or `execute`.
- Stop condition: iteration cap, tests to pass, acceptance criteria, or explicit completion signal.
- Safety boundary: files or directories the loop must not modify, and secrets to avoid.

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
- In execute mode, imported tasks start as `draft` and require enrichment plus explicit promotion before execution.

## Final Response Pattern

When handing off:

- **Route** — command-line, execute, or TUI.
- **Prepared** — target path, mode, brief or task artifact, setup status.
- **Run** — exact command or exact TUI fields.
- **Monitor** — state/log locations to watch.
- **Next step** — start, continue, inspect failure, or increase iterations.

Keep the response concise and action-oriented. Include exact paths and commands.
