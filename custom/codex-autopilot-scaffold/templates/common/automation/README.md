# Repository Autopilot

This folder contains a repo-local unattended Codex autopilot scaffold.

## Files

- `automation/autopilot.py`: cross-platform outer controller
- `automation/autopilot-config.json`: repo-specific objective, queue, validation, and runner settings
- `automation/profiles/windows.json`: machine-neutral Windows defaults
- `automation/profiles/mac.json`: machine-neutral macOS defaults
- `automation/round-prompt.md`: per-round runner prompt template
- `automation/round-result.schema.json`: structured final-response contract
- `automation/runtime/`: ignored runtime state, logs, prompts, and round results
- `docs/status/autopilot-master-plan.md`: strategy and lane priorities
- `docs/status/autopilot-lane-map.md`: quick entrypoints for the current queue
- `docs/status/autopilot-round-roadmap.md`: queued `[NEXT]` / `[QUEUED]` work items

## Core guarantees

- Every round uses `codex exec` in a new non-interactive session
- Loop control lives in the Python controller, not in a recursive prompt
- Runtime state is machine-readable JSON
- Failed rounds hard-reset the worktree to the round's starting `HEAD`
- Successful rounds must write a phase doc and create a commit
- A runtime lock prevents two machines from driving the same branch simultaneously

## Main commands

Before starting unattended rounds, commit the scaffolded autopilot files so the worktree is clean.

### Windows

```powershell
python .\automation\autopilot.py doctor --profile windows
python .\automation\autopilot.py start --profile windows
```

### macOS

```bash
python3 ./automation/autopilot.py doctor --profile mac
python3 ./automation/autopilot.py start --profile mac
```

### Helpful modes

```text
python automation/autopilot.py status
python automation/autopilot.py watch
python automation/autopilot.py start --profile windows --dry-run --single-round
python automation/autopilot.py start --profile windows --single-round
python automation/autopilot.py restart-after-next-commit --profile windows
```

## Watching the right logs

If this repo ever accumulates multiple autopilot runs or old `round-*` directories, bind your operator commands to the exact state file you care about.

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

The scaffolded `watch` output shows:

- `round`
- `phase`
- `status`
- `failures`
- `phase doc`
- `focus`
- the exact `progress.log` path being followed

When the watched state is `active`, the live progress log is usually `current_round + 1`. When the watched state is terminal, it is usually `current_round`.

## Sentinel cutovers

Use `restart-after-next-commit` when you want the current unattended run to finish its next successful round, stop cleanly, and relaunch with replacement settings.

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

## Profile overrides

Committed profile files stay machine-neutral. Put local absolute paths in an external profile JSON and pass it with `--profile-path`.

Example override fields:

```json
{
  "runner_additional_dirs": [
    "C:\\\\absolute\\\\path\\\\to\\\\extra\\\\workspace"
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

## Windows convenience scripts

- `automation/New-AutopilotWorktree.ps1`
- `automation/Start-Autopilot.ps1`
- `automation/Watch-Autopilot.ps1`

These are thin Windows wrappers around the Python CLI. macOS should use `python3 ./automation/autopilot.py ...` directly.
