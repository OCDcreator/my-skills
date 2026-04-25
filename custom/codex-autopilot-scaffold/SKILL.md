---
name: codex-autopilot-scaffold
description: Use when a user wants to add, refresh, or operate a repo-local unattended Codex autopilot scaffold in a repository, especially queue-driven refactor/quality/bugfix work, review-gated rounds, Windows/macOS bootstrap, health checks, remote Mac rollout, or preserving lane docs during scaffold upgrades. Do not use for one-shot fixes or existing OpenCode Loop runs.
---

# Codex Autopilot Scaffold

Install or refresh a **repo-local Codex autopilot scaffold** in a target repo. The scaffold is committed project infrastructure, not an external loop service and not a recursive prompt that depends on the current chat staying alive.

Primary entrypoint:

```bash
python /path/to/skill/scripts/scaffold_repo.py --target-repo /path/to/repo --preset maintainability
```

Generated runtime architecture overview:

- See `RUNTIME-ARCHITECTURE.md` for a visual explanation of how the scaffolded target repo runs rounds, writes runtime artifacts, and exposes `status` / `watch` / `health`.

Generated repos get `automation/autopilot.py`, platform wrappers, profiles, runtime-state support, lane docs under `docs/status/lanes/`, and `automation/README.md` with detailed operator commands.

## Use / Do Not Use

Use this skill for:

- repo-owned unattended Codex autopilot scaffolding
- scaffold refreshes that must preserve existing lane docs/config/state
- queue-driven `maintainability`, `quality-gate`, `bugfix-backlog`, or `review-gated` work
- Windows/macOS bootstrap, background launch, health/status/watch workflows
- remote Mac execution after Windows-local scaffold generation

Do not use it for:

- one-shot manual debugging or app refactors
- generic programming loops
- operating an existing OpenCode Loop setup
- direct edits to the target app while scaffolding

## Hard Boundary

Only scaffold or refresh adjacent autopilot assets:

- `automation/`
- `.opencode/commands/*.md` for `review-gated`
- `docs/status/autopilot-master-plan.md`
- `docs/status/autopilot-lane-map.md`
- `docs/status/lanes/<lane-id>/autopilot-*`
- `.gitignore` entries for ignored runtime files

Do not change target application code as part of this skill.

## Decision Flow

1. **Find target repo.** Resolve Git root and inspect `AGENTS.md`, README, and existing `automation/` / `docs/status/`.
2. **Choose install mode.**
   - Fresh install: no `automation/autopilot-scaffold-version.json`.
   - Shared-controller refresh: existing scaffold; refresh common assets without resetting repo-local queue docs/config/state.
   - Regeneration: use `--force` only when the user explicitly wants generated repo-local files overwritten.
3. **Choose preset.**
   - `maintainability`: ownership reduction / refactor slices.
   - `review-gated`: plan review, implementation, code review, validation, commit.
   - `quality-gate`: lint/typecheck/test/build recovery.
   - `bugfix-backlog`: one reproducible bugfix/backlog slice per round.
4. **Infer commands.** Prefer repo evidence from `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`, or `justfile`; ask only when missing commands materially affect the scaffold.
5. **Run bundled script.** Do not recreate files by hand.
6. **Commit scaffold before execution.** The controller expects a clean worktree for unattended rounds.
7. **Create/use a dedicated branch or worktree** before `doctor`, `start`, or background launch.

## Script Options

Common overrides:

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

Seed approved plans/specs whenever the user already has one; otherwise generic backlog presets tend to drift. The script copies seeds into `docs/status/` and makes them queue authority.

## Keep-Running Contract

If the user says “跑起来 / 一直跑 / 持续跑 / 切后台 / 无人值守 / 别停 / keep running”, the job is not complete after scaffolding.

Required flow:

1. Install or refresh scaffold.
2. Commit scaffold files.
3. Move to a dedicated branch/worktree.
4. Run `doctor`.
5. Run a first-round smoke: usually `start --dry-run --single-round`; use one real foreground round when the user wants proof before daemonizing.
6. Launch the durable background path: `bootstrap-and-daemonize` before the first successful commit exists, or the platform background wrapper for no-window/background operation.
7. Run `health` against the exact intended `--state-path`.

Only say “it is running” when `health` proves all three:

- autopilot parent PID from the runtime lock is alive
- watched `progress.log` is fresh
- `automation/runtime/round-XXX/runner-status.json` shows a live `codex exec` child and non-empty `exec_confirmed_at`

If that proof is missing, report the blocker, state path, log path, saved artifacts, and next single recovery command. Do not end with a generic command list.

## Dedicated Branch Rule

A fresh scaffold may be installed on `main`, but `doctor` / `start` should fail branch guard checks there. This is expected safety behavior. Use prefixes such as:

- `autopilot/<topic>`
- `quality/<topic>`
- `bugfix/<topic>`

## Remote Mac Rollout

When execution target is `ssh mac`, keep runtime proof remote-only:

1. Scaffold locally on Windows.
2. Commit and push.
3. `ssh mac` into the remote/synced repo.
4. Fetch/pull/reset the scaffold commit.
5. Create a Mac-side dedicated worktree/branch.
6. Run Mac-side `doctor`, dry-run/foreground smoke, background start, and `health`.

Windows-local runtime files do not prove the Mac runner is alive.
Use Mac-side `health` with the same three-point proof from the keep-running contract before reporting that the remote runner is alive.
Unless the user explicitly asks for a raw file tail, operator handoff should also include one exact Windows-to-Mac `ssh mac 'cd "<remote repo>" && python3 -u ./automation/autopilot.py watch ... --prefix-format short'` command bound to the intended `--state-path`.

## Preset-Specific Rules

**Review-gated**

- Use `review-gated` for “先审方案，再审代码”.
- Generated assets include `.opencode/commands/review-plan.md`, `.opencode/commands/review-code.md`, `automation/opencode-review.sh`, and `automation/Invoke-OpencodeReview.ps1`.
- Review wrappers may take minutes; slow polling is not a stuck run.
- If a repo layers an OpenCode implementation helper on top of this scaffold, require a background-task-aware completion contract: background tasks are allowed, but the round must not advance until those tasks finish and the final output artifacts are actually written.
- Do not invoke `opencode` unless the user explicitly requested OpenCode review behavior or the selected preset requires the repo-local review wrapper.

**Commit prefix**

- Successful round commits must start with the configured `commit_prefix`, default `autopilot:`.
- Repeated prefix failures mean prompt/config mismatch, not target-code failure.

**Build/deploy**

- `build_ran=true` requires a real non-empty `build_id`.
- If no trustworthy build marker exists, report `build_ran=false`.
- `deploy_ran=true` requires a real deploy and `deploy_verified=true`; prefer `deploy_policy=targeted` over `always`.

**Command budgets**

- Diagnostic `git status --short` / `git diff --stat` budget findings default to warnings via `command_budget_policy: "warn"`.
- Do not roll back successful work solely for budget warnings unless the repo deliberately opts into hard enforcement.

**Failure recovery**

- Failed rounds preserve safety refs under `refs/autopilot/safety/*`, stash dirty work, and reset to the round start.
- If visible work succeeded but state says failed, inspect runtime logs for controller validation findings before chasing app bugs.

## Operator Commands

Prefer the exact commands printed by `scripts/scaffold_repo.py` and the generated `automation/README.md`.

Core checks:

```bash
python automation/autopilot.py version
python automation/autopilot.py doctor --profile windows
python automation/autopilot.py start --profile windows --dry-run --single-round
python automation/autopilot.py bootstrap-and-daemonize --profile windows
python automation/autopilot.py health --state-path automation/runtime/autopilot-state.json
python automation/autopilot.py status --state-path automation/runtime/autopilot-state.json
python automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/autopilot-state.json --tail 80 --prefix-format short
```

Use `python3` and `--profile mac` on macOS. Use scaffolded wrappers for Windows no-window launches and macOS background/watch convenience.

When multiple state files or old `round-*` directories exist, always bind `status`, `health`, and `watch` to the intended `--state-path`.
When a user asks to look at logs, default to the scaffolded `watch` command above instead of a raw `tail`/`Get-Content`, because the prefixed stream keeps lane/queue/round context visible on every line.
When the operator is on Windows and the unattended runner is on `ssh mac`, default to the full remote command with `python3 -u` so the stream is unbuffered:
`ssh mac 'cd "<remote repo>" && python3 -u ./automation/autopilot.py watch --runtime-path automation/runtime --state-path <state-path> --tail 80 --prefix-format short'`

## Cutovers

Prefer built-in `restart-after-next-commit` or scaffolded `Arm-AutopilotCutover.ps1` / `arm-autopilot-cutover.sh` over ad-hoc shell sentinels.

- Use `bootstrap-and-daemonize` before the first successful commit exists.
- Use `restart-after-next-commit` after a live run has a successful commit to watch.
- For code/prompt replacement, prepare a replacement ref and pass `--restart-sync-ref <ref>`.
- Keep custom machine-local sentinels outside the repo unless explicitly requested.

## Final Report

Report:

- chosen preset and target repo
- install mode: fresh install, refresh, or intentional regeneration
- inferred/overridden validation commands
- files added/refreshed
- smoke commands run and result
- if continuous execution was requested: launch command, state path, health verdict, progress log path, PID evidence, and `exec_confirmed_at` from `runner-status.json`
- if log-following is relevant: one exact copy-paste `watch` command with explicit `--state-path`, explicit `--runtime-path`, and `--prefix-format short`; on Windows→Mac handoff this should be the full `ssh mac ... python3 -u ... watch ...` command
- if not verified: exact blocker and next recovery command
