# AGENTS.md

## Repo overview

my-skills is a Git-based collection of AI agent skills and external reference libraries. No build/test/lint steps.
The two main skill trees are `custom/` (self-authored skills) and `external/` (cloned upstream skill sources and reference sources). Repo-local automation and status docs live in `automation/` and `docs/`; utility scripts live in `scripts/`.

## Architecture

```
config/sources.yaml          # Single source of truth for all external sources
scripts/update_external.py   # Core sync logic (replaces duplicated sh/ps1)
scripts/generate_skills_catalog.py  # Generates SKILLS.md + docs/full-catalog.md + README blocks
scripts/verify_structure.py  # Governance gate: checks catalog invariants
update.sh / update.ps1     # Thin wrappers → scripts/update_external.py
```

### Source governance tiers

| Tier | Meaning | In main catalog? |
|------|---------|-----------------|
| `core` | Official/high-quality curated sources (anthropics, mattpocock, kepano) | Yes |
| `community` | Community-contributed sources (baoyu, taste-skill, axton) | Yes |
| `bulk` | High-volume, low-signal sources (awesome-claude-skills: 863 automation skills) | No — only in `docs/full-catalog.md` |
| `reference` | Non-skill reference libraries (awesome-design-md) | No |

## When adding a new skill

### Custom skill (`custom/`)

1. Create a leaf skill directory anywhere under `custom/` and put `SKILL.md` at that leaf
2. `custom/` can contain grouped paths, but keep single-purpose skills at the leaf path the user expects; nested families like `custom/x-reader/*` already exist
3. If the immediate job is to choose which skill from this repo should be loaded for real work, use `custom/skill-router` first; it should inspect this repo as the source of truth, not an installed mirror
4. **Run `python3 scripts/generate_skills_catalog.py`** — this auto-updates:
   - `SKILLS.md` curated index
   - `docs/full-catalog.md` full index
   - `README.md` auto-generated blocks (custom skills table + external sources table)
5. Run `python3 scripts/verify_structure.py`
6. Commit and push

### External skill (`external/`)

When adding a new external source, **update these files**:

1. **`config/sources.yaml`** — add to `skill_sources`:
   ```yaml
   - name: source-name
     repo: https://github.com/owner/repo.git
     branch: main
     subdir: skills          # or "." if skills are at root
     mode: flatten           # or "preserve" for duplicate leaf names
     tier: community         # or "core" / "bulk"
     include_in_main_catalog: true
   ```
2. **`external/<name>/`** — run `update.sh` (or `update.ps1`) to sync, or manually clone and copy
3. **`README.md`** — the external sources table is auto-generated; verify it looks correct after running `generate_skills_catalog.py`
4. **`SKILLS.md`** — auto-generated; verify curated inclusion
5. Run `python3 scripts/generate_skills_catalog.py` and `python3 scripts/verify_structure.py`

### External reference source (`external/`)

Use this for upstream repositories that are useful to agents but do not contain `SKILL.md` files.

When adding a new external reference source:

1. **`config/sources.yaml`** — add to `reference_sources`:
   ```yaml
   - name: awesome-design-md
     repo: https://github.com/VoltAgent/awesome-design-md.git
     branch: main
     subdir: design-md
     tier: reference
     include_in_main_catalog: false
   ```
2. **`external/<name>/`** — run `update.sh` to sync
3. **`README.md`** — the reference sources table is auto-generated
4. Run `python3 scripts/generate_skills_catalog.py` and `python3 scripts/verify_structure.py`

Reference-source rules:

- A directory under `external/` only counts as a skill source when the mirrored leaf directories contain `SKILL.md`
- Repositories like `awesome-design-md` may live under `external/` as reference libraries, but they must not be cataloged as skills
- If `SKILLS.md` exists, do not add reference-source directories to the skill index unless they later gain real `SKILL.md` files

## Gotchas

- **`config/sources.yaml` is the single source of truth**: `update.sh`, `update.ps1`, `generate_skills_catalog.py`, and `verify_structure.py` all read from this file. Never manually edit `update.sh` or `update.ps1` source lists — they are now thin wrappers.
- **`update.sh` / `update.ps1` are thin wrappers**: they delegate to `scripts/update_external.py`. The canonical sync logic lives in Python, not shell/PowerShell.
- **`README.md` tables are auto-generated**: custom skills table and external sources tables are wrapped in `<!-- BEGIN/END GENERATED ... -->` markers. Do not edit between markers manually.
- **`SKILLS.md` is curated**: only `tier: core` and `tier: community` sources appear in the main catalog. `tier: bulk` sources (like awesome-claude-skills) are hidden from the quick-reference but still available in `docs/full-catalog.md`.
- **`external/<name>/` structure varies by source**: some sources put skill dirs directly under the cloned root (subdir=`.`), others use a `skills/` subdirectory (subdir=`skills`). The `config/sources.yaml` `subdir` field controls this.
- **Duplicate leaf skill names need `preserve` mode**: sources like deep-research-skills contain repeated names under language/platform groups, so keep the relative source path instead of flattening.
- **Duplicate skill names are normal**: catalog external skills by path and source, not by `name` alone.

## Script details

| Script | Purpose | Key behavior |
|--------|---------|--------------|
| `update.sh` / `.ps1` | Thin wrapper | Delegates to `scripts/update_external.py` |
| `scripts/update_external.py` | Core sync logic | Reads `config/sources.yaml`, clones, copies, commits, pushes |
| `push.sh` / `.ps1` | Push local changes | `git add -A` + commit + push |
| `pull.sh` / `.ps1` | Hard reset to remote | `git reset --hard origin/main` (destructive — discards uncommitted work) |
| `scripts/generate_skills_catalog.py` | Generate indexes | Outputs `SKILLS.md` (curated) + `docs/full-catalog.md` (full) + updates `README.md` blocks |
| `scripts/verify_structure.py` | Governance gate | Validates `sources.yaml` consistency, catalog invariants, bulk isolation |

- Temp clone directory: `.tmp-skills/` (gitignored)
- `config/sources.yaml` is the single source of truth for all external source configuration

## Conventions

- Only branch: `main`
- Remote: `origin` → `git@github.com:OCDcreator/my-skills.git`
- Dependencies: Python 3 + PyYAML (for `scripts/update_external.py` and catalog generation)
- Every skill must contain a `SKILL.md` at its directory root
- Self-authored skills belong under `custom/`; do not add root-level skill directories
