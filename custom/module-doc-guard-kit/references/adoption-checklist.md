# Module Doc Guard Adoption Checklist

Use this checklist before telling the user the kit is installed.

## Repo inspection

- [ ] Read applicable `AGENTS.md` / README instructions.
- [ ] Identified source roots and file extensions.
- [ ] Identified generated files, tests, declaration files, or vendored files to exclude.
- [ ] Identified existing validation commands and CI entrypoints.

## Configuration

- [ ] `module-docs.config.json` has one group per source root.
- [ ] `exactMappings` covers special entrypoints.
- [ ] `docIgnore` only ignores non-source docs.
- [ ] Monorepo package roots do not map two sources to the same doc path.

## Files

- [ ] `docs/modules/README.md` explains the mapping rules.
- [ ] `docs/modules/_TEMPLATE.md` is adapted to the project language and module types.
- [ ] `docs/modules/_WORKFLOW.md` includes branch diff commands for the repo's base branch.
- [ ] Guard scripts are present under `scripts/`.
- [ ] Agent instructions include the hard doc-sync rule.

## Hard gates

- [ ] Full coverage check passes.
- [ ] Diff check passes for the current branch or is documented with a correct base range.
- [ ] Package/CI/verify gate runs both checks.
- [ ] Failure output tells future agents exactly which docs to add, update, or delete.

## Handoff

- [ ] Final report lists changed files.
- [ ] Final report includes exact commands and results.
- [ ] If placeholder docs remain, final report lists the fill-in plan and warns that the hard gate enforces presence, not semantic accuracy.
