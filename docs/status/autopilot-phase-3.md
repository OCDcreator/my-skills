# Autopilot Phase 3: B3 Rich Generic Assertions And Performance Budgets

> **Status**: [DONE]
> **Attempt**: 3
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B3 - Rich generic assertions and performance budgets`.
- Kept work inside the generic `custom/obsidian-plugin-autodebug` framework and its roadmap docs.
- Extended `obsidian_debug_analyze.mjs` with declarative generic assertions for selector counts, visibility, DOM/log text regex, DOM attributes, computed styles, grouped log rules, and timing/performance budgets.
- Preserved declarative assertion severities by emitting blocking `fail` plus non-blocking `warn`, `expected`, and `flaky` statuses, and added machine-readable `assertionSummary` data to diagnosis output.
- Updated the HTML report to summarize rich assertion outcomes, severity classes, grouped log rule details, and count summaries.
- Expanded the generic assertion template and added a plugin-neutral synthetic rich-assertion fixture for validation and downstream reuse.
- Extended CDP UI capture summaries with computed-style match metadata so style assertions can consume machine-readable selector captures.
- Kept baseline/comparison helpers severity-aware for the new assertion statuses.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/assertions/plugin-view-health.template.json`
- `custom/obsidian-plugin-autodebug/assertions/synthetic-plugin-rich-health.fixture.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_cdp_capture_ui.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-3.md`

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_cdp_capture_ui.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs` — passed.
- `node -e "const fs=require('fs'); for (const p of ['custom/obsidian-plugin-autodebug/assertions/plugin-view-health.template.json','custom/obsidian-plugin-autodebug/assertions/synthetic-plugin-rich-health.fixture.json']) JSON.parse(fs.readFileSync(p,'utf8')); console.log('assertion JSON ok');"` — passed.
- Synthetic artifacts were generated under `.tmp-skills/autopilot-b3/` to validate rich assertion behavior without a real plugin.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_analyze.mjs --summary .tmp-skills/autopilot-b3/summary.json --assertions custom/obsidian-plugin-autodebug/assertions/synthetic-plugin-rich-health.fixture.json --output .tmp-skills/autopilot-b3/diagnosis.json` — passed; emitted `fail`, `warn`, `expected`, and `flaky` custom assertion statuses plus `assertionSummary`.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_report.mjs --diagnosis .tmp-skills/autopilot-b3/diagnosis.json --output .tmp-skills/autopilot-b3/report.html` — passed; rendered grouped log rules and assertion summary counts.
- `node -e "const fs=require('fs'); const diagnosis=JSON.parse(fs.readFileSync('.tmp-skills/autopilot-b3/diagnosis.json','utf8')); if (diagnosis.status !== 'fail') throw new Error('expected fail diagnosis'); const byId=Object.fromEntries(diagnosis.customAssertions.map((entry) => [entry.id, entry])); if (byId['plugin-status-text']?.status !== 'fail') throw new Error('missing fail severity'); if (byId['plugin-ready-attribute']?.status !== 'warn') throw new Error('missing warn severity'); if (byId['cold-start-empty-state']?.status !== 'expected') throw new Error('missing expected severity'); if (byId['server-ready-budget']?.status !== 'flaky') throw new Error('missing flaky severity'); if (diagnosis.assertionSummary?.blockingFailures?.[0] !== 'plugin-status-text') throw new Error('blocking summary missing'); if ((diagnosis.assertionSummary?.warnings ?? []).length !== 2) throw new Error('warning summary missing'); if ((diagnosis.assertionSummary?.expected ?? []).length !== 1) throw new Error('expected summary missing'); if ((diagnosis.assertionSummary?.flaky ?? []).length !== 1) throw new Error('flaky summary missing'); const group = byId['grouped-log-health']; if (!group?.rules || group.rules.length !== 2) throw new Error('grouped log rules missing'); console.log('diagnosis rich assertions ok');"` — passed.
- `node -e "const fs=require('fs'); const html=fs.readFileSync('.tmp-skills/autopilot-b3/report.html','utf8'); for (const needle of ['Blocking:', 'Grouped log rules', 'warn', 'expected', 'flaky']) { if (!html.includes(needle)) throw new Error('report missing '+needle); } console.log('report summary ok');"` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_compare.mjs --baseline .tmp-skills/autopilot-b3/diagnosis.json --candidate .tmp-skills/autopilot-b3/diagnosis.json --output .tmp-skills/autopilot-b3/comparison.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode save --baseline-root .tmp-skills/autopilot-b3/baselines --name rich-assertions --diagnosis .tmp-skills/autopilot-b3/diagnosis.json --report .tmp-skills/autopilot-b3/report.html --comparison .tmp-skills/autopilot-b3/comparison.json` — passed.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_baseline.mjs --mode compare --baseline-root .tmp-skills/autopilot-b3/baselines --name rich-assertions --candidate-diagnosis .tmp-skills/autopilot-b3/diagnosis.json --output .tmp-skills/autopilot-b3/baseline-compare.json` — passed.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- Continue with `B4 - Baseline taxonomy, regression comparison, and retention`.
