# Autopilot Master Plan

> **Status**: [ACTIVE]
> **Preset**: `[[PRESET_LABEL]]`
> **Repository**: `[[REPO_NAME]]`

## Overall objective

- [[OBJECTIVE]]
- Recover configured gates before expanding into broader refactors
- Keep queue items small and validation-focused

## Priority lanes

- **P1. Gate recovery**: restore failing or noisy validation commands to a stable baseline
- **P2. Justified cleanup**: reduce remaining warnings or brittle edges only when directly related to P1
- **P3. Checkpointing**: document what changed and whether unattended continuation is still worth it

## Guardrails

- Follow the first `[NEXT]` queue item in `docs/status/autopilot-round-roadmap.md`
- Do not turn warning cleanup into a general rewrite
- Do not expand the queue automatically beyond the preset checkpoint
