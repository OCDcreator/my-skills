# Target Skill Scope

## `custom/` only

skill-evolution edits target skill paths under `custom/` only. A target path outside `custom/` must be refused. This is a Hard Contract rule.

## Why `external/` is refused

`external/` skills are upstream mirrors. `update_external.py` (run by `update.sh` / `update.ps1`) re-clones and overwrites them on sync. Any local edit to an `external/` skill is destroyed on the next sync. The repo's `config/sources.yaml` is the source of truth for external sources, not the checked-out mirror.

## Fork-first path

To improve an `external/` skill:

1. Copy it into `custom/` (e.g. `custom/<name>-fork/`), with a `provenance` note pointing at the upstream repo + commit.
2. Run skill-evolution against the `custom/` fork.
3. (Optional) upstream the improvement back to the source repo via its own contribution process — out of scope for skill-evolution.

## Path resolution algorithm

1. **Known repo root** — `C:\Users\lt\Desktop\Write\custom-project\my-skills` (the same hardcoded root `custom/skill-router` uses), then `custom/<skill>/`.
2. **realpath fallback** — resolve `os.path.realpath` on the loaded skill path; accept only if it lands inside `<root>/custom/`.
3. **Ask the user** — if both fail. This is a normal path, not an error. Never guess; never write to an unverified location.

Validate the resolved path starts with `<root>/custom/` before any read/write.
