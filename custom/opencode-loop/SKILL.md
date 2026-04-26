---
name: opencode-loop
description: "Use when the user wants OpenCode Loop/opencode-loop unattended or self-running multi-iteration coding over a target project: create projects, optimize/refactor repos, fix test/lint/type failures, run build→verify→fix/report cycles, configure CLI/TUI/supervisor/hooks, inspect status/logs, or asks about opencode-loop commands, version, update-check, doctor/status JSON, next-command. Trigger on Chinese/English phrases like 无人值守, 自动循环, 自动修 bug, 让大模型自己跑. Do not trigger for one-shot manual debugging, generic programming loops, TUI UI implementation, or explicit requests not to use unattended agents."
---

# OpenCode Loop Skill

Use this skill to help the user run the local `opencode-loop` project as an unattended orchestrator over a target project. The loop is useful when a task benefits from repeated model iterations: bootstrapping a project, implementing a backlog, improving quality, fixing bugs, resolving test failures, addressing warnings, or running ML experiments.

OpenCode Loop has two supported usage modes:

- **Command-line mode**: the assistant confirms the plan with the user, prepares the target project and loop inputs, then runs the appropriate setup/start commands.
- **TUI mode**: the assistant prepares the needed target project inputs, then guides the user to fill them into the OpenCode Loop TUI.

## First Decide The Route

Choose a route early so the rest of the workflow is concrete:

- Prefer **command-line mode** when the assistant has terminal access, the user wants the agent to execute the loop directly, or the task is mostly mechanical.
- Prefer **TUI mode** when the user wants a visual control plane, wants to supervise multiple projects, or explicitly asks for the TUI.
- If the user does not choose, default to command-line mode and mention that the TUI is available for manual control.

Before starting either route, clarify only the details that are risky to assume:

- Target project path, or whether a new project should be created.
- Goal statement: what should be built, improved, fixed, or investigated.
- Mode: `dev` for software projects, `ml` for ML experiment loops.
- Stop condition: iteration cap, acceptance criteria, tests to pass, or a structured “done” signal.
- Safety boundary: files or directories the loop must not modify, secrets to avoid, and commands that require user approval.

## Locate The OpenCode Loop Repo

When working from inside the OpenCode Loop repository, use the current repo root. Otherwise locate it before giving commands:

- If the global `opencode-loop` command is installed, prefer it over manually calling repo scripts.
- Ask the user for the local `opencode-loop` path if it is unknown.
- On macOS, use the native repo path directly.
- On Windows, prefer running Bash-facing workflows through WSL.
- For this repo on a macOS host, a known pattern is:
  - macOS repo path: `/Volumes/SDD2T/obsidian-vault-write/open-source-project/autonomous-ai-agents/agent-loops/opencode-loop`
- For this repo on a Windows host, a known pattern is:
  - Windows repo path: `C:\Users\lt\Desktop\Write\open-source-project\autonomous-ai-agents\agent-loops\opencode-loop`
  - WSL execution path should be derived with `wslpath`.

Do not run `lib/*.sh` files directly. They are sourced modules used by `opencode-loop.sh`.

## Prefer The AI-Friendly CLI

The global `opencode-loop` wrapper delegates to the current repo checkout. Prefer it for repeatable agent work because it exposes stable commands and machine-readable JSON:

```bash
opencode-loop --version
opencode-loop doctor --dir /path/to/target --json
opencode-loop status --dir /path/to/target --json
opencode-loop next-command --dir /path/to/target --kind supervisor --profile long
```

Use `opencode-loop update-check --json` only when the user asks whether the tool itself is current. Normal `start` and `supervisor` launches do not contact the remote, which keeps unattended runs from failing because of network or GitHub problems.

If the wrapper is missing, install it from the repo checkout:

```bash
bash bin/install-cli.sh                         # macOS / Linux / WSL
PowerShell -ExecutionPolicy Bypass -File .\bin\install-cli.ps1  # Windows host
```

## Prepare The Target Project

Prepare enough context so the unattended loop has a clear objective:

1. Ensure the target directory exists. If the user is starting from scratch, create or scaffold the project after confirming the stack and minimal requirements.
2. Ensure the project has a Git repository when appropriate, because the downstream loop may inspect diffs and commit/report progress depending on its program.
3. Add a concise project brief if the repo lacks one, such as `README.md`, `TASKS.md`, or a dedicated planning note.
4. Record acceptance criteria in plain language: commands to run, expected behavior, errors to fix, or files to produce.
5. Avoid putting secrets into prompts, config files, logs, or `.opencode-loop/`.

For existing projects, inspect enough local context to define a bounded task. Prefer narrow goals over “make it better” unless the user explicitly wants open-ended optimization.

## Command-Line Workflow

Use this workflow when the assistant will run OpenCode Loop directly.

### 1. Preflight

Check the basics before starting the loop:

```bash
opencode-loop --version
opencode-loop doctor --dir /path/to/target --json
```

If the global wrapper is not installed yet, fall back to repo-local checks:

```bash
bash -n opencode-loop.sh
command -v opencode
command -v jq
command -v git
```

If tests or full validation are desired from the loop repo:

```bash
bash bin/test.sh
```

On macOS for this repo, a concrete pattern is:

```bash
cd /Volumes/SDD2T/obsidian-vault-write/open-source-project/autonomous-ai-agents/agent-loops/opencode-loop && bash bin/test.sh
```

On Windows hosts, prefer WSL:

```powershell
wsl -d Ubuntu -- bash -lic 'cd /mnt/.../opencode-loop && bash bin/test.sh'
```

### 2. Initialize The Target Project

Initialize from the global CLI when available:

```bash
opencode-loop init --dir /path/to/target --mode dev
```

Fallback from the OpenCode Loop repo root:

```bash
bash bin/setup.sh --dir /path/to/target --mode dev
```

Use `--mode ml` for ML experiment workflows.

Setup creates target-side orchestration files including:

- `.opencode-loop/program.md`
- `.opencode-loop/state.json`
- `.opencode-loop/control.json`
- `.opencode-loop/runtime.json`
- `.opencode-loop/progress.txt`
- `opencode.json`

### 3. Start The Loop

Use conservative limits first, then expand after the first run looks healthy. Preview the exact command before starting when the user asks for safety:

```bash
opencode-loop next-command --dir /path/to/target --kind start --profile quick
opencode-loop start --dir /path/to/target --profile quick
```

For longer tasks, prefer the supervisor profile rather than wrapping `opencode-loop.sh` yourself:

```bash
opencode-loop next-command --dir /path/to/target --kind supervisor --profile long
opencode-loop supervisor --dir /path/to/target --profile long
```

Useful flags:

- `--iterations N` limits unattended loop length.
- `--timeout MIN` limits each OpenCode iteration.
- `--program FILE` points to a custom program prompt if the default template is not enough.
- `--auto-reset` resets circuit breaker state on startup.
- `--opencode PATH` uses a non-default `opencode` binary.
- `--session-mode MODE` sets session strategy: `single` (default), `multi` (recommended for 10+ iterations), `auto` (experimental, context-based), `clean` (fresh session each iteration).
- `--session-rotate N` iterations per session in multi mode (default: 5).
- `--context-threshold PCT` context usage % trigger for auto mode (default: 70).
- `--context-window-tokens N` model context window for auto mode estimation (default: 200000).

**Multi-session recommendations**:
- Use `multi` mode with `--session-rotate 5` or `10` for tasks over 15 iterations.
- Use `clean` mode for maximum isolation when each iteration is independent.
- `auto` mode is experimental — prefer `multi` for reliability.
- The loop generates a `handoff.md` on each rotation to preserve task continuity across sessions.

### 4. Monitor And Report

Prefer machine-readable CLI state for agents:

```bash
opencode-loop status --dir /path/to/target --json
opencode-loop logs --dir /path/to/target --file progress --tail 80
```

Target-side loop state remains under:

- `.opencode-loop/progress.txt`
- `.opencode-loop/state.json`
- `.opencode-loop/runtime.json`
- `.opencode-loop/logs/`
- `.opencode-loop/output-*.jsonl`
- `.opencode-loop/stderr-*.log`

Report back with:

- What was prepared.
- Exact command used.
- Current loop state or final result.
- Any user action needed, such as installing `opencode`, `jq`, or `bats`.

### 5. Optional External Hooks

Use the CLI to configure Kimi/Codex or other external tools around each iteration instead of hand-editing JSON:

```bash
opencode-loop hooks add --dir /path/to/target --event pre_iteration --name kimi-ui --command 'kimi-code --dir "$OPENCODE_LOOP_TARGET_DIR" "Review UI before this iteration"' --attempts 3
opencode-loop hooks add --dir /path/to/target --event post_iteration --name codex-review --command 'codex exec --cd "$OPENCODE_LOOP_TARGET_DIR" "Review this iteration"' --attempts 3
opencode-loop hooks list --dir /path/to/target --json
opencode-loop hooks test --dir /path/to/target --event post_iteration --iteration 0
```

Hook failures retry, warn, and continue unless the project intentionally changes that policy.

## TUI Workflow

Use this workflow when the user will operate the visual frontend.

### 1. Prepare Inputs First

Before launching or instructing the user to launch the TUI, prepare:

- Target project path.
- Recommended mode: `dev` or `ml`.
- Suggested iteration cap and timeout.
- Short goal statement and acceptance criteria.
- Any custom program file path if the default program is not enough.
- Notes about commands/tests the downstream agent should run.

If the target project has not been initialized, either run setup for the user or tell them to let the TUI run setup.

### 2. Launch The TUI

From the OpenCode Loop repo on Unix/WSL:

```bash
bash bin/opencode-loop-tui.sh --dir /path/to/target
```

On macOS, prefer the repo-root launcher when the user wants the local desktop app experience:

```bash
open "/Volumes/SDD2T/obsidian-vault-write/open-source-project/autonomous-ai-agents/agent-loops/opencode-loop/OpenCode Loop TUI.command"
```

The macOS launcher can bootstrap a local `.venv-tui/` automatically before opening the TUI.

On Windows, prefer the native Windows frontend plus WSL backend launcher:

```powershell
& ".\OpenCode Loop TUI (WSL).cmd" "C:\path\to\target"
```

The TUI frontend runs in native Windows Python while setup and loop actions execute through WSL.

### 3. Tell The User What To Fill In

Give the user a compact checklist:

- **Target directory**: the project to be created, optimized, or fixed.
- **Mode**: `dev` for code/project work, `ml` for ML experiments.
- **Iterations**: start small, often `3`, then increase after review.
- **Timeout**: start with `15` minutes unless the project needs longer builds.
- **Program**: leave default unless a custom `.md` plan was prepared.
- **Controls**: use pause/resume/stop for iteration boundaries; do not expect the TUI to hard-kill active OpenCode work.

Explain that the TUI is a control and inspection layer over the target project's `.opencode-loop/` state, not a separate orchestrator.

## When To Customize The Program

Use the default templates unless the task needs unusual behavior:

- `templates/program-dev.md` for project creation, coding, refactoring, debugging, warnings, errors, docs, and tests.
- `templates/program-ml.md` for hypothesis/evaluate/keep-or-revert ML experiments.

If a custom program is needed, create a separate Markdown file and pass it with `--program FILE`. Avoid casually editing `templates/program-*.md` or `templates/opencode.json`, because those define the downstream agent contract for future target projects.

## Safety And Boundaries

OpenCode Loop is intentionally unattended, so make the boundary explicit:

- Start with a small iteration cap before long unattended runs.
- Avoid broad destructive requests like “rewrite everything” unless the user truly intends it.
- Keep persisted loop state under the target project's `.opencode-loop/`.
- Preserve atomic JSON write semantics if editing OpenCode Loop internals.
- Do not replace structured JSON exit detection with keyword guessing.
- Do not expose API keys, credentials, private tokens, or secrets to loop prompts or logs.

## Final Response Pattern

When handing off to the user, use this structure:

- **Route**: command-line or TUI.
- **Prepared**: target path, mode, brief/task files, setup status.
- **Run command or TUI fields**: exact command or exact fields to fill.
- **Monitoring**: files or TUI locations to check.
- **Next step**: whether to start, continue, review logs, or increase iterations.

Keep the response concise, but include exact paths and commands so the user can act immediately.
