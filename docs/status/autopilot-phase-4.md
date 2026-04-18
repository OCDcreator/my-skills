# Autopilot Phase 4: B4 Baseline Taxonomy, Regression Comparison, And Retention

> **Status**: [DONE]
> **Attempt**: 4
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B4 - Baseline taxonomy, regression comparison, and retention`.
- Kept work inside the generic `custom/obsidian-plugin-autodebug` baseline workflow and status docs.
- Extended `obsidian_debug_baseline.mjs` so save/list/compare flows understand taxonomy tags for platform, vault state, cold/warm mode, scenario, plugin id, and run label.
- Added closest-match baseline selection for tag-driven comparisons while preserving direct `--name` selection and legacy baseline directories that only contain `diagnosis.json`.
- Added retention pruning with recent-age, keep-recent, and keep-per-taxonomy protections plus explicit delete mode for stale baseline artifacts.
- Updated the skill documentation to show tagged save/list/compare commands and dry-run retention pruning.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-4.md`

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs` — passed.
- Synthetic artifacts were generated under `.tmp-skills/autopilot-b4/` to validate tag-aware save/list/compare flows and retention without a real plugin.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode save ...` — passed for Windows warm, Windows cold, macOS warm, and stale Windows warm taxonomy variants.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode list --baseline-root .tmp-skills/autopilot-b4/baselines --tags "pluginId=sample-plugin|platform=windows|mode=warm"` — passed; returned the expected tagged warm Windows baselines.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode compare --baseline-root .tmp-skills/autopilot-b4/baselines --tags "pluginId=sample-plugin|platform=windows|mode=warm|scenario=open-plugin-view" --candidate-diagnosis .tmp-skills/autopilot-b4/candidate.json --output .tmp-skills/autopilot-b4/baseline-compare.json` — passed; selected the closest matching warm Windows baseline and recorded selection metadata.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode compare --baseline-root .tmp-skills/autopilot-b4/baselines --name legacy-only --candidate-diagnosis .tmp-skills/autopilot-b4/candidate.json --output .tmp-skills/autopilot-b4/legacy-compare.json` — passed; confirmed legacy name-based comparisons still work for baseline folders without `baseline.json`.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode prune --baseline-root .tmp-skills/autopilot-b4/baselines --tags "pluginId=sample-plugin|platform=windows|mode=warm|scenario=open-plugin-view" --max-age-days 30 --keep-recent 1 --keep-per-class 1 --delete true` — passed; removed only the stale warm Windows baseline and preserved the current baseline.
- A final `node -e` assertion script over `.tmp-skills/autopilot-b4` — passed; verified tagged list count, selected baseline name, legacy compare behavior, and retention removal results.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- Continue with `B5 - Screenshot diff and report artifact previews`.
