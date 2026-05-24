# AGENTS.md

## Repo overview

my-skills is a Git-based collection of AI agent skills and external reference libraries. No build/test/lint steps.
The two main skill trees are `custom/` (self-authored skills) and `external/` (cloned upstream skill sources and reference sources). Repo-local automation and status docs live in `automation/` and `docs/`; utility scripts live in `scripts/`.

## When adding a new skill

### Custom skill (`custom/`)

1. Create a leaf skill directory anywhere under `custom/` and put `SKILL.md` at that leaf
2. `custom/` can contain grouped paths, but keep single-purpose skills at the leaf path the user expects; nested families like `custom/x-reader/*` already exist
3. If the immediate job is to choose which skill from this repo should be loaded for real work, use `custom/skill-router` first; it should inspect this repo as the source of truth, not an installed mirror
4. Update `README.md`: add entry to directory tree + custom skill table
5. If `SKILLS.md` exists or the user asks for a skill catalog or catalog maintenance, use `custom/skill-catalog-maintainer` and include source repo/subdir/install hints in the catalog
   - For project-specific recommendations, install hints should name target paths for Claude Code (`.claude/skills`), OpenCode (`.opencode/skills`), and/or Codex (`.agents/skills`)
6. Run `python3 scripts/generate_skills_catalog.py` and `python3 scripts/verify_structure.py`
7. Commit and push

### External skill (`external/`)

When adding a new external source, **all four files** must be updated:

1. **`external/<name>/`** — clone the repo, remove `.git/`, keep only dirs containing `SKILL.md`
2. **`update.sh`** — append to `SKILL_SOURCES` array:
   ```
   "name|https://github.com/owner/repo.git|branch|subdir|mode"
   ```
   - `subdir`: path inside the cloned repo where skills live (e.g. `skills`, `.` if at root)
   - `mode`: optional copy mode. Leave blank for flattened leaf skill dirs, use `preserve` when duplicate leaf skill names require keeping the relative source path
   - Script auto-discovers dirs containing `SKILL.md` under that subdir
   - Example: `"anthropics-skills|https://github.com/anthropics/skills.git|main|skills"`
3. **`update.ps1`** — add a matching `$SkillSources` entry and keep copy-mode behavior aligned with `update.sh`
4. **`README.md`** — update three places:
   - Directory tree under `external/`
   - External sources table (columns: local dir, source repo link, description)
   - Source count in the `update.sh` / `update.ps1` row of the scripts table
5. **`SKILLS.md`** — if present, update the skill catalog using `custom/skill-catalog-maintainer`; external entries should keep source repo, branch, subdir, and install hints. Project install hints should mention `.claude/skills`, `.agents/skills`, and `.opencode/skills` where relevant.
6. Run `python3 scripts/generate_skills_catalog.py` and `python3 scripts/verify_structure.py`

### External reference source (`external/`)

Use this for upstream repositories that are useful to agents but do not contain `SKILL.md` files.

When adding a new external reference source, update all four files:

1. **`external/<name>/`** — clone the repo, remove `.git/`, keep only the reference material the repo intentionally mirrors
2. **`update.sh`** — append to `REFERENCE_SOURCES` and keep the copy logic aligned with the upstream structure
3. **`update.ps1`** — add the matching Windows clone+copy block and keep the reference counters consistent
4. **`README.md`** — update the directory tree, the external reference table, and the update-script description if the wording changes
5. Run `python3 scripts/generate_skills_catalog.py` and `python3 scripts/verify_structure.py`

Reference-source rules:

- A directory under `external/` only counts as a skill source when the mirrored leaf directories contain `SKILL.md`
- Repositories like `awesome-design-md` may live under `external/` as reference libraries, but they must not be cataloged as skills
- If `SKILLS.md` exists, do not add reference-source directories to the skill index unless they later gain real `SKILL.md` files

## Gotchas

- **`update.ps1` mirrors `.sh` manually**: there is no code generation; any change to `.sh` must be replicated to `.ps1` by hand.
- **`EXCLUDE_NAMES` must match in `update.sh` and `update.ps1`**: both scripts filter excluded skill names; keep the arrays and behavior aligned.
- **`external/<name>/` structure varies by source**: some sources put skill dirs directly under the cloned root (subdir=`.`), others use a `skills/` subdirectory (subdir=`skills`). The `update.sh` `SKILL_SOURCES` `subdir` field controls this.
- **Duplicate leaf skill names need `preserve` mode**: sources like deep-research-skills contain repeated names under language/platform groups, so keep the relative source path instead of flattening.
- **Duplicate skill names are normal**: catalog external skills by path and source, not by `name` alone.

## Script details

| Script | Purpose | Key behavior |
|--------|---------|--------------|
| `update.sh` / `.ps1` | Sync external skill sources and reference sources | `git clone --depth 1`, copy mirrored content, auto commit+push if changed |
| `push.sh` / `.ps1` | Push local changes | `git add -A` + commit + push |
| `pull.sh` / `.ps1` | Hard reset to remote | `git reset --hard origin/main` (destructive — discards uncommitted work) |

- `.sh` is canonical; `.ps1` mirrors for Windows
- `update.sh` uses `SKILL_SOURCES` and `REFERENCE_SOURCES`; `update.ps1` mirrors them manually with PowerShell clone/copy blocks
- Temp clone directory: `.tmp-skills/` (gitignored)
- `scripts/generate_skills_catalog.py` regenerates `SKILLS.md`; `scripts/verify_structure.py` is the lightweight structure gate

## Conventions

- Only branch: `main`
- Remote: `origin` → `git@github.com:OCDcreator/my-skills.git`
- No dependencies, no package manager, no build system
- Every skill must contain a `SKILL.md` at its directory root
- Self-authored skills belong under `custom/`; do not add root-level skill directories
