# Autopilot Phase 1: B18 Preflight Lint And Plugin-Entry Validation Gates

> **Status**: [DONE]
> **Attempt**: 1
> **Preset**: Bugfix / backlog
> **Lane**: `b1-backlog-slice`
> **Repository**: `my-skills`
> **Date**: 2026-04-19

## Scope

- Executed the queued B18 slice only: promoted repo-owned lint and plugin-entry validation into reusable preflight metadata that doctor/runtime reporting and generated CI templates can share.
- Fixed plugin-entry script detection so ReviewBot-style `validate:plugin-entry` commands are actually discovered, surfaced with runnable command previews plus remediation hints, and emitted into generated CI templates before build/test steps.
- Added a portable `preflight-smoke-plugin` fixture plus docs updates so manifest/template-residue failures can be demonstrated and validated pre-build without hard-coding one plugin repo or machine-local path.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/README.md`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/dist/main.js`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/dist/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/dist/styles.css`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/package.json`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/reviewbot-plugin-entry.json`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/scripts/check-manifest-residue.mjs`
- `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/scripts/validate-plugin-entry.mjs`
- `custom/obsidian-plugin-autodebug/references/command-reference.md`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ci_templates.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ecosystem_support.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_preflight_support.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_repo_runtime.mjs`
- `docs/status/lanes/b1-backlog-slice/autopilot-phase-1.md`
- `docs/status/lanes/b1-backlog-slice/autopilot-round-roadmap.md`

## Implementation Notes

- Added `obsidian_debug_preflight_support.mjs` as the shared pre-build gate resolver so doctor and CI template generation use the same ordered lint/plugin-entry detection, command previews, and remediation hints.
- Fixed `detectScriptProbe()` to allow loose script-name/body matching for plugin-entry validation probes, then tightened the name/body patterns so `validate:plugin-entry`/ReviewBot-style scripts are caught without relying on an installed package name.
- Reordered generated Bash/PowerShell quality-gate templates so plugin-entry validation now runs after lint and before build, and exposed the shared preflight metadata in doctor/CI reports for downstream consumers.
- Added `fixtures/preflight-smoke-plugin/` with intentionally committed `{{...}}` residue in `manifest.json` and `reviewbot-plugin-entry.json`, plus node-based validation scripts that fail before build to prove the preflight gates work without package-manager installs.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_preflight_support.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ecosystem_support.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ci_templates.mjs`
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `node --check custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/scripts/check-manifest-residue.mjs`
- `node --check custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/scripts/validate-plugin-entry.mjs`
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b18-repro --plugin-id autopilot-b18-repro --output .tmp-skills/autopilot-b18-repro-doctor.json` — passed after the fix; doctor now reports `validate:plugin-entry` as a pre-build gate with command preview and remediation hints.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ci_templates.mjs --repo-dir .tmp-skills/autopilot-b18-repro --job job.json --output-dir autodebug/ci --output .tmp-skills/autopilot-b18-repro-ci.json` — passed after the fix; generated defaults now keep `pluginEntryValidationScript=validate:plugin-entry`.
- `node --input-type=module -` inline assertions against `.tmp-skills/autopilot-b18-repro-doctor.json`, `.tmp-skills/autopilot-b18-repro-ci.json`, and `.tmp-skills/autopilot-b18-repro/autodebug/ci/quality-gate.sh` — passed; verified plugin-entry detection plus lint → plugin-entry → build ordering.
- `node --input-type=module -` inline spawn assertions for `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/scripts/check-manifest-residue.mjs` and `custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin/scripts/validate-plugin-entry.mjs` — passed; both scripts fail intentionally with the expected pre-build residue diagnostics.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin --plugin-id preflight-smoke-plugin --output .tmp-skills/autopilot-b18/preflight-doctor.json` — passed; the committed fixture advertises both preflight gates in doctor output.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_ci_templates.mjs --repo-dir custom/obsidian-plugin-autodebug/fixtures/preflight-smoke-plugin --job ../../../../.tmp-skills/autopilot-b18/preflight-job.json --output-dir ../../../../.tmp-skills/autopilot-b18/ci --output .tmp-skills/autopilot-b18/preflight-ci.json` — passed; generated fixture templates emit plugin-entry validation before build.
- `node --input-type=module -` inline assertions against `.tmp-skills/autopilot-b18/preflight-doctor.json`, `.tmp-skills/autopilot-b18/preflight-ci.json`, and `.tmp-skills/autopilot-b18/ci/quality-gate.sh` — passed; verified the committed fixture’s preflight metadata and generated Bash gate ordering.

## Validation Gaps

- Lint command was blank in the autopilot metadata, so no repo-wide lint command existed beyond the targeted syntax checks and doctor/CI regressions above.
- Typecheck command was blank in the autopilot metadata, so no repo-wide typecheck command existed to run.
- Full test command was blank in the autopilot metadata, so no repo-wide full test suite existed to run.
- Build command was blank in the autopilot metadata, so no repo-wide build command existed beyond the targeted doctor/template generation checks above.
- Vulture command was blank in the autopilot metadata, so no dead-code observability run existed to record.

## Next Recommended Slice

- Advance the controller to `b2-backlog-slice` for `B19 - Repo-owned Obsidian E2E adapter fixtures and CI wiring`.
