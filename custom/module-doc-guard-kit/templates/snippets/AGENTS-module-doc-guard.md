## Module Documentation Guard

- Source modules are mapped to `docs/modules/**` by `module-docs.config.json`.
- If a source module is added, add its mapped module doc.
- If a source module is changed, update its mapped module doc in the same branch.
- If a source module is deleted, delete its mapped module doc.
- If a source module is renamed, rename or replace its mapped module doc.
- Run `node scripts/check-module-doc-coverage.mjs` and `node scripts/check-module-doc-diff.mjs --range <base>...HEAD` before claiming documentation sync is complete.
- Use `node scripts/list-module-doc-targets-from-diff.mjs --range <base>...HEAD` to list required doc targets for a branch.
