# Module Doc Guard Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package OpenCodian's module-doc discipline as a reusable skill that installs hard documentation-sync guardrails into other repositories.

**Architecture:** The skill lives under `custom/module-doc-guard-kit/` and ships repo-ready templates plus deterministic Node guard scripts. The target repo gets a config-driven one-to-one source-to-doc coverage check and a git-diff check that fails when changed modules are not accompanied by matching module docs.

**Tech Stack:** Codex skill Markdown, repo templates, dependency-free Node `.mjs` scripts, `git diff --name-status`.

---

### Task 1: Skill Contract

**Files:**
- Create: `custom/module-doc-guard-kit/SKILL.md`
- Create: `custom/module-doc-guard-kit/references/hard-constraint-contract.md`
- Create: `custom/module-doc-guard-kit/references/adoption-checklist.md`

- [ ] Define trigger wording for module-doc drift, `docs/modules`, and hard doc gates.
- [ ] Document first-pass repo inspection, adoption modes, output boundary, and validation expectations.
- [ ] Keep the main skill concise and route detailed contract/checklist content into references.

### Task 2: Repo Templates

**Files:**
- Create: `custom/module-doc-guard-kit/templates/repo/module-docs.config.json`
- Create: `custom/module-doc-guard-kit/templates/repo/docs/README.md`
- Create: `custom/module-doc-guard-kit/templates/repo/docs/modules/README.md`
- Create: `custom/module-doc-guard-kit/templates/repo/docs/modules/_TEMPLATE.md`
- Create: `custom/module-doc-guard-kit/templates/repo/docs/modules/_WORKFLOW.md`
- Create: `custom/module-doc-guard-kit/templates/snippets/AGENTS-module-doc-guard.md`
- Create: `custom/module-doc-guard-kit/templates/snippets/package-json-scripts.jsonc`
- Create: `custom/module-doc-guard-kit/templates/snippets/github-actions-module-docs.yml`

- [ ] Provide a TypeScript-first default mapping that can be adapted for other source roots.
- [ ] Include a clear model handoff workflow and prompt blocks.
- [ ] Include snippets for repo instructions, `package.json`, and GitHub Actions.

### Task 3: Guard Scripts

**Files:**
- Create: `custom/module-doc-guard-kit/templates/repo/scripts/module-doc-guard-lib.mjs`
- Create: `custom/module-doc-guard-kit/templates/repo/scripts/check-module-doc-coverage.mjs`
- Create: `custom/module-doc-guard-kit/templates/repo/scripts/check-module-doc-diff.mjs`
- Create: `custom/module-doc-guard-kit/templates/repo/scripts/list-module-doc-targets-from-diff.mjs`

- [ ] Implement full coverage check for missing docs and orphan docs.
- [ ] Implement diff check requiring touched docs for touched source modules.
- [ ] Implement target listing for doc-sync workers and reviewer handoff.

### Task 4: Catalog And Evals

**Files:**
- Modify: `README.md`
- Create: `custom/module-doc-guard-kit/evals/evals.json`

- [ ] Add the new custom skill to the README directory tree and table.
- [ ] Add realistic eval prompts for bootstrap, retrofit, and stale-doc failure cases.

### Task 5: Validation

**Files:**
- No committed test fixture required.

- [ ] Run a disposable repo smoke test for coverage success and failure.
- [ ] Run a disposable repo smoke test for diff success and failure.
- [ ] Check `git status --short` and report changed files.
