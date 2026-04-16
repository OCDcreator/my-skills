# AGENTS.md

## Repo overview

my-skills is a Git-based collection of AI agent skills and external reference libraries. No build/test/lint steps.
Two top-level directories: `custom/` (self-authored skills) and `external/` (cloned upstream skill sources and reference sources).

## When adding a new skill

### Custom skill (`custom/`)

1. Create a leaf skill directory anywhere under `custom/` and put `SKILL.md` at that leaf
2. `custom/` can contain grouped paths, but keep single-purpose skills at the leaf path the user expects; nested families like `custom/x-reader/*` already exist
3. Update `README.md`: add entry to directory tree + custom skill table
4. If `SKILLS.md` exists or the user asks for a skill catalog, use `custom/skill-catalog-maintainer` and include source repo/subdir/install hints in the catalog
   - For project-specific recommendations, install hints should name target paths for Claude Code (`.claude/skills`), OpenCode (`.opencode/skills`), and/or Codex (`.agents/skills`)
5. Commit and push

### External skill (`external/`)

When adding a new external source, **all four files** must be updated:

1. **`external/<name>/`** — clone the repo, remove `.git/`, keep only dirs containing `SKILL.md`
2. **`update.sh`** — append to `SKILL_SOURCES` array:
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
5. **`SKILLS.md`** — if present, update the skill catalog using `custom/skill-catalog-maintainer`; external entries should keep source repo, branch, subdir, and install hints. Project install hints should mention `.claude/skills`, `.agents/skills`, and `.opencode/skills` where relevant.

### External reference source (`external/`)

Use this for upstream repositories that are useful to agents but do not contain `SKILL.md` files.

When adding a new external reference source, update all four files:

1. **`external/<name>/`** — clone the repo, remove `.git/`, keep only the reference material the repo intentionally mirrors
2. **`update.sh`** — append to `REFERENCE_SOURCES` and keep the copy logic aligned with the upstream structure
3. **`update.bat`** — add the matching Windows clone+copy block and keep the reference counters consistent
4. **`README.md`** — update the directory tree, the external reference table, and the update-script description if the wording changes

Reference-source rules:

- A directory under `external/` only counts as a skill source when the mirrored leaf directories contain `SKILL.md`
- Repositories like `awesome-design-md` may live under `external/` as reference libraries, but they must not be cataloged as skills
- If `SKILLS.md` exists, do not add reference-source directories to the skill index unless they later gain real `SKILL.md` files

## Gotchas

- **`update.bat` counters drift easily**: every `[N/M]` in every block must be updated when adding/removing a source. Verify all counters are consistent after edits.
- **`EXCLUDE_NAMES` only in `update.sh`**: the `.sh` script filters out excluded skill names; `.bat` has no exclusion logic and copies everything.
- **`external/<name>/` structure varies by source**: some sources put skill dirs directly under the cloned root (subdir=`.`), others use a `skills/` subdirectory (subdir=`skills`). The `update.sh` `SKILL_SOURCES` `subdir` field controls this.
- **`.bat` mirrors `.sh` manually**: there is no code generation; any change to `.sh` must be replicated to `.bat` by hand.
- **Duplicate skill names are normal**: catalog external skills by path and source, not by `name` alone.

## Script details

| Script | Purpose | Key behavior |
|--------|---------|--------------|
| `update.sh` / `.bat` | Sync external skill sources and reference sources | `git clone --depth 1`, copy mirrored content, auto commit+push if changed |
| `push.sh` / `.bat` | Push local changes | `git add -A` + commit + push |
| `pull.sh` / `.bat` | Hard reset to remote | `git reset --hard origin/main` (destructive — discards uncommitted work) |

- `.sh` is canonical; `.bat` mirrors for Windows
- `update.sh` uses `SKILL_SOURCES` and `REFERENCE_SOURCES`; `update.bat` mirrors them manually with inline clone blocks
- Temp clone directory: `.tmp-skills/` (gitignored)

## Conventions

- Only branch: `main`
- Remote: `origin` → `git@github.com:OCDcreator/my-skills.git`
- No dependencies, no package manager, no build system
- Every skill must contain a `SKILL.md` at its directory root
