# Module Documentation Workflow

> Audience: agents maintaining `docs/modules/` alongside source code.

## Rule

Do not let module documentation drift:

- Added source module -> add mapped module doc.
- Modified source module -> update mapped module doc in the same branch.
- Deleted source module -> delete mapped module doc.
- Renamed source module -> rename or replace mapped module doc.

The hard gate is:

```bash
node scripts/check-module-doc-coverage.mjs
node scripts/check-module-doc-diff.mjs --range origin/main...HEAD
```

## Incremental Sync

### 1. List affected docs

```bash
node scripts/list-module-doc-targets-from-diff.mjs --range origin/main...HEAD
```

### 2. Update only affected docs

For small changes, the same agent that changes code should update mapped docs.

For larger changes:

- Code agent owns source and tests.
- Doc-sync agent owns only listed docs.
- Reviewer checks source-doc consistency and parent indexes.

### 3. Check aggregate docs

Also inspect parent docs when:

- a source file is added, deleted, or renamed
- `index.ts` changes
- a module boundary or owner changes
- the source root or doc mapping changes

## Doc-Sync Prompt

```text
You are updating module documentation for this repository.

Changed source files:
- src/...

Required module docs:
- docs/modules/...

Rules:
- Read the changed source and direct dependencies before editing docs.
- Update only docs directly related to this diff.
- Do not invent behavior; describe current source truth.
- If a source module was deleted, delete its mapped doc.
- If a source module was added, create its mapped doc from docs/modules/_TEMPLATE.md.
- If parent index or README docs need updates, list or update them according to repo rules.
- Run:
  node scripts/check-module-doc-coverage.mjs
  node scripts/check-module-doc-diff.mjs --range <base>...HEAD

Final report:
- files changed
- commands run
- remaining uncertainties
```

## Reviewer Checklist

- [ ] Every changed source file has a mapped doc path touched in the diff.
- [ ] No source module is missing a doc.
- [ ] No mapped doc remains after its source was deleted.
- [ ] Renames update both source and doc paths.
- [ ] Parent `index.md` / `README.md` docs are current when module topology changed.
- [ ] Docs describe current source behavior, not intent or guesses.
