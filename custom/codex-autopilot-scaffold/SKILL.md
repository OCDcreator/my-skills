---
name: codex-autopilot-scaffold
description: Use this skill when the user wants to inject a Codex-style repo-local unattended autopilot into an existing project, port a proven `codex exec` automation loop into another repository, or scaffold persistent `automation/autopilot.py` + queue docs + state/lock/history files that other models can run without hand-holding. Trigger for requests about repo-owned autopilot setup, round-by-round unattended Codex workflows, queue-driven refactor/quality-gate/bugfix scaffolds, or Windows/macOS autopilot bootstrapping. Do not use this skill for one-shot debugging or for merely running an existing OpenCode Loop setup.
---

# Codex Autopilot Scaffold

Use this skill to install a **repo-local Codex autopilot scaffold** into a target repository. The output is not an external loop service. It is a set of files committed into the target repo so future agents can run:

- `python automation/autopilot.py doctor|start|watch|status|restart-after-next-commit`
- `automation/Arm-AutopilotCutover.ps1` and `automation/arm-autopilot-cutover.sh` for reusable post-commit cutovers
- root status overview docs plus lane-local `docs/status/lanes/<lane-id>/autopilot-*.md`
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
- `docs/status/autopilot-master-plan.md`
- `docs/status/autopilot-lane-map.md`
- `docs/status/lanes/<lane-id>/autopilot-*`
- `.gitignore` entry for `automation/runtime/`

Do not refactor the target app itself while scaffolding.

The scaffold now records its deployed version in `automation/autopilot-scaffold-version.json`. When you invoke this skill against a repo that already has an older autopilot scaffold, prefer rerunning `scripts/scaffold_repo.py` without `--force`: it should auto-refresh the shared controller/wrapper assets to the current scaffold version while preserving repo-specific queue docs, prompts, and `automation/autopilot-config.json`.

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
--vulture-command "python -m vulture src tests"
--deploy-policy targeted
--deploy-required-paths src/ manifest.json scripts/deploy/
--deploy-verify-path dist/build-id.txt
--runner-model "gpt-5.4"
--force
```

## What the script does

It deterministically writes:

- common automation assets from `templates/common/`
- preset-specific config/prompt/docs from `templates/presets/<preset>/`
- `automation/autopilot-scaffold-version.json` with the deployed scaffold version
- `.gitignore` entry for `automation/runtime/`

It also prints:

- inferred validation commands and their sources
- warnings when inference is weak
- whether an older deployed scaffold was auto-upgraded
- suggested `doctor` and `start --dry-run --single-round` commands

## After scaffolding

Commit the scaffold first, because the autopilot controller expects a clean worktree before unattended execution.

If the target repo already has this scaffold and the deployed `scaffold_version` is older than the current skill version, the script should auto-upgrade shared controller assets first. Treat that as a scaffold refresh, not as user intent to regenerate or reset the repo-specific lane docs.

### Commit prefix gate

The controller validates successful round commits against `commit_prefix` in `automation/autopilot-config.json`.

- If `commit_prefix` is non-empty, every successful round commit subject must start with `<commit_prefix>:` (for example, `autopilot:`).
- If you create a custom lane or custom `round-prompt*.md`, keep that commit-message rule explicit in the prompt or set `commit_prefix` to an empty string deliberately.
- The scaffolded controller also injects this requirement into every rendered round prompt, so custom prompts cannot silently omit it.
- Treat repeated `Commit message must start with ...` failures as a lane configuration/prompt mismatch, not as a code-quality failure.

### Build/deploy result gate

The controller also validates `build_ran`, `build_id`, `deploy_ran`, and `deploy_verified` in the final JSON.

- If `build_ran` is `true`, the round must report a real non-empty `build_id`.
- If no trustworthy build identifier exists, the round should report `build_ran=false` rather than inventing one.
- If `deploy_ran` is `true`, that deploy must actually have happened and must satisfy the configured verification checks.
- The scaffolded controller injects these requirements into every rendered round prompt so custom prompts cannot silently omit them.

Then run a smoke test in the target repo:

Failed rounds preserve a safety ref under `refs/autopilot/safety/*` and stash dirty work before resetting to the round's starting `HEAD`, so operators can recover commits or concurrent local edits instead of losing them silently.

### Windows

```powershell
python .\automation\autopilot.py doctor --profile windows
python .\automation\autopilot.py start --profile windows --dry-run --single-round
```

If the operator explicitly wants a no-window unattended launch, do **not** start `py.exe` or `python.exe` in a fresh visible console. Prefer the scaffolded background wrapper, implemented through a hidden PowerShell host that launches `py` / `python` without a top-level window:

```powershell
.\automation\Start-Autopilot.ps1 -Background --% --profile windows
```

### macOS

```bash
python3 ./automation/autopilot.py doctor --profile mac
python3 ./automation/autopilot.py start --profile mac --dry-run --single-round
bash ./automation/start-autopilot.sh -- --profile mac --dry-run --single-round
bash ./automation/watch-autopilot.sh --state-path automation/runtime/autopilot-state.json --tail 80
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
- macOS gets convenience wrappers:
  - `automation/start-autopilot.sh`
  - `automation/watch-autopilot.sh`
  - `automation/launchd/com.example.codex-autopilot.plist`
- Clarify the two Windows window layers when you scaffold or hand off:
  - child shell subwindows such as `cmd.exe` / `pwsh.exe`
  - the top-level launcher window such as `py.exe` / `python.exe`
- `autopilot.py` must hide child shell subwindows by default so unattended rounds do not spawn blank `cmd.exe` popups.
- Hiding child subwindows is **not** enough to guarantee a no-window launch. If the user asked for zero visible windows, the scaffold and your instructions must also use `automation/Start-Autopilot.ps1 -Background`, implemented via a hidden `pwsh.exe` / Windows PowerShell host that launches `py` / `python` without a visible top-level console. Do **not** rely solely on `pythonw.exe` / `pyw.exe`; those shims can be unreliable on some Windows installs.
- Committed profiles must stay machine-neutral
- Local absolute paths belong in external profile JSON passed through `--profile-path`
- Prefer `deploy_policy=targeted` over `deploy_policy=always`; deploying every successful round is usually unnecessary unless the repo truly publishes every round.

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

- The scaffolded `watch` command now prints `round`, `phase`, `lane`, `queue progress`, `status`, `failures`, `phase doc`, `focus`, and the exact `progress.log` path it is following.
- When `vulture_command` is configured, `status` and `watch` also report the latest finding count and delta from the previous successful snapshot.
- Every streamed detail line from `progress.log` is also prefixed with a live state tag that includes lane and queue counts, defaulting to the long form `[lane=b1-backlog-slice queue=1/3 round=006 phase=005 status=active failures=0]` so the current lane/queue/round/phase/status stays visible after the header scrolls away.
- Operators who prefer denser output can run `watch --prefix-format short` to switch detail lines to `[b1-backlog-slice q1/3 r006 p005 active f0]`.
- When the watched state is `active`, the live round log is usually `current_round + 1`; when the state is terminal, it is usually `current_round`.
- If the log looks stale, compare `status --state-path ...` against the watched `progress.log` path before assuming the runner is stuck.
- In queue-driven presets, `goal_complete` means the active lane's current `[NEXT]` slice was already satisfied. The controller should only leave the lane when its roadmap has no remaining `[NEXT]` or `[QUEUED]` items; otherwise it must keep the lane `active`, advance `next_phase_number`, and continue into the next queued slice.

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
- Keep Python bytecode disabled in custom sentinels or wrappers (`PYTHONDONTWRITEBYTECODE=1`) and make sure the target repo ignores `automation/**/__pycache__/` plus `automation/**/*.pyc`; otherwise the next `doctor` or `start` can reject the worktree as dirty.

Reusable scaffolded wrappers:

### Windows

```powershell
.\automation\Arm-AutopilotCutover.ps1 `
  -StatePath automation\runtime\<state-file>.json `
  -Profile windows `
  -ConfigPath automation\<config>.json `
  -RestartSyncRef <cutover-ref>
```

### macOS

```bash
bash ./automation/arm-autopilot-cutover.sh \
  --state-path automation/runtime/<state-file>.json \
  --profile mac \
  --config-path automation/<config>.json \
  --restart-sync-ref <cutover-ref>
```

Both wrappers also support config/profile/state-only cutovers by omitting `restart-sync-ref` and passing replacement paths directly.

For a repo-local macOS LaunchAgent handoff, copy `automation/launchd/com.example.codex-autopilot.plist` into `~/Library/LaunchAgents/`, replace `/ABSOLUTE/PATH/TO/REPO`, then use `launchctl bootstrap gui/$(id -u) ...` and `launchctl kickstart -k ...`.

## Final response pattern

When you finish scaffolding, report:

- chosen preset
- target repo path
- commands inferred or overridden
- files added
- smoke-test commands run and their result
- the next command the user or future agent should run
