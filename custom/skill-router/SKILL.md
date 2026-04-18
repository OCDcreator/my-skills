---
name: skill-router
description: Use when the immediate job is to decide which skills should be loaded from the `my-skills` repository before doing real work, especially if the user asks for skill recommendations, says to search their skill repo, references `my-skills`, or invokes a path-based skill prompt to bootstrap another task.
---

# Skill Router

Route real work to the right skills from the source-of-truth `my-skills` repository. This skill is for discovery and routing, not for maintaining the catalog itself.

## Hard Rule

Do not recommend skills from memory or from the currently installed skill list alone.

First inspect the source-of-truth `my-skills` repository, then recommend the next skill to load.

## Source Of Truth

Resolve the skills repository in this order:

1. Local source repo: `C:\Users\lt\Desktop\Write\custom-project\my-skills`
2. Git remote for the source repo: `git@github.com:OCDcreator/my-skills.git`
3. HTTPS fallback: `https://github.com/OCDcreator/my-skills.git`

If the local repo exists, prefer it over installed copies such as `~/.codex/skills`, `~/.claude/skills`, `.agents/skills`, or mirrored repos like `skills-manager`.

## Use This For

- Figuring out which skill should be loaded next for a concrete user task
- Searching `my-skills` before implementation starts
- Recommending custom or external skills from this repository for another project
- Routing maintenance work to `skill-catalog-maintainer`
- Routing style-seeking UI work to `design-reference-router`

Do not use this skill to edit `README.md`, `AGENTS.md`, `SKILLS.md`, or update source mirrors. That is `skill-catalog-maintainer`.

## Discovery Workflow

1. Resolve the source-of-truth repo path or remote
2. Read `README.md` and `AGENTS.md` there first
3. Find skills with `custom/**/SKILL.md` and `external/**/SKILL.md`; treat leaf dirs containing `SKILL.md` as skills
4. Extract frontmatter `name` and `description` before reading full skill bodies
5. Translate the user request into a concrete job to be done
6. Match the job against the discovered skills; prefer direct trigger matches
7. Prefer `custom/` skills over `external/` skills when both fit equally well
8. Return a short ordered recommendation and explicitly say which skill to load next

Never stop at “here are some possible skills.” The output must end with the next skill to load.

## Matching Rules

- Prefer skills whose trigger conditions directly mention the user’s task, tools, or symptoms
- Prefer narrower skills over broad generic ones
- When the task is repository maintenance, route to `skill-catalog-maintainer`
- When the task is discovery-only, do not drift into implementation advice
- If no direct match exists, return the closest skills and clearly state the gap

## Output Format

Use a compact table:

```markdown
| Priority | Skill | Why it matches | Source path | Next action |
```

After the table, add one explicit line:

```markdown
Load next: `<skill-name>`
```

## Recommendation Rules

- Include the source-of-truth repo path in `Source path`, not only an installed copy path
- If a process skill should be loaded before the domain skill, put it first
- Only recommend supporting follow-up skills when they add clear value
- Keep each reason to one short sentence

## Common Routes

| Task shape | Route to |
|---|---|
| Skill repo cataloging, README/AGENTS/SKILLS maintenance | `skill-catalog-maintainer` |
| Real-brand UI style selection before implementation | `design-reference-router` |
| Obsidian plugin automated debug/dev loop | `obsidian-plugin-autodebug` |
| Obsidian plugin logging and diagnostics | `obsidian-plugin-debug-logging` |
| Obsidian plugin release/version workflow | `obsidian-plugin-release-manager` |
| OpenCode unattended coding loop | `opencode-loop` |
| OpenCode provider/model config | `opencode-provider-config` |
| Search the live web | `searxng` |
| Fork/upstream sync workflow | `fork-upstream-workflow` |

## Common Mistakes

- Recommending from the currently installed skill list without checking `my-skills`
- Treating `skills-manager` as the source-of-truth repo
- Calling `skill-catalog-maintainer` for general task routing
- Returning a list of skills without naming the next one to load
- Omitting the repo path, which makes installation or follow-up ambiguous
