---
name: opencode-loop
description: "Use when the user wants opencode-loop — a Python-powered unattended coding engine — to run self-healing multi-iteration coding over a target project. Trigger on: 无人值守, 自动循环, 自动修 bug, overnight coding, autopilot coding, self-healing loop, run opencode-loop, start the loop, gated queue, circuit breaker, orphaned task, heartbeat install, worktree isolation, build-verify-fix cycles, verification/acceptance gates. Do not trigger for one-shot debugging, generic loops, or CI/CD pipeline setup."
---

# OpenCode Loop Skill

Use this skill to turn a natural language requirement into an autonomously executed project. The default workflow is the **Full Auto Pipeline**: you receive a requirement, structure it with OpenSpec, decompose it with Task Master, then execute each task through opencode-loop's gated queue — without asking the user to choose modes or run individual commands.

## How This Skill Works

When the user gives you a requirement (e.g., "帮我写一个计算器库", "build a REST API", "add auth to my app"), you do this automatically:

> **Summary** — these 6 steps are a high-level overview. `references/full-auto-pipeline.md` contains the complete three-layer workflow with all prerequisites, edge cases, and validation checkpoints. Load it before execution.

1. **Read `references/full-auto-pipeline.md`** — it contains the complete three-layer workflow. Load it now and follow it end-to-end.
2. **Execute Layer 1** (OpenSpec) — `openspec init`, `openspec new change`, then YOU write the proposal.
3. **Execute Layer 2** (Task Master) — `task-master init --yes`, `task-master parse-prd`, configure AI provider if needed.
4. **Execute Layer 3** (opencode-loop) — `plan --from-taskmaster`, enrich tasks, promote, `init --mode execute`, start.
5. **Install the outer self-healing guard** — run `opencode-loop heartbeat install --dir <target> --runner auto --interval-minutes 30` so a local cron/launchd heartbeat can wake Codex or OpenCode to repair `opencode-loop` itself.
6. **Hand off** the running loop to the user with heartbeat/status instructions.

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

**Pre-flight check:** Before starting any unattended run, ensure `opencode.json` is in the target project's `.gitignore`. `setup.sh` generates this file at runtime — if it is not gitignored, the loop exits with `environment_blocked` (exit code 6) after the first task commits. Verify with: `grep -q '^opencode.json$' /path/to/target/.gitignore || echo 'opencode.json' >> /path/to/target/.gitignore`

**Pipeline dependency check:** The Full Auto Pipeline needs `openspec` and `task-master`. If either is missing, do not pretend the pipeline ran; install/configure the missing CLI when appropriate, or fall back to a manual queue-gated execute run and say which layer was bypassed.

## Full Auto Workspace Policy

For Git-backed target projects, the Full Auto Pipeline must execute in a dedicated worktree, not the user's main workspace. Treat the main workspace as the final merge/verify/push location only. New imported execute queues default to `profile.isolation: "worktree"` and `profile.integration_strategy: "fast_forward_merge"`; keep those defaults unless the user explicitly requests in-place execution and accepts the risk.

Before starting a new goal, archive or reset stale runtime state (`.opencode-loop/queue.json`, `state.json`, `runtime.json`, logs) instead of silently resuming an old queue. Resume an existing queue only when the user explicitly asks to continue that queue and you have verified the current task/status from live state.

## Locate The Repo

When already inside the `opencode-loop` repository, use the current repo root. Otherwise locate it first:

- Prefer the global `opencode-loop` wrapper if it is installed.
- Ask for the local repo path if it is unknown.
- On macOS, use the native repo path directly.
- On Windows, prefer WSL for Bash-facing workflows.
- Known Windows repo pattern for this environment: `C:\Users\lt\Desktop\Write\open-source-project\autonomous-ai-agents\agent-loops\opencode-loop`.
- Requires Python >= 3.11; the engine uses only stdlib modules.
- The Python engine at `engine/` handles orchestration. Public Bash/PowerShell files are launchers only: `opencode-loop.sh` delegates to `python3 -m engine.loop`, and `bin/opencode-loop-cli.sh` delegates to `python3 -m engine.cli`.
- The migrated project should not contain an active `lib/*.sh` private orchestration layer or `engine.bridge` Bash-to-Python bridge. Treat either as a migration regression and verify against the current checkout before documenting or depending on it.

## Prefer The AI-Friendly CLI

Prefer the wrapper for repeatable agent work:

```bash
opencode-loop --version
opencode-loop doctor --dir /path/to/target --json
opencode-loop status --dir /path/to/target --json
opencode-loop next-command --dir /path/to/target --kind supervisor --profile long
opencode-loop next-command --dir /path/to/target --kind supervisor --profile execute --wrap tmux --tmux-session target-loop
opencode-loop heartbeat install --dir /path/to/target --runner auto --interval-minutes 30
opencode-loop heartbeat status --dir /path/to/target --json
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
python3 --version
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

Profile defaults match the original Bash behavior: `quick` = 3 iterations/15min/single session; `long` = 30/60/multi rotate 10; `ml` = 200/30/multi rotate 10; `execute` = 30/60/multi rotate 1 with 1440min stale detection.

Use the core script when the user needs advanced flags:

```bash
bash opencode-loop.sh --dir /path/to/target --mode dev --iterations 5 --timeout 15
```

Note: `--auto-reset` (circuit breaker reset on startup) is now the default. Use `--no-auto-reset` to opt out. All examples below omit it since it is implied.

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

### 4. Productized Cron/Heartbeat Guard

For any run the user expects to keep going unattended, the supervisor is necessary but not sufficient. Always add an outer cron/heartbeat guard unless the user explicitly declines it. This guard is responsible for cases where the shell, supervisor, controller repo, queue contract, or wrapper breaks and no local child process remains alive to self-restart.

Install the local scheduler:

```bash
opencode-loop heartbeat install --dir /path/to/target --runner auto --interval-minutes 30
```

`--runner auto` first tries `codex exec --cd <opencode-loop repo>` and falls back to `opencode run --dir <opencode-loop repo> -- "<prompt>"` if Codex is unavailable or out of quota. Use `--runner codex` or `--runner opencode` only when the user explicitly wants one runner. The scheduler calls a generated `run.sh`, which skips model calls while the target is genuinely healthy and only invokes a runner when status/observe/logs show an unhealthy loop or a progress trap. The executable scheduler copy and CLI snapshot live under the user's HOME heartbeat runtime so macOS launchd/cron does not need to execute controller scripts from external volumes; target-side `.opencode-loop/heartbeat/` keeps config and logs.

The generated repair prompt requires the runner to:

- inspect `status --json`, `observe --json`, and latest logs before acting;
- treat process liveness as necessary but not sufficient: a live loop repeatedly failing `gate-review`, accumulating rejected tasks, or requeueing the same phase is unhealthy even if `status.health` says `healthy`;
- leave only genuinely healthy runs alone and report exact task/process state;
- when progress is abnormal, pause blind relaunches, preserve task work, extract the latest `gate-review` JSON `reason` plus queue `last_error`, and turn that into a concrete repair objective for the next run;
- when broken, preserve task work, fix verified `opencode-loop` controller bugs first, run tests, prepend `docs/pitfalls-and-lessons.md`, commit, redeploy with `bash bin/install-cli.sh`, and resume the original queue with `--resume-existing-queue`;
- pause itself with `opencode-loop heartbeat pause --dir /path/to/target` only after the target task is truly complete.

Key core-script flags:

- `--iterations N` — cap unattended loop length.
- `--timeout MIN` — per-iteration timeout.
- `--mode dev|ml|execute` — route selection.
- `--program FILE` — custom program prompt.
- `--session-mode single|multi|auto|clean` — session strategy.
- `--session-rotate N` — iterations per session in multi mode.

### 5. Monitor

Use `status --json` as the primary summary view — it merges all runtime state into one JSON object:

```bash
opencode-loop status --dir /path/to/target --json
```

The JSON output merges all runtime state: `state`, `runtime`, `control`, `circuit_breaker`, `process_check`, `process_alive`, `warning`, `logs`.

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

Watch for abnormal progress, not only dead processes. These are heartbeat-worthy problems even while supervisor and child PIDs are alive:

- The same task/phase hits `Queue gate review needs_changes` repeatedly.
- `queue.json` has one or more `rejected` tasks while another task is `in_progress`.
- Progress shows `queue_inconsistent:rejected_exhausted` or repeated manual requeues.
- The latest hook log repeats the same reviewer reason, so the model is likely receiving too vague a repair objective.

The Python engine self-heals through: circuit breaker (`cb_record_progress`), orphaned task recovery (2x/10x timeout thresholds), auto-blocking at `max_attempts`, and atomic state writes. See `references/hooks-and-recovery.md` for the full self-repair protocol.

In those cases, do not simply relaunch. Back up `queue.json` and task-worktree diffs, stop blind retries if they are burning time, read the newest `gate-review` hook stdout JSON and the affected task's `last_error`, then write a targeted recovery prompt such as "fix duplicate status/session handler registration in OpenCodeAdapter" rather than "continue the task". If the failure is a controller/heartbeat behavior gap, fix and deploy `opencode-loop` first, then resume the target queue.

Target-side state lives under `.opencode-loop/progress.txt`, `.opencode-loop/state.json`, `.opencode-loop/runtime.json`, `.opencode-loop/logs/`, `.opencode-loop/output-*.jsonl`, and `.opencode-loop/stderr-*.log`.

### Self-Repair and Hooks

For the complete self-repair protocol (7-step evolution loop for stalled runs) and optional hooks configuration (reviewer detection, two-layer validation, install-review/install-recovery), **read `references/hooks-and-recovery.md`**.

Key flags:

- `--no-auto-reset` — opt out of startup circuit-breaker reset (default is enabled).
- `--auto-resume-safe` — auto-resolve `stale_running_without_process` when no live loop owns the queue.

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

Imported execute queues default to `profile.isolation: "worktree"` and `profile.integration_strategy: "fast_forward_merge"`. This is the Full Auto default; hand-written low-level queues can still use `isolation: "none"` when that is intentional.

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

For command gates, verify the command works in the same non-interactive shell that gates use, especially on macOS where login shells may resolve a different `python3` than Codex's current shell:

```bash
bash --noprofile --norc -c 'command -v python3 && python3 -m pytest -q'
```

If this resolves the wrong interpreter or misses dependencies, use the project's virtualenv/absolute tool path in `verification` and `acceptance_checks` instead of a bare command.

Prefer behavior-based acceptance checks over file-placement checks. File checks are fine for newly required artifacts, but avoid over-specifying which source file must contain an implementation detail when the public behavior can be verified through tests or CLI/API output.

Only set `tdd_required: true` when the task prompt explicitly asks the model to emit gate-recognized `TDD_RED[...]` and `TDD_GREEN[...]` evidence. For general E2E loop probes or legacy code hardening where TDD evidence is not part of the objective, leave it false so the TDD gate does not fail an otherwise valid delivery.

Finish enrichment before the task becomes `in_progress`; execute prompts are captured at task selection time. Updating an active task can still harden gates, but it does not rewrite the prompt already handed to OpenCode. If a command acceptance check inspects a committed task diff, compare `HEAD^ HEAD` rather than plain `HEAD`.

Avoid command checks that start with `!` and contain a pipe, such as `! git diff ... | awk ...`; Bash negates the whole pipeline and can invert pass/fail in surprising ways. Use explicit shell logic instead, and run `opencode-loop queue lint --strict` before start.

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

bash opencode-loop.sh --dir /path/to/target --mode execute --iterations 30 --timeout 60 --session-mode multi --session-rotate 5
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

For new Full Auto queues, install this hook with:

```bash
opencode-loop hooks install-review --dir /path/to/target --codex-bin codex --timeout 1800
opencode-loop hooks test --dir /path/to/target --event post_iteration --gate
```

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

For Full Auto and newly imported execute queues, prefer `worktree` plus `fast_forward_merge`. Use `none` only for intentional in-place execution, low-level tests, or emergency recovery where worktree isolation is unavailable.

Core-script emergency flags:

```bash
bash opencode-loop.sh --dir /path/to/target --mode execute --skip-gates review,tdd
bash opencode-loop.sh --dir /path/to/target --mode execute --unsafe-skip-baseline-gates
```

### Worktree Isolation Lifecycle

When `profile.isolation` is `worktree`, each queue task runs in an isolated Git worktree. The Python isolation manager handles creation, cleanup, and integration automatically.

For manual worktree management (recovery, continuation, inspection), **read `references/worktree-recovery.md`** which covers:
- Recovery from interrupted worktree creation (index.lock, missing directories)
- State migration to new worktrees
- Dependency installation before execute
- Full continuation checklist
- Post-commit repo cleanliness (opencode.json dirty handling)

Resume guard auto-resolution can clear `stale_running_without_process` with `--auto-resume-safe` when the saved PID is gone and no live loop owns the queue; use it for unattended recovery instead of forcing `--resume-existing-queue` blindly.

### Failure / Recovery

| Symptom | Check | Fix |
|---------|-------|-----|
| `doctor --json` shows `ok: false` | Missing `opencode`, `jq`, or `git` | Install missing dependency |
| Circuit breaker OPEN | 3+ no-progress or 5+ same errors | Default `--auto-reset` on next start, or wait 30min cooldown |
| Circuit breaker `permanent_open` | 5 open/half-open cycles exhausted | Inspect repeated blocker, fix root cause, then reset breaker intentionally |
| Task stuck `rejected` | `queue show --task ID --json` | Fix gate failure, `queue set-status --task ID --status todo --reason "retry"` |
| Task auto-blocked | `attempt_count >= max_attempts` | Fix task cause, raise max attempts only if justified, then requeue |
| Orphaned task with dirty files | `last_activity` > 10x timeout and worktree dirty | Engine reverts task work and resets to `todo`; inspect recovery logs |
| Stale `index.lock` blocks worktree ops | `.git/index.lock` exists, no git process | `rm -f .git/index.lock` |
| Worktree: branch exists, path missing | `git branch` shows branch, `git worktree list` doesn't | `git worktree add <path> <branch>` (re-bind) |
| "Dirty working tree with no active task" | Completed task, `opencode.json` dirty | Loop exits `environment_blocked` (code 6). Gitignore `opencode.json` or absorb into commit |
| Rate limit hit | 100 calls/hour | Wait, or check `rate_limit.json` |
| Supervisor says stale | No activity for `--stale-minutes` | Check `supervisor.log` |
| WSL hooks can't find CLI | CLIs not in WSL PATH | Symlink: `ln -s $(which claude.exe) /usr/local/bin/claude` |
| `plan` refuses overwrite | `queue.json` exists | Delete before re-import |

For the complete three-layer pipeline (OpenSpec → Task Master → opencode-loop), see `references/full-auto-pipeline.md`. For accumulated operational debugging knowledge (8 rounds of real-world failure analysis), see `references/opencode-loop-pitfalls-summary.local.md`.

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
open "<opencode-loop-repo>/OpenCode Loop TUI.command"
```

Replace `<opencode-loop-repo>` with the actual clone path.

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
