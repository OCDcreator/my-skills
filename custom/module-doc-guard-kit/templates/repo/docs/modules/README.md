# Module Documentation

> Source modules must have matching docs under `docs/modules/`. The guard scripts fail when this mapping drifts.

## Coverage Rules

Default mapping:

- `src/main.ts` -> `docs/modules/entry-point/main.md`
- Other `src/**/foo.ts` -> `docs/modules/**/foo.md`
- `index.ts` barrel files need docs because they define the public aggregation surface.
- Type, constant, locale, adapter, and experimental modules still need docs when they are part of tracked source.

Adapt the exact source roots, extensions, excludes, and special cases in `module-docs.config.json`.

## Non-Source Docs

These docs support the documentation system and are intentionally ignored by source coverage:

- `docs/modules/README.md`
- `docs/modules/_TEMPLATE.md`
- `docs/modules/_WORKFLOW.md`
- `docs/modules/infrastructure/**/*.md`

Keep any other exceptions encoded in `module-docs.config.json`.

## Required Checks

Run both checks before merge:

```bash
node scripts/check-module-doc-coverage.mjs
node scripts/check-module-doc-diff.mjs --range origin/main...HEAD
```

Use the actual base branch for the repo.

## Writing Conventions

Each mapped document should follow `_TEMPLATE.md`, adapted to the module type:

- Service/controller/runtime modules: responsibilities, state, methods, data flow, interactions.
- Types/constants: exported semantics, constraints, consumers.
- `index.ts` barrel modules: aggregation surface and public API.
- Locale/content modules: key space, consumers, sync requirements.
- Experimental/demo modules: entrypoint, isolation, cleanup path, risk.

Do not invent runtime behavior to fill the template. Write “None” or “Not applicable” when a section does not fit.
