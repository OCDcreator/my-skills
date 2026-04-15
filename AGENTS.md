# AGENTS.md

## Repo overview

my-skills is a Git-based skill collection for AI coding agents. No build/test/lint steps.
Two top-level directories: `custom/` (self-authored) and `external/` (cloned from upstream repos).

## When adding a new skill

### Custom skill (`custom/`)

1. Create a leaf skill directory anywhere under `custom/` and put `SKILL.md` at that leaf
2. `custom/` is not flat: grouped paths like `custom/devops/syncthing` and nested families like `custom/x-reader/*` already exist
3. Update `README.md`: add entry to directory tree + custom skill table
4. If `SKILLS.md` exists or the user asks for a skill catalog, use `custom/skill-catalog-maintainer` and update the catalog too
5. Commit and push

### External skill (`external/`)

When adding a new external source, **all four files** must be updated:

1. **`external/<name>/`** — clone the repo, remove `.git/`, keep only dirs containing `SKILL.md`
2. **`update.sh`** — append to `SOURCES` array:
   ```
   "name|https://github.com/owner/repo.git|branch|subdir"
   ```
   - `subdir`: path inside the cloned repo where skills live (e.g. `skills`, `.` if at root)
   - Script auto-discovers dirs containing `SKILL.md` under that subdir
   - Example: `"anthropics-skills|https://github.com/anthropics/skills.git|main|skills"`
3. **`update.bat`** — add a numbered clone+copy block following the existing pattern
   - **Update all `[N/M]` counters** in every block to match new total (e.g. `[1/7]`..`[7/7]`)
   - Counter is in two places: the `echo [N/M]` line and must be consistent across all blocks
4. **`README.md`** — update three places:
   - Directory tree under `external/`
   - External sources table (columns: local dir, source repo link, description)
   - Source count in the `update.sh` / `update.bat` row of the scripts table
5. **`SKILLS.md`** — if present, update the skill catalog using `custom/skill-catalog-maintainer`

## Gotchas

- **`update.bat` counters drift easily**: every `[N/M]` in every block must be updated when adding/removing a source. Verify all counters are consistent after edits.
- **`EXCLUDE_NAMES` only in `update.sh`**: the `.sh` script filters out excluded skill names; `.bat` has no exclusion logic and copies everything.
- **`external/<name>/` structure varies by source**: some sources put skill dirs directly under the cloned root (subdir=`.`), others use a `skills/` subdirectory (subdir=`skills`). The `update.sh` SOURCES `subdir` field controls this.
- **`.bat` mirrors `.sh` manually**: there is no code generation; any change to `.sh` must be replicated to `.bat` by hand.
- **Duplicate skill names are normal**: catalog external skills by path and source, not by `name` alone.

## Script details

| Script | Purpose | Key behavior |
|--------|---------|--------------|
| `update.sh` / `.bat` | Sync all external sources | `git clone --depth 1`, copy SKILL.md dirs, auto commit+push if changed |
| `push.sh` / `.bat` | Push local changes | `git add -A` + commit + push |
| `pull.sh` / `.bat` | Hard reset to remote | `git reset --hard origin/main` (destructive — discards uncommitted work) |

- `.sh` is canonical; `.bat` mirrors for Windows
- `update.sh` uses a `SOURCES` array with pipe-delimited `name|url|branch|subdir`; `update.bat` has inline clone blocks
- Temp clone directory: `.tmp-skills/` (gitignored)

## Conventions

- Only branch: `main`
- Remote: `origin` → `git@github.com:OCDcreator/my-skills.git`
- No dependencies, no package manager, no build system
- Every skill must contain a `SKILL.md` at its directory root
