---
name: module-doc-guard-kit
description: Use when a repo needs per-module documentation under docs/modules, hard CI/local checks that fail on source-doc drift, or a reusable package so another agent can keep module docs synchronized when files are added, changed, renamed, or deleted. Trigger on 模块文档, module docs, docs/modules, doc coverage, documentation guard, stale docs, changed code without docs, or requests to port OpenCodian-style module documentation to another project.
---

# Module Doc Guard Kit

Use this skill to install a **repo-local module documentation guard** into a target repository. The output is a small, committed kit that future agents can run without remembering the policy:

- `module-docs.config.json`
- `docs/modules/` template and workflow docs
- `scripts/check-module-doc-coverage.mjs`
- `scripts/check-module-doc-diff.mjs`
- `scripts/list-module-doc-targets-from-diff.mjs`
- package/CI/agent-rule snippets adapted to the target repo

## When this skill wins

Use it when the user wants any of these:

- “把 OpenCodian 的模块文档机制同步到别的项目”
- “模块更新但文档没更新就失败”
- “新增/删除模块时对应 docs/modules 也必须同步”
- `docs/modules` one-to-one source mapping
- hard guardrails for documentation drift in CI, `npm run verify`, or another validation gate
- a reusable handoff package another model can apply in a different repo

Do **not** use this for general README polishing, API reference writing, or one-off documentation summaries that are not tied to source-file coverage.

## First pass

Inspect the target repo before copying anything:

1. Read applicable `AGENTS.md` / `CLAUDE.md` / README rules.
2. Find source roots: `src/`, `app/`, `packages/*/src/`, `lib/`, or language-specific roots.
3. Find existing docs and validation commands.
4. Decide whether this is a bootstrap or retrofit:
   - **Bootstrap**: no module-doc system exists yet.
   - **Retrofit**: docs exist, but coverage/diff gates are missing or stale.
5. Identify package/CI hooks. Prefer wiring into the existing verify gate if one exists.

Only ask the user if source roots or the target validation gate cannot be inferred safely.

## Hard guard contract

Install both checks together:

| Check | Catches |
|---|---|
| `check-module-doc-coverage.mjs` | source exists but doc missing; doc exists but source was deleted |
| `check-module-doc-diff.mjs` | source changed in this branch/diff but mapped doc was not touched |
| `list-module-doc-targets-from-diff.mjs` | non-failing helper for doc-sync workers |

Coverage alone cannot prove modified modules updated their docs. Diff alone cannot catch old orphan docs. Use both.

Detailed behavior is in `references/hard-constraint-contract.md`.

## Use the bundled templates

Copy from `templates/repo/` into the target repo, then adapt placeholders:

```text
templates/repo/
├── module-docs.config.json
├── docs/
│   ├── README.md
│   └── modules/
│       ├── README.md
│       ├── _TEMPLATE.md
│       └── _WORKFLOW.md
└── scripts/
    ├── module-doc-guard-lib.mjs
    ├── check-module-doc-coverage.mjs
    ├── check-module-doc-diff.mjs
    └── list-module-doc-targets-from-diff.mjs
```

Then apply snippets from `templates/snippets/`:

- `AGENTS-module-doc-guard.md`
- `package-json-scripts.jsonc`
- `github-actions-module-docs.yml`

Do not blindly overwrite existing docs. Merge the template into the repo's current documentation structure when it already has one.

## Configuration rules

Default TypeScript mapping:

```text
src/main.ts -> docs/modules/entry-point/main.md
src/**/foo.ts -> docs/modules/**/foo.md
```

Adapt `module-docs.config.json` for other roots. For monorepos, add one config group per package/source root. Keep generated docs predictable: one source file should map to exactly one module doc.

## Agent workflow

### Bootstrap

1. Install templates.
2. Generate placeholder docs for every current source module, or explicitly plan the fill-in batches.
3. Run coverage check and fix all missing/orphan reports.
4. Wire the check scripts into package/CI/verify.
5. Update repo instructions so future agents know the gate is mandatory.

### Incremental code changes

1. Run `node scripts/list-module-doc-targets-from-diff.mjs --range <base>...HEAD`.
2. Update only the listed module docs plus required parent indexes.
3. Run coverage and diff checks.
4. Run the repo's normal validation gate.

### Reviewer pass

Check only:

- Each changed source file has its mapped doc touched.
- New source files have new docs.
- Deleted source files have deleted docs.
- Docs state the current code behavior, not guesses.
- Parent `index.md` / `README.md` updates are present when module topology changed.

## Expected final report

When finished, report:

- Source roots and mapping rules installed.
- Scripts added and how they are wired into validation.
- Whether current coverage is clean.
- Which docs were generated or left as placeholders.
- Which commands were run and their results.
- Any target repo assumptions another model must preserve.

Use `references/adoption-checklist.md` for the final self-check.
