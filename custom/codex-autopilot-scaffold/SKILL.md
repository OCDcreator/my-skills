---
name: codex-autopilot-scaffold
description: Use this skill when the user wants to inject a Codex-style repo-local unattended autopilot into an existing project, port a proven `codex exec` automation loop into another repository, or scaffold persistent `automation/autopilot.py` + queue docs + state/lock/history files that other models can run without hand-holding. Trigger for requests about repo-owned autopilot setup, round-by-round unattended Codex workflows, queue-driven refactor/quality-gate/bugfix scaffolds, or Windows/macOS autopilot bootstrapping. Do not use this skill for one-shot debugging or for merely running an existing OpenCode Loop setup.
---

# Codex Autopilot Scaffold

Use this skill to install a **repo-local Codex autopilot scaffold** into a target repository. The output is not an external loop service. It is a set of files committed into the target repo so future agents can run:

- `python automation/autopilot.py doctor|start|watch|status|restart-after-next-commit`
- queue-driven `docs/status/autopilot-*.md`
- machine-readable runtime state in `automation/runtime/`

## When this skill wins

Use this skill when the user wants any of the following:

- “把这套 Codex 无人值守流程移植到别的项目里”
- “给这个仓库装一套 repo-local autopilot”
- “生成 round prompt / roadmap / lane map / state / lock 这些框架”
- “让别的模型之后能直接在这个项目里跑类似 Codex autopilot”
- a reusable unattended scaffold for **maintainability/refactor**, **quality-gate recovery**, or **bugfix/backlog**

Do **not** use this skill when the user really wants:

- a one-shot manual fix
- generic advice about `for` / `while` loops
- to run the existing `opencode-loop` project rather than scaffold a repo-owned autopilot

## Output boundary

This skill should only scaffold autopilot assets and adjacent docs/config:

- `automation/`
- `docs/status/autopilot-*`
- `.gitignore` entry for `automation/runtime/`

Do not refactor the target app itself while scaffolding.

## First decide the preset

Choose the narrowest preset that matches the user's intent:

- `maintainability`: queue-driven ownership reduction and refactor slices
- `quality-gate`: restore lint/typecheck/test/build gates and close the most justified validation hotspots
- `bugfix-backlog`: execute one reproducible bugfix or backlog slice at a time

If the user does not specify, prefer:

1. `maintainability` for “可维护性 / 重构 / 降复杂度”
2. `quality-gate` for “lint/typecheck/test/build 红了”
3. `bugfix-backlog` for “按 backlog / bug 队列一轮轮修”

## Minimal inputs

Before scaffolding, discover as much as possible from the target repo. Only ask if the remaining ambiguity changes the generated scaffold materially.

Prefer to discover:

- Git repo root
- likely validation commands from `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`, `justfile`
- likely source/test entrypoints
- whether `automation/` or `docs/status/` already exists

Only ask if needed:

- which preset to use, if intent is genuinely ambiguous
- missing validation commands that the user cares about and the repo does not reveal
- whether to overwrite an existing autopilot scaffold

## Use the bundled script

Use `scripts/scaffold_repo.py` rather than recreating files by hand.

Typical command:

```bash
python /path/to/skill/scripts/scaffold_repo.py \
  --target-repo /path/to/repo \
  --preset maintainability
```

Useful overrides:

```bash
--objective "custom objective"
--lint-command "custom lint command"
--typecheck-command "custom typecheck command"
--full-test-command "custom full test command"
--build-command "custom build command"
--runner-model "gpt-5.4"
--force
```

## What the script does

It deterministically writes:

- common automation assets from `templates/common/`
- preset-specific config/prompt/docs from `templates/presets/<preset>/`
- `.gitignore` entry for `automation/runtime/`

It also prints:

- inferred validation commands and their sources
- warnings when inference is weak
- suggested `doctor` and `start --dry-run --single-round` commands

## After scaffolding

Commit the scaffold first, because the autopilot controller expects a clean worktree before unattended execution.

Then run a smoke test in the target repo:

### Windows

```powershell
python .\automation\autopilot.py doctor --profile windows
python .\automation\autopilot.py start --profile windows --dry-run --single-round
```

### macOS

```bash
python3 ./automation/autopilot.py doctor --profile mac
python3 ./automation/autopilot.py start --profile mac --dry-run --single-round
```

If the repo has no allowed autopilot branch yet, create one first. Prefer names like:

- `autopilot/<topic>`
- `quality/<topic>`
- `bugfix/<topic>`

## Cross-platform rules

- The Python CLI is the main entrypoint on both Windows and macOS
- Windows gets convenience wrappers:
  - `automation/New-AutopilotWorktree.ps1`
  - `automation/Start-Autopilot.ps1`
  - `automation/Watch-Autopilot.ps1`
- Windows runner subprocesses should hide console windows by default so unattended rounds do not spawn blank `cmd.exe` popups.
- Committed profiles must stay machine-neutral
- Local absolute paths belong in external profile JSON passed through `--profile-path`

## Operator visibility rules

When a repo has more than one autopilot state file or old `round-*` directories, do **not** rely on bare `watch` or bare `status`. Always bind operator commands to the intended state line.

Preferred commands after scaffolding:

### Windows

```powershell
python .\automation\autopilot.py status --state-path automation\runtime\<state-file>.json
python .\automation\autopilot.py watch --runtime-path automation\runtime --state-path automation\runtime\<state-file>.json --tail 80
Get-Content automation\runtime\round-XYZ\progress.log -Wait -Tail 80
```

### macOS

```bash
python3 ./automation/autopilot.py status --state-path automation/runtime/<state-file>.json
python3 ./automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/<state-file>.json --tail 80
tail -n 80 -F automation/runtime/round-XYZ/progress.log
```

Operational guidance:

- The scaffolded `watch` command now prints `round`, `phase`, `status`, `failures`, `phase doc`, `focus`, and the exact `progress.log` path it is following.
- When the watched state is `active`, the live round log is usually `current_round + 1`; when the state is terminal, it is usually `current_round`.
- If the log looks stale, compare `status --state-path ...` against the watched `progress.log` path before assuming the runner is stuck.

## Sentinel / cutover rules

Prefer the built-in `restart-after-next-commit` command over ad-hoc shell loops whenever you need to stop after the next successful round and relaunch unattended work.

Use it in two standard modes:

### 1. Config/profile/state cutover

Use this when the replacement run only needs different config/profile/state arguments.

#### Windows

```powershell
python .\automation\autopilot.py restart-after-next-commit `
  --profile windows `
  --state-path automation\runtime\<state-file>.json `
  --restart-profile windows `
  --restart-config-path automation\<new-config>.json `
  --restart-state-path automation\runtime\<new-state-file>.json `
  --restart-profile-path C:\Users\you\.config\codex-autopilot\windows.profile.json `
  --restart-output-path automation\runtime\<new-run>.out `
  --restart-pid-path automation\runtime\<new-run>.pid
```

#### macOS

```bash
python3 ./automation/autopilot.py restart-after-next-commit \
  --profile mac \
  --state-path automation/runtime/<state-file>.json \
  --restart-profile mac \
  --restart-config-path automation/<new-config>.json \
  --restart-state-path automation/runtime/<new-state-file>.json \
  --restart-profile-path /Users/you/.config/codex-autopilot/mac.profile.json \
  --restart-output-path automation/runtime/<new-run>.out \
  --restart-pid-path automation/runtime/<new-run>.pid
```

### 2. Code or prompt cutover via ref

Use this when the next run should resume from a replacement commit prepared elsewhere, typically in a cutover worktree or sibling branch. This is the default answer when a user says “挂个哨兵，这一轮提交后切过去继续跑”.

Workflow:

1. Prepare the replacement commit on another ref.
2. Launch `restart-after-next-commit` against the currently active state line.
3. Pass `--restart-sync-ref <ref>` so the controller waits for that ref, fast-forwards to it, and then restarts the unattended loop.

#### Windows

```powershell
python .\automation\autopilot.py restart-after-next-commit `
  --profile windows `
  --state-path automation\runtime\<state-file>.json `
  --restart-sync-ref <cutover-ref> `
  --restart-profile windows `
  --restart-config-path automation\<config>.json `
  --restart-state-path automation\runtime\<state-file>.json
```

#### macOS

```bash
python3 ./automation/autopilot.py restart-after-next-commit \
  --profile mac \
  --state-path automation/runtime/<state-file>.json \
  --restart-sync-ref <cutover-ref> \
  --restart-profile mac \
  --restart-config-path automation/<config>.json \
  --restart-state-path automation/runtime/<state-file>.json
```

Sentinel guidance:

- Prefer `restart-after-next-commit` first; only write a custom local shell script when the cutover includes non-committed machine-local behavior that cannot live on a git ref.
- Keep custom sentinels local and uncommitted under a user config path such as `~/.config/<project>/`.
- When a repo has multiple concurrent state lines, always pass the exact `--state-path` for the run you are handing off.
- If the user asks for a future unattended cutover, explicitly report the sentinel command, output log path, pid path, and watched state path.

## Final response pattern

When you finish scaffolding, report:

- chosen preset
- target repo path
- commands inferred or overridden
- files added
- smoke-test commands run and their result
- the next command the user or future agent should run
