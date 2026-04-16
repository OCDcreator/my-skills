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

## Final response pattern

When you finish scaffolding, report:

- chosen preset
- target repo path
- commands inferred or overridden
- files added
- smoke-test commands run and their result
- the next command the user or future agent should run
