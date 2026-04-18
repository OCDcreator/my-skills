# Autopilot Phase 1: B1 Config-Driven Debug Jobs

> **Status**: [DONE]
> **Attempt**: 1
> **Preset**: `Bugfix / Backlog`
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Executed the queued `[NEXT]` slice: `B1 - Config-driven debug job spec and platform-neutral command adapters`.
- Kept work inside `custom/obsidian-plugin-autodebug`.
- Added a generic job spec format covering runtime, build, deploy, reload, log watch, scenario, assertions, comparison, profile, report, capture, and state handling.
- Added a platform adapter runner that emits Windows PowerShell and macOS/Linux Bash dry-run command plans around the existing direct cycle wrappers.
- Preserved the direct PowerShell and Bash cycle workflows as documented fallback paths.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs`
- `custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json`
- `custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-1.md`

## Validation Results

- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json --platform windows --dry-run` — passed; emitted a PowerShell dry-run command plan.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json --platform bash --dry-run` — passed; emitted a Bash dry-run command plan.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs` — passed.
- `node -e "const fs=require('fs'); for (const p of ['custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json','custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json']) JSON.parse(fs.readFileSync(p,'utf8')); console.log('job spec JSON ok');"` — passed.
- `$output = node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json --platform windows --mode run 2>&1; if ($LASTEXITCODE -eq 0) { throw 'expected placeholder guard to fail run mode' }; if (($output -join "`n") -notmatch 'placeholder') { throw 'placeholder guard message missing' }; 'placeholder guard ok'` — passed; confirmed run mode refuses unresolved placeholders.

## Configured Validation Gaps

- Lint: blank in round metadata; not run.
- Typecheck: blank in round metadata; not run.
- Full test: blank in round metadata; not run.
- Build: blank in round metadata; not run.
- Vulture: blank in round metadata; not run.

## Vulture Findings

- Vulture was not configured for this round, so no dead-code observability command was run.

## Next Recommended Slice

- Continue with `B2 - Generic view-open strategy chain and selector discovery`.
