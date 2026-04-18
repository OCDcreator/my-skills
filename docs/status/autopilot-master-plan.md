# Autopilot Master Plan

> **Status**: [ACTIVE]
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`

## Overall objective

- Queue and execute Windows + macOS dual-platform generic custom/obsidian-plugin-autodebug framework enhancement slices: config-driven job specs, platform-neutral command adapters, generic view-open and selector discovery, richer assertions, baseline classification, screenshot diff, doctor/report/playbook automation, and cross-platform validation without hard-coding one plugin.
- Keep each queued slice small, reproducible, and easy to validate
- Prefer the highest-confidence bugfix or backlog item first

## Priority lanes

- **P1. Generic orchestration**: job specs, shell-safe command adapters, watch loops, and deploy/reload/log phases that work on Windows PowerShell and macOS/Linux Bash without assuming one plugin
- **P2. Generic diagnosis**: view-open strategy chains, selector discovery, richer assertions, baseline classification, screenshot diff, and reports
- **P3. Safe automation**: executable playbooks, doctor/fix helpers, clean-state matrices, Windows + macOS smoke tests, and checkpointed handoffs

## Guardrails

- Follow the first `[NEXT]` queue item in `docs/status/autopilot-round-roadmap.md`
- Keep each round inside the generic `custom/obsidian-plugin-autodebug` framework backlog
- Preserve plugin-agnostic behavior; real plugin names may appear only as validation fixtures or examples
- Do not modify existing skill files unless the active queue item explicitly requires it
