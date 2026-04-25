# Repository Autopilot

This folder contains a repo-local unattended Codex autopilot scaffold.

## Files

- `automation/autopilot.py`: cross-platform CLI entrypoint for the repo-local controller
- `automation/_autopilot/`: stdlib-only support modules for controller runtime helpers and support wiring, lane/state lifecycle handling, locking, CLI assembly, start/runtime orchestration, watch/status flows, runner execution, round lifecycle/prompt flow, process lifecycle/restart flows, doctor checks, and result validation
- `automation/autopilot-scaffold-version.json`: deployed scaffold name/version marker
- `automation/Arm-AutopilotCutover.ps1`: Windows post-commit cutover wrapper
- `automation/arm-autopilot-cutover.sh`: macOS post-commit cutover wrapper
- `automation/start-autopilot.sh`: macOS start wrapper with optional background mode
- `automation/watch-autopilot.sh`: macOS watch wrapper
- `automation/launchd/com.example.codex-autopilot.plist`: launchd example for repo-local background launches
- `automation/autopilot-config.json`: repo-specific objective, queue, validation, and runner settings
- `automation/opencode-review.sh`: review wrapper for macOS/Linux when the `review-gated` preset is installed
- `automation/Invoke-OpencodeReview.ps1`: review wrapper for Windows when the `review-gated` preset is installed
- `automation/profiles/windows.json`: machine-neutral Windows defaults
- `automation/profiles/mac.json`: machine-neutral macOS defaults
- `automation/round-prompt.md`: per-round runner prompt template
- `automation/round-result.schema.json`: structured final-response contract
- `automation/runtime/`: ignored runtime state, logs, prompts, and round results
- `docs/status/autopilot-master-plan.md`: static cross-lane strategy overview
- `docs/status/autopilot-lane-map.md`: static index of configured lane directories
- `docs/status/lanes/<lane-id>/autopilot-round-roadmap.md`: lane-local queued `[NEXT]` / `[QUEUED]` work items
- `docs/status/lanes/<lane-id>/autopilot-phase-0.md`: lane-local baseline phase document

## Core guarantees

- Every round uses `codex exec` in a new non-interactive session
- Loop control lives in the Python controller, not in a recursive prompt
- Runtime state is machine-readable JSON
- Queue routing is driven by explicit `lanes` in `automation/autopilot-config.json`
- Failed rounds preserve the pre-reset `HEAD` under `refs/autopilot/safety/*`, stash dirty work, then reset to the round's starting `HEAD`
- Diagnostic command budget findings default to warnings, so repeated `git status --short` or `git diff --stat` reports do not roll back otherwise successful commits
- `health` is the truth source for runner liveness because it checks state, lock, pid, and progress-artifact freshness together
- Successful rounds must write a phase doc and create a commit
- A runtime lock prevents two machines from driving the same branch simultaneously

## Main commands

Before starting unattended rounds:

1. Commit the scaffolded autopilot files so the worktree is clean.
2. Create or switch to a dedicated branch/worktree such as `autopilot/<topic>`, `quality/<topic>`, or `bugfix/<topic>`.
3. Then run `doctor` and `start`.

Running `doctor` on `main` right after scaffold may fail the branch guard by design. That is a safety signal, not an installation failure.

## Keep-running startup contract

Do not confuse "scaffold installed" with "autopilot is running." A chat agent or terminal session can stop; this repo-local controller is the durable runner.

When the operator asks for continuous unattended work:

1. Commit the scaffolded files.
2. Switch to a dedicated branch/worktree.
3. Run `doctor` for the target profile.
4. Run a dry-run or foreground first-round smoke if requested.
5. Start the durable path with `bootstrap-and-daemonize` or the platform background wrapper.
6. Verify with `health` bound to the intended state file before reporting success.

Only claim the next round is running when `health` shows the autopilot parent PID alive, a fresh `progress.log`, and a live `codex exec` child recorded in `automation/runtime/round-XYZ/runner-status.json` with `exec_confirmed_at`.

## Commit Prefix Gate

`automation/autopilot.py` validates successful round commits against `commit_prefix` in `automation/autopilot-config.json`.

- Non-empty `commit_prefix`: successful commit subjects must start with `<commit_prefix>:` such as `autopilot:`.
- Empty `commit_prefix`: no commit-message prefix is enforced.
- The controller injects this rule into every rendered round prompt, including custom prompt templates.
- If rounds complete useful work but fail with `Commit message must start with ...`, either amend the commit subject to the configured prefix or intentionally set `commit_prefix` to an empty string for that lane.

## Build And Deploy Result Gate

The controller also validates build/deploy result fields in the final JSON:

- `build_ran=true` requires a non-empty `build_id`.
- If the round did not produce a trustworthy build marker, report `build_ran=false` instead of fabricating a `build_id`.
- `deploy_ran=true` is only valid when the round actually performed a deploy required by config.
- `deploy_ran=true` also requires `deploy_verified=true`, and deploy verification may additionally check that the configured artifact contains the reported `build_id`.

## Command Budget Policy

`automation/autopilot-config.json` includes:

```json
"command_budget_policy": "warn"
```

With the default policy, repeated diagnostic commands such as `git status --short` and `git diff --stat` are reported as controller warnings instead of hard failures. This prevents a successful commit from being reset only because the agent inspected Git state too often.

If a project deliberately wants strict enforcement, set `command_budget_policy` to `hard`, `fail`, or `error`.

## Seeded Plan Or Spec

If the scaffold was created with `--seed-plan` or `--seed-spec`, the source is copied to `docs/status/autopilot-seed-plan.md` or `docs/status/autopilot-seed-spec.md`, and lane roadmaps contain a seeded queue override.

- Treat the seed as the approved execution source before generic preset prose.
- Execute one seed slice per round.
- Keep progress notes current so the next unattended round can find the next seed slice without inventing a backlog.

### Windows

```powershell
python .\automation\autopilot.py doctor --profile windows
python .\automation\autopilot.py health --state-path automation\runtime\autopilot-state.json
python .\automation\autopilot.py start --profile windows
python .\automation\autopilot.py bootstrap-and-daemonize --profile windows
```

For a true no-window unattended launch on Windows, prefer the wrapper's background mode instead of starting `py.exe` in a new visible console. The wrapper should run through a hidden PowerShell host that launches `py` / `python` without depending on `pythonw` / `pyw` shims:

```powershell
.\automation\Start-Autopilot.ps1 -Background --% --profile windows
```

### macOS

```bash
python3 ./automation/autopilot.py doctor --profile mac
python3 ./automation/autopilot.py health --state-path automation/runtime/autopilot-state.json
python3 ./automation/autopilot.py start --profile mac
python3 ./automation/autopilot.py bootstrap-and-daemonize --profile mac
```

For a repo-local macOS wrapper flow, prefer `bash ./...` so Windows-authored commits do not depend on POSIX executable bits surviving the sync path:

```bash
bash ./automation/start-autopilot.sh -- --profile mac
bash ./automation/watch-autopilot.sh --state-path automation/runtime/autopilot-state.json --tail 80
```

### Remote Mac Rollout From Windows

When the scaffold is created locally on Windows but execution should happen on the Mac:

```bash
git push
ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo> && git fetch --all --prune'
ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo> && git worktree add ../<repo>-autopilot autopilot/<topic>'
ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && python3 ./automation/autopilot.py doctor --profile mac'
ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && python3 ./automation/autopilot.py health --state-path automation/runtime/autopilot-state.json'
ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && python3 ./automation/autopilot.py bootstrap-and-daemonize --profile mac'
ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && bash ./automation/start-autopilot.sh --background -- --profile mac'
ssh mac 'cd /Volumes/SDD2T/obsidian-vault-write/custom-project/<repo>-autopilot && python3 ./automation/autopilot.py health --state-path automation/runtime/autopilot-state.json'
```

Adjust `<repo>` and `<topic>` to the actual repository and branch names. Keep runtime state in the Mac worktree you intend to watch, and use Mac-side `health` with the same parent-PID / fresh-log / runner-status proof before reporting that the remote runner is alive.

### Helpful modes

```text
python automation/autopilot.py version
python automation/autopilot.py status
python automation/autopilot.py health
python automation/autopilot.py watch
python automation/autopilot.py start --profile windows --dry-run --single-round
python automation/autopilot.py start --profile windows --single-round
python automation/autopilot.py bootstrap-and-daemonize --profile windows
python automation/autopilot.py restart-after-next-commit --profile windows
bash ./automation/start-autopilot.sh --background -- --profile mac
```

`start --dry-run --single-round` only renders the next prompt. It leaves the state in `stopped_dry_run` so `status` / `health` do not pretend a live unattended runner exists, and a later real `start` automatically resumes from that preview state.

## Review-gated preset

If this repo was scaffolded with the `review-gated` preset, the scaffold also commits repo-local review assets:

- `.opencode/commands/review-plan.md`
- `.opencode/commands/review-code.md`
- `automation/opencode-review.sh`
- `automation/Invoke-OpencodeReview.ps1`

Those review wrappers are intentionally slow-friendly. They emit periodic “still running” heartbeats because reviewer runs can take minutes.

### Windows review wrapper

```powershell
pwsh -File .\automation\Invoke-OpencodeReview.ps1 -Mode plan -PlanPath automation\runtime\round-001\implementation-plan.md -OutputPath automation\runtime\round-001\plan-review.txt
pwsh -File .\automation\Invoke-OpencodeReview.ps1 -Mode code -OutputPath automation\runtime\round-001\code-review.txt
```

### macOS/Linux review wrapper

```bash
bash ./automation/opencode-review.sh plan automation/runtime/round-001/implementation-plan.md automation/runtime/round-001/plan-review.txt
bash ./automation/opencode-review.sh code automation/runtime/round-001/code-review.txt
```

The generated `.gitignore` should explicitly unignore the committed `.opencode/commands/*.md` review assets so repo-local review flows survive commit/push/pull.

## Deploy policy

Prefer `deploy_policy=targeted` or `deploy_policy=never` for most unattended repos. Deploying after every successful round is usually unnecessary churn.

## Versioned scaffold upgrades

The scaffold records its deployed version in `automation/autopilot-scaffold-version.json`.

- Re-running the scaffold script against an older deployed version auto-refreshes common controller assets such as `automation/autopilot.py`, `automation/_autopilot/`, wrappers, profiles, schema, and this version marker.
- Repo-local queue docs, prompts, and `automation/autopilot-config.json` stay in place during that automatic upgrade path.
- Use `python automation/autopilot.py version` to confirm what version a target repo is currently running.
- Use `--force` only when you intentionally want to overwrite repo-local generated files beyond the shared controller layer.

- Use `deploy_policy=targeted` when only specific files or directories should trigger deploy
- Keep `deploy_required_paths` narrow and repo-relative
- Reserve `deploy_policy=always` for repos where every successful build must publish a runtime artifact

## Watching the right logs

If this repo ever accumulates multiple autopilot runs or old `round-*` directories, bind your operator commands to the exact state file you care about.

### Windows

```powershell
python .\automation\autopilot.py status --state-path automation\runtime\<state-file>.json
python .\automation\autopilot.py health --runtime-path automation\runtime --state-path automation\runtime\<state-file>.json
python .\automation\autopilot.py watch --runtime-path automation\runtime --state-path automation\runtime\<state-file>.json --tail 80 --prefix-format short
Get-Content automation\runtime\round-XYZ\progress.log -Wait -Tail 80
```

### macOS

```bash
python3 ./automation/autopilot.py status --state-path automation/runtime/<state-file>.json
python3 ./automation/autopilot.py health --runtime-path automation/runtime --state-path automation/runtime/<state-file>.json
python3 ./automation/autopilot.py watch --runtime-path automation/runtime --state-path automation/runtime/<state-file>.json --tail 80 --prefix-format short
tail -n 80 -F automation/runtime/round-XYZ/progress.log
```

The scaffolded `watch` output shows:

- `round`
- `phase`
- `lane`
- `queue progress`
- `status`
- `health`
- `failures`
- `phase doc`
- `focus`
- the exact `progress.log` path being followed
- a per-line prefix on every streamed detail line, with `--prefix-format short` recommended for operator handoff by default
- the long form `[lane=b1-backlog-slice queue=1/3 round=006 phase=005 status=active failures=0]` when you need the fully spelled-out header
- Vulture count and delta when `vulture_command` is configured
- latest plan/code review verdicts and last blocker when the round recorded them

Default operator handoff should use `watch ... --prefix-format short` so every streamed line stays attributable even after copy/paste into another terminal or log collector.

Use raw `Get-Content` / `tail -F` only when you explicitly want the underlying `progress.log` without autopilot metadata prefixes.

When the watched state is `active`, the live progress log is usually `current_round + 1`. When the watched state is terminal, it is usually `current_round`.

Use `health` when `status=active` looks suspicious. It exists specifically for the case where the JSON state still says active but the runner process already exited.

Do not tell an operator “the next round is running” until `health` confirms all of these:

- the autopilot parent PID from the runtime lock is alive
- the watched round `progress.log` is still updating
- the watched round `runner-status.json` shows a live `codex exec` child PID and a non-empty `exec_confirmed_at`

Useful per-round runtime artifacts usually live together under `automation/runtime/round-XYZ/`:

- `progress.log`
- `events.jsonl`
- `assistant-output.json`
- `runner-status.json`

For queue-driven presets, a round result of `goal_complete` means the current lane's `[NEXT]` slice was already done. If the active lane roadmap still has another `[NEXT]` or any `[QUEUED]` work, the controller keeps the same lane active and advances `next_phase_number`; if the lane is clear, it immediately switches to the next configured lane or marks the overall objective complete.

## Sentinel cutovers

Use `restart-after-next-commit` when you want the current unattended run to finish its next successful round, stop cleanly, and relaunch with replacement settings.

If there is not yet a successful commit for the watched state line, `restart-after-next-commit` has nothing to watch. In that first-round bootstrap window, use `bootstrap-and-daemonize` instead.

For routine operator handoffs, prefer the scaffolded wrappers:

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

### Config/profile/state cutover

Use this when you only need to swap config, profile, output, or state paths.

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

### Code/prompt cutover via git ref

Use this when the replacement run should resume from a prepared commit on another ref, such as a cutover worktree branch.

1. Prepare the replacement commit on a sibling ref.
2. Launch the sentinel against the currently active state line.
3. Pass `--restart-sync-ref <cutover-ref>` so the controller waits for that ref, fast-forwards to it, and relaunches unattended work.

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

Prefer this built-in sentinel flow over ad-hoc shell loops. Only fall back to a custom local script when the cutover must run machine-local actions that cannot be expressed through git refs and restart arguments.

The generated Python entrypoint and wrapper scripts keep bytecode disabled, and the scaffolded `.gitignore` covers fallback bytecode paths:

- `automation/**/__pycache__/`
- `automation/**/*.pyc`

This prevents generated bytecode from making `doctor`, `start`, or a replacement cutover run fail the clean-worktree guard.

## Profile overrides

Committed profile files stay machine-neutral. Put local absolute paths in an external profile JSON and pass it with `--profile-path`.

Example override fields:

```json
{
  "runner_additional_dirs": [
    "C:\\absolute\\path\\to\\extra\\workspace"
  ],
  "deploy_verify_path": ""
}
```

Typical usage:

```powershell
python .\automation\autopilot.py start --profile windows --profile-path C:\Users\you\.config\codex-autopilot\windows.profile.json
```

```bash
python3 ./automation/autopilot.py start --profile mac --profile-path /Users/you/.config/codex-autopilot/mac.profile.json
```

## macOS convenience scripts

- `automation/start-autopilot.sh` (foreground by default, `--background` for nohup launches)
- `automation/watch-autopilot.sh`
- `automation/arm-autopilot-cutover.sh`

To turn the scaffold into a LaunchAgent:

1. Copy `automation/launchd/com.example.codex-autopilot.plist` to `~/Library/LaunchAgents/com.<repo>.codex-autopilot.plist`
2. Replace every `/ABSOLUTE/PATH/TO/REPO` placeholder
3. Load it with:

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.<repo>.codex-autopilot.plist
launchctl kickstart -k gui/$(id -u)/com.<repo>.codex-autopilot
```

To stop and unload it later:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.<repo>.codex-autopilot.plist
```

## Windows convenience scripts

- `automation/New-AutopilotWorktree.ps1`
- `automation/Start-Autopilot.ps1` (interactive by default, `-Background` for no-window launches)
- `automation/Watch-Autopilot.ps1`

These are thin Windows wrappers around the Python CLI. `autopilot.py` already hides child `cmd.exe` / `pwsh.exe` subprocess windows, and `Start-Autopilot.ps1 -Background` should use a hidden PowerShell host so the top-level launcher also stays windowless even when `pythonw` / `pyw` shims are unreliable.
