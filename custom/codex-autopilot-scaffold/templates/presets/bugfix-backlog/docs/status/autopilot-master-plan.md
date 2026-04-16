# Autopilot Master Plan

> **Status**: [ACTIVE]
> **Preset**: `[[PRESET_LABEL]]`
> **Repository**: `[[REPO_NAME]]`

## Overall objective

- [[OBJECTIVE]]
- Keep each queued slice small, reproducible, and easy to validate
- Prefer the highest-confidence bugfix or backlog item first

## Priority lanes

- **P1. Reproducible bugfixes**: issues with a clear failing test, error, or broken behavior
- **P2. Bounded backlog**: queued improvements with explicit acceptance criteria
- **P3. Checkpointing**: record what landed and whether unattended continuation still makes sense

## Guardrails

- Follow the first `[NEXT]` queue item in `docs/status/autopilot-round-roadmap.md`
- Do not expand scope beyond the queued issue
- Do not extend the queue automatically beyond the preset checkpoint
