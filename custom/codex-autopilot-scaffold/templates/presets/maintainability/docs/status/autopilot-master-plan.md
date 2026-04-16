# Autopilot Master Plan

> **Status**: [ACTIVE]
> **Preset**: `[[PRESET_LABEL]]`
> **Repository**: `[[REPO_NAME]]`

## Overall objective

- [[OBJECTIVE]]
- Prefer queue-driven ownership reduction over free-form cleanup
- Keep configured validation commands green after every successful round

## Priority lanes

- **P1. Thick-owner reduction**: shrink modules or entrypoints that still concentrate too much ownership
- **P2. Validation friction**: clean up validation-heavy hotspots only when they unblock or stabilize P1 work
- **P3. Boundary hygiene**: keep docs, queue, and validation instructions aligned with the current architecture

## Guardrails

- Follow the first `[NEXT]` item in `docs/status/autopilot-round-roadmap.md`
- Do not expand the queue automatically beyond the preset checkpoint item
- Do not create new thin wrappers unless they isolate a genuinely reused or risky dependency
- Do not change product behavior while chasing maintainability wins
