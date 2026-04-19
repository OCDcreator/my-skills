# Autopilot Master Plan

> **Status**: [ACTIVE]
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`

## Overall objective

- Queue and execute the remaining approved Windows + macOS generic `custom/obsidian-plugin-autodebug` ecosystem slices beyond B16: persistent vault log ingestion, official lint/plugin-entry preflight validation, and repo-owned Obsidian E2E adapter fixtures plus CI wiring without hard-coding one plugin.
- Keep each queued slice small, reproducible, and easy to validate
- Prefer the highest-confidence bugfix or backlog item first

## Priority lanes

- **P1. Persistent log capture and diagnosis**: vault-level structured logging discovery, NDJSON ingestion, and merged console/CDP plus file-log evidence with plugin-neutral defaults
- **P2. Preflight validation gates**: official lint/plugin-entry checks that surface manifest and template issues before build/deploy while respecting repository-owned scripts
- **P3. Repo-owned Obsidian E2E adapters**: optional `obsidian-e2e`, `obsidian-testing-framework`, and `wdio-obsidian-service` fixture plus CI wiring that preserves the existing CLI/CDP-first path

## Guardrails

- Follow the first `[NEXT]` queue item in `docs/status/autopilot-round-roadmap.md`
- Keep each round inside the generic `custom/obsidian-plugin-autodebug` framework backlog
- Preserve plugin-agnostic behavior; real plugin names may appear only as validation fixtures or examples
- Do not modify existing skill files unless the active queue item explicitly requires it
- Do not expand beyond the approved B17-B19 queue without another human approval
