---
name: skill-catalog-maintainer
description: Use when working in a skills repository and the user asks to understand, catalog, compare, audit, add, remove, maintain, discover, or recommend AI agent skills for a project or task. Also use when creating or updating SKILLS.md, README skill tables, AGENTS.md maintenance rules, or when another project needs matching skill recommendations with source and install hints.
---

# Skill Catalog Maintainer

## Overview

Keep a skills repository understandable. Build and maintain a concise catalog that answers: what does each skill do, when should it trigger, where did it come from, and which related skills overlap.

## Use This For

- Explaining what skills in this repo are for
- Finding which skills fit a specific development request or project need
- Creating or updating `SKILLS.md`
- Adding, removing, renaming, or reorganizing skills
- Auditing duplicate or overlapping skill names across sources
- Updating `README.md` and `AGENTS.md` after skill changes

## Inventory Workflow

1. Read `README.md`, `AGENTS.md`, `update.sh`, and `update.bat` first.
2. Find skills with `custom/**/SKILL.md` and `external/**/SKILL.md`; do not assume either tree is flat.
3. For each `SKILL.md`, extract frontmatter `name` and `description` before reading the full body.
4. Preserve both path and source because different external sources may contain skills with the same `name`.
5. Classify by practical use case, not by repository source alone.
6. Resolve install source information: for `custom/`, use this repository as the source; for `external/`, map the source prefix through `update.sh` `SOURCES` and `README.md`.

## Discovery Workflow

Use this when the user is not asking to maintain the catalog itself, but is using this skill to discover which other skills should be loaded for real work.

1. Translate the user's request into a concrete job to be done, such as `frontend polish`, `bug diagnosis`, `provider config`, or `Obsidian automation`.
2. Match that job against skill frontmatter `name`, `description`, and category; prefer skills whose trigger conditions directly match the task.
3. Recommend both the primary implementation skill and any required process skill that should be loaded first.
4. When multiple skills fit, give a short ordered recommendation with why each one applies and how they combine.
5. If the user referenced this skill by path while asking for development help, treat that as a discovery request unless they explicitly ask for catalog maintenance only.
6. If no direct match exists, return the closest skills and clearly say what gap remains.

Prefer recommendations in this order:

- Required process skills first, such as `brainstorming`, `systematic-debugging`, or `test-driven-development`
- Primary domain skill second, such as `frontend-design`, `pdf`, or `obsidian-cli`
- Supporting follow-up skills last, only when they add clear value

For a discovery request, the answer should usually be a compact table like this:

```markdown
| Priority | Skill | Why it matches | Local path | Next action |
```

After recommending skills, explicitly tell the agent which skill to load next instead of stopping at catalog analysis.

## Catalog Shape

Use this structure for `SKILLS.md` unless the user asks for something else:

```markdown
# Skills Catalog

## Quick Picker
| Need | Recommended skill(s) | Notes |

## Common Combinations
| Workflow | Skill combination | Why |

## Custom Skills
| Path | Name | Use when |

## External Skills
| Source | Notable skills | Use when |

## Full Index
| Path | Name | Category | Use when | Source repo | Source subdir | Install hint |
```

Keep descriptions short. Prefer the skill's own `description` field, then compress it into plain language. If the purpose is unclear after reading the skill, mark it as `Needs review` instead of guessing.

## Project Recommendation Output

When recommending skills for another project, include enough source data for another agent to install them without guessing:

| Field | Meaning |
|-------|---------|
| Skill | Frontmatter `name` and human-readable label |
| Why | Why this project needs it |
| Local path | Current path in this repo |
| Source repo | Git repository to clone or fetch from |
| Source branch | Branch from `update.sh` for external sources; `main` for this repo unless verified otherwise |
| Source subdir | Exact upstream path to copy, usually `<source-subdir>/<skill-dir>` |
| Install hint | One-line clone/copy instruction that names the target agent directories |

Prefer this compact recommendation table:

```markdown
| Skill | Why | Source repo | Source branch | Source subdir | Local path | Install hint |
```

For `custom/*` skills, use this repo as the source repo and the custom path as the source subdir. For `external/*` skills, derive the repo, branch, and base subdir from `update.sh` `SOURCES`; append the local skill directory name to that base subdir. If the source cannot be verified, write `Needs source review` rather than inventing a URL.

## Target Project Installation

When the user wants another agent or another machine to install recommended skills into a project, give tool-specific target paths. Prefer copying the same selected skill directories into both `.claude/skills/` and `.agents/skills/` for broad compatibility.

| Target agent | Project-level skill path | Notes |
|--------------|--------------------------|-------|
| Claude Code | `.claude/skills/<skill-name>/SKILL.md` | Project-only skills. If the project uses `AGENTS.md`, create `CLAUDE.md` containing `@AGENTS.md` so Claude Code reads the same project guidance. |
| OpenCode | `.opencode/skills/<skill-name>/SKILL.md` | Native OpenCode path. OpenCode also discovers `.claude/skills/` and `.agents/skills/`, so those are usually enough for shared setups. |
| Codex CLI | `.agents/skills/<skill-name>/SKILL.md` | Cross-agent repo skills path; also useful when the project should work across Codex and OpenCode. |

Use this installation plan unless the user specifies one tool only:

1. Clone the source repo to a temp directory.
2. Copy each selected `Source subdir` to `<project>/.claude/skills/<skill-dir>/` and `<project>/.agents/skills/<skill-dir>/`.
3. If the user specifically targets OpenCode, also copy to `<project>/.opencode/skills/<skill-dir>/` or note that OpenCode can read the shared `.claude`/`.agents` paths.
4. Update target `AGENTS.md` with the selected skills, trigger scenarios, and the chosen project skill directories.
5. For Claude Code projects, create or update `CLAUDE.md` with `@AGENTS.md` unless the project already has equivalent Claude instructions.

Example install hint:

```text
git clone --depth 1 -b <branch> <source-repo> <tmp>; copy <tmp>/<source-subdir> to <project>/.claude/skills/<skill-dir>/ and <project>/.agents/skills/<skill-dir>/
```

## Categories

Start with these categories and add only when needed:

| Category | Use for |
|----------|---------|
| Frontend/UI | Web pages, components, visual design, UI review |
| Documents | PDF, DOCX, PPTX, XLSX, Markdown conversion |
| Obsidian | Vault notes, Bases, Canvas, CLI, markdown workflows |
| Media | Video, audio, transcript, image, visual generation |
| Web/Research | Search, URL extraction, content research |
| Automation/Agents | MCP, plugins, hooks, agents, skill creation |
| Content/Publishing | Translation, social posts, slides, articles |
| DevOps/Config | Deployment, provider config, local services |

## Maintenance Rules

When adding or removing a skill, update all relevant files in the same change:

| Change | Required updates |
|--------|------------------|
| Custom skill | `custom/<path>/SKILL.md`, `README.md` tree/table, `SKILLS.md` |
| External source | `external/<source>/`, `update.sh`, `update.bat`, `README.md`, `SKILLS.md` with source repo/subdir info |
| Skill rename/move | Any links in `README.md`, `SKILLS.md`, and `AGENTS.md` that mention the old path |
| Workflow rule change | `AGENTS.md` |

## Gotchas

- `custom/` can contain nested skill families such as `custom/x-reader/video`; treat leaf directories containing `SKILL.md` as skills.
- External sources can duplicate skill names; catalog by `path + name`, not name alone.
- Recommendation output must include a clone/copy source. A local path alone is not enough for project-specific installation.
- Project install guidance should name agent-specific directories. Do not say only "copy to the project" without specifying `.claude/skills`, `.agents/skills`, or `.opencode/skills`.
- `update.sh` auto-discovers skill dirs under each source's configured subdir; `update.bat` mirrors this manually.
- `update.sh` has `EXCLUDE_NAMES`; `update.bat` may not have equivalent filtering. Document this asymmetry when it affects catalog completeness.
- Do not list every upstream README or asset as a skill. A skill is a directory containing `SKILL.md`.

## Verification

Before saying the catalog is current:

1. Count current `SKILL.md` files in `custom/` and `external/`.
2. Check that new/removed skill paths are reflected in `README.md` and `SKILLS.md`.
3. For external source changes, verify `update.sh` and `update.bat` both mention the source and that `.bat` counters are consistent.
4. Run `git diff --name-status` to confirm only intended catalog, docs, script, and skill files changed.

## Output Style

- Lead with the user-facing answer: what to use and why.
- Keep catalog entries one line each unless a skill has non-obvious overlap or prerequisites.
- Flag uncertain or duplicate skills explicitly.
- Do not rewrite unrelated skill content while cataloging.
