# Project Docs Guide

`docs/` is organized by purpose. Keep source-adjacent documentation under `docs/modules/` so code changes and module docs can be validated together.

## Start Here

- `modules/README.md`
  - Module documentation index and source-to-doc coverage rules.
- `modules/_WORKFLOW.md`
  - Incremental update workflow for agents and reviewers.
- `modules/_TEMPLATE.md`
  - Standard template for one module document.

## Directory Rules

- Source-adjacent docs live in `docs/modules/`.
- Status, requirements, architecture, and external references may live in sibling folders if the repo uses them.
- Do not add one-off module notes outside `docs/modules/`; they will bypass the guardrail.
