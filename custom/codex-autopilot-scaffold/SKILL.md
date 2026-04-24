---
name: codex-autopilot-scaffold
description: Use this skill when the user wants to scaffold or safely refresh a repo-local unattended Codex autopilot inside a repository, including queue-driven presets, review-gated autopilot assets, or Windows/macOS bootstrap and health workflows. Trigger for requests about repo-owned autopilot setup, scaffold upgrades that must preserve lane docs, or adding multi-round unattended controller files to a project. Do not use this skill for one-shot debugging or for merely running an existing OpenCode Loop setup.
---

# Codex Autopilot Scaffold

Use this skill to install a **repo-local Codex autopilot scaffold** into a target repository. The output is not an external loop service. It is a set of files committed into the target repo so future agents can run:

- `python automation/autopilot.py doctor|start|watch|status|health|bootstrap-and-daemonize|restart-after-next-commit`
- `automation/Arm-AutopilotCutover.ps1` and `automation/arm-autopilot-cutover.sh` for reusable post-commit cutovers
- root status overview docs plus lane-local `docs/status/lanes/<lane-id>/autopilot-*.md`
- machine-readable runtime state in `automation/runtime/`

This is **not** a one-command “立即开跑” skill. Treat it as **scaffold + controller + repo assets**:

- install or refresh the controller/wrappers
- seed the queue with a preset, approved plan, or approved spec
- hand off exact `doctor` / `bootstrap-and-daemonize` / `watch` / `health` commands
- when the user wants review-gated unattended work, scaffold the repo-local `.opencode/commands/*` review commands and review wrappers too

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

The scaffold now records its deployed version in `automation/autopilot-scaffold-version.json`. When you invoke this skill against a repo that already has an older autopilot scaffold, prefer rerunning `scripts/scaffold_repo.py` without `--force`: it should auto-refresh the shared controller/wrapper assets and preset `automation/*` files to the current scaffold version while preserving repo-specific lane queue docs under `docs/status/`.

## First decide install mode

Before you pick a preset, decide whether the target repo needs a **fresh install** or a **shared-controller refresh**:

- **Fresh install**: no existing `automation/autopilot-scaffold-version.json` and no legacy `automation/autopilot.py`
- **Shared-controller refresh**: existing scaffold detected, and the user wants newer controller/runtime/wrapper behavior without resetting repo-local lane queue docs
- **Intentional regeneration**: only use `--force` when the user explicitly wants generated repo-local files overwritten

If the repo already has queue docs, say out loud whether you are refreshing shared assets or replacing project-local queue assets. Do not leave that ambiguous.

## First decide the preset

Choose the narrowest preset that matches the user's intent:

- `maintainability`: queue-driven ownership reduction and refactor slices
- `review-gated`: each round must write a short plan, pass a plan review, implement, pass a code review, then validate before committing
- `quality-gate`: restore lint/typecheck/test/build gates and close the most justified validation hotspots
- `bugfix-backlog`: execute one reproducible bugfix or backlog slice at a time

If the user does not specify, prefer:

1. `maintainability` for “可维护性 / 重构 / 降复杂度”
2. `review-gated` for “每轮先审方案再审代码 / 方案 gate / code review gate / opencode review”
3. `quality-gate` for “lint/typecheck/test/build 红了”
4. `bugfix-backlog` for “按 backlog / bug 队列一轮轮修”

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
--seed-plan docs/superpowers/plans/approved-plan.md
--seed-spec docs/superpowers/specs/approved-spec.md
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
- when `review-gated` is selected: `.opencode/commands/review-plan.md`, `.opencode/commands/review-code.md`, `automation/opencode-review.sh`, and `automation/Invoke-OpencodeReview.ps1`

It also prints:

- inferred validation commands and their sources
- warnings when inference is weak
- whether an older deployed scaffold was auto-upgraded
- current scaffold version and source path
- a reminder to create a dedicated `autopilot/...` branch/worktree before `doctor` / `start`
- suggested `doctor`, `health`, `start --dry-run --single-round`, and `bootstrap-and-daemonize` commands
- a remote Mac rollout template when the operator wants Windows-local scaffold + Mac unattended execution

If the user has an approved implementation plan or spec, pass `--seed-plan` or `--seed-spec`. The script copies that file into `docs/status/`, adds a seeded queue override to lane roadmaps, and makes the approved plan/spec the queue authority before generic preset text. This avoids the common failure mode where `bugfix-backlog` or `maintainability` starts from broad placeholder backlog language instead of the user's approved plan.

## After scaffolding

Commit the scaffold first, because the autopilot controller expects a clean worktree before unattended execution.

If the target repo already has this scaffold and the deployed `scaffold_version` is older than the current skill version, the script should auto-upgrade shared controller assets plus preset `automation/*` files first. Treat that as a scaffold refresh, not as user intent to regenerate or reset the repo-specific lane docs.

Before running `doctor` or `start`, create a dedicated branch or worktree. A fresh scaffold on `main` is allowed to install, but `doctor` / `start` should fail branch guard checks until the operator moves to a branch such as `autopilot/<topic>`, `quality/<topic>`, or `bugfix/<topic>`. Make this explicit in handoff text so “installed successfully, then doctor failed on main” is understood as expected safety behavior.

When the operator wants “先前台确认首轮跑通，再切后台常驻”, prefer `bootstrap-and-daemonize` over hand-written sentinels. That command exists specifically because `restart-after-next-commit` cannot watch a commit that does not exist yet.

When the target execution machine is a remote Mac, hand off a concrete playbook instead of leaving the operator to assemble it:

1. Scaffold locally on Windows.
2. Commit and push.
3. `ssh mac` into the synced/remote repo.
4. Fetch/reset or pull the scaffold commit.
5. Create a dedicated Mac-side worktree/branch.
6. Run `doctor`, `health`, `start --dry-run --single-round`, then `bootstrap-and-daemonize` or the background wrapper.

### Review-gated preset rules

If the user wants “每轮先审方案，再审代码”, use `review-gated` instead of telling them to bolt reviews on manually.

- The preset scaffolds repo-local `.opencode/commands/` review assets as committed files, not machine-local notes
- It also adds cross-platform wrappers:
  - Windows: `pwsh -File .\automation\Invoke-OpencodeReview.ps1 ...`
  - macOS/Linux: `bash ./automation/opencode-review.sh ...`
- The generated `.gitignore` should unignore those `.opencode/commands/*.md` files so repo-local review flows survive commit/push/pull
- Review wrappers are allowed to take minutes; slow polling is expected, not evidence of a stuck run
- Useful round-level artifacts usually live in `automation/runtime/round-XXX/`, especially `progress.log`, `events.jsonl`, `assistant-output.json`, and `runner-status.json`

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

### Command budget policy

The controller records budget findings for repeated `git status --short` and `git diff --stat`, but scaffold version `1.0.3+` defaults those findings to warnings through `command_budget_policy: "warn"`.

- Do not roll back an otherwise successful commit only because `commands_run` exceeded a diagnostic command budget.
- If a repo really needs hard enforcement, set `command_budget_policy` to `hard`, `fail`, or `error` deliberately.
- Treat budget warnings as operator feedback for future prompt/config tuning, not as proof the target repo code failed.
- If a round looks “failed” after visible work succeeded, inspect runtime logs for controller budget/validation findings before chasing phantom app bugs.

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
python .\automation\autopilot.py health --runtime-path automation\runtime --state-path automation\runtime\<state-file>.json
python .\automation\autopilot.py watch --runtime-path automation\runtime --state-path automation\runtime\<state-file>.json --tail 80
Get-Content automation\runtime\round-XYZ\progress.log -Wait -Tail 80
```

### macOS

```bash
python3 ./automation/autopilot.py status --state-path automation/runtime/<state-file>.json
python3 ./automation/autopilot.py health --runtime-path automation/runtime --state-path automation/runtime/<state-file>.json
python3 ./automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/<state-file>.json --tail 80
tail -n 80 -F automation/runtime/round-XYZ/progress.log
```

Operational guidance:

- The scaffolded `watch` command now prints `round`, `phase`, `lane`, `queue progress`, `status`, `failures`, `phase doc`, `focus`, and the exact `progress.log` path it is following.
- `watch` and `status` should also surface the latest review verdicts and last blocker when the run recorded them.
- `health` is the source of truth for “state says active, but is the runner really alive?” because it checks state, lock, pid, and artifact freshness together.
- Do **not** report “下一轮已经在跑” unless all three are true at the same time:
  - the autopilot parent PID from the runtime lock is alive
  - the watched round `progress.log` is still updating
  - the watched round `runner-status.json` shows the `codex exec` child PID alive **and** `exec_confirmed_at` is present
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
- If there is no successful commit yet for the current state line, do **not** reach for `restart-after-next-commit`; use `bootstrap-and-daemonize` or stay foreground until the first commit exists.
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
