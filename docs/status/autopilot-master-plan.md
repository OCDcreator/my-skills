# Autopilot Master Plan

> **Status**: [ACTIVE]
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`

## Overall objective

- Queue and execute Windows + macOS dual-platform generic `custom/obsidian-plugin-autodebug` framework enhancement slices beyond B10: package-manager/runtime doctor coverage, optional Playwright and `obsidian-testing-framework` adapters, Hot Reload coordination checks, sample-plugin scaffold/bootstrap flows, and CI-ready quality-gate templates without hard-coding one plugin.
- Keep each queued slice small, reproducible, and easy to validate
- Prefer the highest-confidence bugfix or backlog item first

## Priority lanes

- **P1. Environment and runtime doctoring**: Node/Corepack/package-manager detection, runtime prerequisites, Hot Reload coordination, and optional tool-adapter discovery that work on Windows PowerShell and macOS/Linux Bash without assuming one plugin
- **P2. UI automation and testing adapters**: optional Playwright and `obsidian-testing-framework` integration, richer scenario execution, and trace/screenshot evidence with plugin-neutral defaults
- **P3. Generic scaffolding and delivery**: sample-plugin scaffold/bootstrap, CI-ready quality-gate templates, and checkpointed dual-platform validation for future agents

## Guardrails

- Follow the first `[NEXT]` queue item in `docs/status/autopilot-round-roadmap.md`
- Keep each round inside the generic `custom/obsidian-plugin-autodebug` framework backlog
- Preserve plugin-agnostic behavior; real plugin names may appear only as validation fixtures or examples
- Do not modify existing skill files unless the active queue item explicitly requires it
- Do not expand beyond the approved B11-B15 queue without another human approval
