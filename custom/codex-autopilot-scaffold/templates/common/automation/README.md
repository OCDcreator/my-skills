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
