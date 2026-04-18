# Autopilot Phase 11: B11 Package-Manager And Runtime Doctor Coverage

> **Status**: [DONE]
> **Attempt**: 1
> **Preset**: Bugfix / backlog
> **Repository**: `my-skills`
> **Date**: 2026-04-18

## Scope

- Added repo-driven package-manager/runtime detection for Node, Corepack, `packageManager`, lockfiles, and `build` / `dev` / `test` scripts.
- Updated the generic doctor to report package-manager inference, Corepack readiness, script catalogs, and fix plans that use inferred npm/pnpm commands instead of assuming npm-only workflows.
- Updated the generic job runner and job template/schema so `build.command` can stay empty while `build.inferFromRepo` + `build.script` infer the repo-owned package-manager command.
- Added npm and pnpm/Corepack smoke fixtures plus skill/eval documentation for the new repo-driven inference path.

## Changed Files

- `custom/obsidian-plugin-autodebug/SKILL.md`
- `custom/obsidian-plugin-autodebug/evals/evals.json`
- `custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin/package.json`
- `custom/obsidian-plugin-autodebug/fixtures/native-smoke-sample-plugin/package-lock.json`
- `custom/obsidian-plugin-autodebug/fixtures/package-manager-smoke-pnpm-plugin/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/package-manager-smoke-pnpm-plugin/package.json`
- `custom/obsidian-plugin-autodebug/fixtures/package-manager-smoke-pnpm-plugin/pnpm-lock.yaml`
- `custom/obsidian-plugin-autodebug/fixtures/package-manager-smoke-pnpm-plugin/dist/manifest.json`
- `custom/obsidian-plugin-autodebug/fixtures/package-manager-smoke-pnpm-plugin/dist/main.js`
- `custom/obsidian-plugin-autodebug/fixtures/package-manager-smoke-pnpm-plugin/dist/styles.css`
- `custom/obsidian-plugin-autodebug/job-specs/generic-debug-job.template.json`
- `custom/obsidian-plugin-autodebug/job-specs/obsidian-debug-job.schema.json`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs`
- `custom/obsidian-plugin-autodebug/scripts/obsidian_debug_repo_runtime.mjs`
- `docs/status/autopilot-round-roadmap.md`
- `docs/status/autopilot-phase-11.md`

## Implementation Notes

- `obsidian_debug_repo_runtime.mjs` centralizes package-manager detection and resolves runnable script commands through direct tools or Corepack when the repo points at `pnpm` / `yarn`.
- `obsidian_debug_doctor.mjs` now emits `repoRuntime` details plus checks for `package-manager-field`, `package-manager-lockfiles`, `package-manager-inference`, `corepack-readiness`, and the `build/dev/test` script catalog.
- Doctor build fix plans now use the inferred repo command, so missing dist artifacts produce `npm run build` or `corepack pnpm run build` as appropriate.
- `obsidian_debug_job.mjs` now records `repoTooling`, `buildCommand`, and `blockers`; it infers the build command when `build.command` is empty and refuses run mode if inference stays unresolved.

## Windows-Style Smoke

- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b11/npm-missing-dist --plugin-id native-smoke-sample-plugin --platform windows --obsidian-command obsidian --fix --output .tmp-skills/autopilot-b11/npm-doctor-windows.json` inferred npm with high confidence from `packageManager=npm@10.9.0` plus `package-lock.json` and generated `.tmp-skills/autopilot-b11/doctor-fixes.ps1` with `npm run build`.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b11/npm-job.json --platform windows --dry-run --output .tmp-skills/autopilot-b11/npm-job-plan.json` produced a PowerShell cycle plan with `-BuildCommand npm run build` and no blockers.

## macOS / Bash Smoke

- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs --repo-dir .tmp-skills/autopilot-b11/pnpm-missing-dist --plugin-id package-manager-smoke-pnpm-plugin --platform bash --obsidian-command obsidian --fix --output .tmp-skills/autopilot-b11/pnpm-doctor-bash.json` inferred pnpm with high confidence from `packageManager=pnpm@9.15.0` plus `pnpm-lock.yaml`, detected that `pnpm` was absent from `PATH`, and generated `.tmp-skills/autopilot-b11/doctor-fixes.sh` with `corepack pnpm run build`.
- `node custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs --job .tmp-skills/autopilot-b11/pnpm-job.json --platform bash --dry-run --output .tmp-skills/autopilot-b11/pnpm-job-plan.json` produced a Bash cycle plan with `--build-command "corepack pnpm run build"` and no blockers.

## Validation Results

- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_repo_runtime.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_doctor.mjs` — passed.
- `node --check custom/obsidian-plugin-autodebug/scripts/obsidian_debug_job.mjs` — passed.
- `node --input-type=module -e "import { detectRepoRuntime } ..."` — passed for npm and pnpm fixtures, including inferred `build/dev/test` commands.
- The four doctor/job smoke commands above produced the expected npm and pnpm/Corepack JSON outputs plus fix scripts.
- `node --input-type=module <<'EOF' ... EOF` — passed while asserting the generated doctor/job artifacts and fix scripts.
- `git diff --check` — passed.

## Validation Gaps

- Lint command was blank in the round metadata, so no repo-wide lint step existed to run.
- Typecheck command was blank in the round metadata, so no repo-wide typecheck step existed to run.
- Full test command was blank in the round metadata, so no repo-wide test suite existed to run.
- Build command was blank in the round metadata, so no repo-wide build step existed to run.
- Vulture command was blank in the round metadata, so no dead-code observability run existed to record.

## Next Recommended Slice

- `B12 - Optional Playwright and UI trace adapter`
