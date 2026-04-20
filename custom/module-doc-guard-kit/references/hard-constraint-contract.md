# Module Doc Hard Constraint Contract

This contract turns module documentation from a convention into a validation gate.

## Required checks

Run both checks in every pre-merge gate:

```bash
node scripts/check-module-doc-coverage.mjs
node scripts/check-module-doc-diff.mjs --range origin/main...HEAD
```

Use the repo's real base branch when it is not `main`.

## Failure cases

### Module added without doc

Source:

```text
src/features/newFeature.ts
```

Expected doc:

```text
docs/modules/features/newFeature.md
```

If the doc does not exist, `check-module-doc-coverage.mjs` fails.

### Module deleted without doc deletion

Deleted source:

```text
src/features/oldFeature.ts
```

Lingering doc:

```text
docs/modules/features/oldFeature.md
```

If the mapped doc still exists, `check-module-doc-coverage.mjs` fails as an orphan.

### Module modified without doc update

Changed source:

```text
src/core/runtime.ts
```

Mapped doc:

```text
docs/modules/core/runtime.md
```

If the source path appears in the git diff but the mapped doc path does not, `check-module-doc-diff.mjs` fails.

### Module renamed without doc rename/update

Renamed source:

```text
src/core/OldName.ts -> src/core/NewName.ts
```

Expected doc movement:

```text
docs/modules/core/OldName.md -> docs/modules/core/NewName.md
```

The diff check expects both old and new mapped doc paths to be touched. The coverage check verifies the final tree has only the new mapped doc.

## Why two checks are necessary

- Coverage is about final tree shape.
- Diff is about this branch's accountability.

A stale doc from last month can pass a diff check if this branch never touches that source. A modified source can pass coverage if its old doc still exists. The hard gate needs both checks.

## Acceptable exceptions

Exceptions must be encoded in `module-docs.config.json`, not remembered by agents.

Use `docIgnore` for non-source docs such as:

- `README.md`
- `_TEMPLATE.md`
- `_WORKFLOW.md`
- `infrastructure/**/*.md`

Use `exactMappings` for special source files such as:

- `src/main.ts -> docs/modules/entry-point/main.md`

Do not hide real source modules with broad ignore patterns just to make validation pass.
